from typing import Any

import httpx

from app.core import logs
from app.core.config import Settings, get_settings
from app.core.exceptions import AppError

Message = dict[str, Any]

# Erros em que vale tentar o próximo modelo (limite, modelo removido, falha do provedor).
RETRYABLE_STATUS = {404, 408, 429, 500, 502, 503, 504}


class OpenRouterError(AppError):
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message, status_code=status_code, code="openrouter_error")


async def chat_completion(
    messages: list[Message],
    *,
    model: str | None = None,
    temperature: float = 0.2,
    max_tokens: int | None = None,
    json_mode: bool = False,
    settings: Settings | None = None,
) -> str:
    """Chama o OpenRouter (API compatível com OpenAI), com fallback entre modelos. Retorna o texto."""
    settings = settings or get_settings()
    if not settings.openrouter_api_key:
        raise OpenRouterError("OPENROUTER_API_KEY não configurada", status_code=500)

    models = [model or settings.openrouter_model, *settings.openrouter_fallback_models]
    errors: list[str] = []

    async with httpx.AsyncClient(base_url=settings.openrouter_base_url, timeout=settings.openrouter_timeout) as client:
        for current in dict.fromkeys(models):
            payload: dict[str, Any] = {"model": current, "messages": messages, "temperature": temperature}
            if max_tokens is not None:
                payload["max_tokens"] = max_tokens
            if json_mode:
                payload["response_format"] = {"type": "json_object"}
            with logs.Cronometro() as t:
                try:
                    response = await client.post(
                        "/chat/completions",
                        json=payload,
                        headers={"Authorization": f"Bearer {settings.openrouter_api_key}"},
                    )
                except httpx.HTTPError as exc:
                    response = None
                    errors.append(f"{current}: rede ({exc})")
                    logs.aviso("openrouter", f"{current}: falha de rede ({logs.curto(exc, 100)}) → próximo modelo")
            if response is None:
                continue
            logs.detalhe("openrouter", f"{current} → {response.status_code} em {t.texto}")

            if response.status_code == 200:
                try:
                    texto = response.json()["choices"][0]["message"]["content"] or ""
                    logs.detalhe("openrouter", f"resposta: {logs.curto(texto, 300)}")
                    return texto
                except (KeyError, IndexError, ValueError):
                    errors.append(f"{current}: resposta inesperada")
                    logs.aviso("openrouter", f"{current}: resposta sem conteúdo → próximo modelo")
                    continue

            errors.append(f"{current}: {response.status_code} {response.text[:150]}")
            invalid_model = False
            if response.status_code == 400:
                try:
                    message = str(response.json().get("error", {}).get("message", "")).lower()
                    invalid_model = "model" in message and any(
                        phrase in message for phrase in ("not a valid", "not valid", "invalid", "not found", "does not exist")
                    )
                except (ValueError, AttributeError):
                    pass
            retry = response.status_code in RETRYABLE_STATUS or invalid_model
            logs.aviso("openrouter", f"{current}: {response.status_code} {logs.curto(response.text, 110)}"
                                     f"{' → próximo modelo' if retry else ''}")
            if not retry:
                break

    raise OpenRouterError("Todos os modelos falharam:\n" + "\n".join(errors))
