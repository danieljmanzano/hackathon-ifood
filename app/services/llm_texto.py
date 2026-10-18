"""LLM de texto com fallback entre provedores: se um falhar, tenta o outro (quando a chave existe).

OpenRouter (modelos gratuitos, com 3 reservas) e OpenAI (pago). Quem chama diz quem tem preferência;
a ordem é sempre [preferido, outro]. Desligue com LLM_FALLBACK=false.
Se todos falharem, levanta o erro do preferido (quem chama já trata OpenRouterError / OpenAIError).
"""

import asyncio
from typing import Literal

from app.core import logs
from app.core.config import Settings, get_settings
from app.core.exceptions import AppError
from app.services.openai_client import OpenAIError, responder
from app.services.openrouter import Message, OpenRouterError, chat_completion

Provedor = Literal["openrouter", "openai"]
ERRO = {"openrouter": OpenRouterError, "openai": OpenAIError}


def _chave(settings: Settings, provedor: Provedor) -> str:
    return (
        settings.openai_api_key.get_secret_value()
        if provedor == "openai"
        else settings.openrouter_api_key
    )


def ordem(settings: Settings, preferido: Provedor) -> list[Provedor]:
    """Provedores a tentar, em ordem; os sem chave ficam de fora."""
    outro: Provedor = "openai" if preferido == "openrouter" else "openrouter"
    candidatos = [preferido, outro] if settings.llm_fallback else [preferido]
    return [p for p in candidatos if _chave(settings, p)]


def _para_openai(messages: list[Message]) -> tuple[str | list[Message], str]:
    """Mensagens de chat -> (entrada, instruções) da Responses API: o 'system' vira instruções."""
    instrucoes = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
    resto = [m for m in messages if m["role"] != "system"]
    entrada = resto[0]["content"] if len(resto) == 1 and resto[0]["role"] == "user" else resto
    return entrada, instrucoes


async def chat_completion_fallback(
    messages: list[Message],
    *,
    model: str | None = None,
    temperature: float = 0.2,
    max_tokens: int | None = None,
    json_mode: bool = False,
    preferido: Provedor | None = None,
    prazo_primeiro: float | None = None,
    log_content: bool = True,
    settings: Settings | None = None,
) -> str:
    """`prazo_primeiro`: segundos que o provedor principal tem antes de a reserva assumir (só se houver reserva).

    Padrão: LLM_FALLBACK_APOS_SEGUNDOS. Quem tem um prazo total curto (ex.: a interpretação da busca, 18 s)
    deve passar uma fração dele, senão o principal consome tudo e a reserva nunca roda.
    """
    settings = settings or get_settings()
    preferido = (
        preferido or settings.nutrition_provider
    )  # padrão: o provedor escolhido (NUTRITION_PROVIDER)
    tentativas = ordem(settings, preferido)
    if not tentativas:
        raise ERRO[preferido](
            f"Nenhuma chave de LLM configurada ({preferido}"
            f"{' ou o outro provedor' if settings.llm_fallback else ''})",
            status_code=500,
        )
    limite = prazo_primeiro if prazo_primeiro is not None else settings.llm_fallback_apos_segundos

    async def chamar(provedor: Provedor) -> str:
        if provedor == "openai":
            entrada, instrucoes = _para_openai(messages)
            texto, _ = await responder(
                entrada,
                instrucoes=instrucoes,
                json_mode=json_mode,
                log_content=log_content,
                settings=settings,
            )
            return texto
        return await chat_completion(
            messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=json_mode,
            log_content=log_content,
            settings=settings,
        )

    primeiro_erro: AppError | None = None
    for i, provedor in enumerate(tentativas):
        ha_reserva = i + 1 < len(tentativas)
        try:
            # Só o que tem reserva atrás é cortado por tempo; o último usa o que sobrar do prazo de quem chamou.
            texto = await (
                asyncio.wait_for(chamar(provedor), limite) if ha_reserva else chamar(provedor)
            )
            if i > 0:
                modelo = (
                    settings.nutrition_model if provedor == "openai" else settings.openrouter_model
                )
                logs.info(
                    "llm", f"RESERVA respondeu: {provedor} ({modelo}) no lugar de {tentativas[0]}"
                )
                if log_content:
                    logs.info("llm", f"resposta da reserva: {logs.curto(texto, 500) or '(vazia)'}")
            return texto
        except (AppError, asyncio.TimeoutError) as e:
            erro = (
                e
                if isinstance(e, AppError)
                else ERRO[provedor](f"{provedor} não respondeu em {limite:.0f} s", status_code=504)
            )
            primeiro_erro = primeiro_erro or erro
            proximo = tentativas[i + 1] if ha_reserva else None
            logs.aviso(
                "llm",
                f"{provedor} falhou ({logs.curto(erro.message, 120) if log_content else type(erro).__name__})"
                + (f" → usando {proximo} como reserva" if proximo else " → sem mais reservas"),
            )
    raise primeiro_erro
