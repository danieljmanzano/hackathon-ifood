"""Cliente mínimo da OpenAI (Responses API) via HTTP: texto em JSON e busca na web."""
import asyncio
import base64
import copy
from typing import Any

import httpx

from app.core.config import Settings, get_settings
from app.core import logs
from app.core.nutrition_budget import reserve_call, output_limit, check_input
from app.core.exceptions import AppError

RETRYABLE_STATUS = {429, 500, 502, 503, 504}
TENTATIVAS = 3


class OpenAIError(AppError):
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message, status_code=status_code, code="openai_error")


def _estrito(schema: dict) -> dict:
    """JSON Schema no modo strict da OpenAI: todo objeto fecha propriedades extras e exige todas as chaves."""
    novo = copy.deepcopy(schema)

    def visitar(no):
        if isinstance(no, dict):
            if no.get("type") == "object" or "properties" in no:
                no["additionalProperties"] = False
                no["required"] = list(no.get("properties", {}))
            for v in no.values():
                visitar(v)
        elif isinstance(no, list):
            for v in no:
                visitar(v)

    visitar(novo)
    return novo


def _texto(dados: dict[str, Any]) -> str:
    if dados.get("output_text"):
        return dados["output_text"]
    partes = [
        parte.get("text", "")
        for saida in dados.get("output", []) if saida.get("type") == "message"
        for parte in saida.get("content") or [] if parte.get("type") == "output_text"
    ]
    return "".join(partes)


def _fontes(dados: dict[str, Any]) -> list[str]:
    """URLs que a busca realmente abriu ou citou nesta resposta."""
    urls: list[str] = []
    for saida in dados.get("output", []):
        if saida.get("type") == "web_search_call":
            for fonte in (saida.get("action") or {}).get("sources") or []:
                if fonte.get("url"):
                    urls.append(fonte["url"])
        elif saida.get("type") == "message":
            for parte in saida.get("content") or []:
                for anotacao in parte.get("annotations") or []:
                    if anotacao.get("type") == "url_citation" and anotacao.get("url"):
                        urls.append(anotacao["url"])
    return urls


async def responder(
    entrada: str | list[dict],
    *,
    json_mode: bool = True,
    log_content: bool = True,
    instrucoes: str = "",
    web: bool = False,
    schema: dict | None = None,
    imagem: tuple[bytes, str] | None = None,
    model: str | None = None,
    settings: Settings | None = None,
) -> tuple[str, list[str]]:
    """Resposta em JSON (o prompt precisa pedir JSON). Com web=True usa web_search e devolve as URLs consultadas.

    A OpenAI não aceita json_object junto com web_search: com web, a saída estruturada só vale via `schema`
    (json_schema strict); sem schema, o JSON fica por conta do prompt.
    """
    settings = settings or get_settings()
    if not settings.openai_api_key.get_secret_value():
        raise OpenAIError("OPENAI_API_KEY não configurada", status_code=500)

    check_input([entrada, instrucoes])
    modelo = model or settings.nutrition_model
    if imagem is not None:
        url = f"data:{imagem[1]};base64,{base64.b64encode(imagem[0]).decode()}"
        corpo: Any = [{"role": "user", "content": [{"type": "input_text", "text": entrada},
                                                    {"type": "input_image", "image_url": url}]}]
    else:
        corpo = entrada
    payload: dict[str, Any] = {"model": modelo, "input": corpo}
    if schema is not None:
        payload["text"] = {"format": {"type": "json_schema", "name": "saida", "schema": _estrito(schema),
                                      "strict": True}}
    elif not web and json_mode:
        payload["text"] = {"format": {"type": "json_object"}}
    if instrucoes:
        payload["instructions"] = instrucoes
    if web:
        payload["tools"] = [{"type": "web_search"}]
        payload["include"] = ["web_search_call.action.sources"]
    if modelo.startswith(("gpt-5", "o")):  # só modelos de raciocínio aceitam o parâmetro
        payload["reasoning"] = {"effort": settings.openai_reasoning_effort_web if web
                                else settings.openai_reasoning_effort}

    if output_limit():
        payload["max_output_tokens"] = output_limit()
    erro = ""
    async with httpx.AsyncClient(base_url=settings.openai_base_url, timeout=settings.openai_timeout) as client:
        for tentativa in range(TENTATIVAS):
            with logs.Cronometro() as t:
                try:
                    reserve_call("openai")
                    resposta = await client.post("/responses", json=payload,
                                                 headers={"Authorization": f"Bearer {settings.openai_api_key.get_secret_value()}"})
                except httpx.HTTPError as exc:
                    resposta, erro = None, f"rede ({exc!r})"
            if resposta is not None:
                logs.detalhe("openai", f"{modelo}{' +web' if web else ''}{' +imagem' if imagem else ''} → {resposta.status_code} em {t.texto}")
                if resposta.status_code == 200:
                    try:
                        dados = resposta.json()
                    except ValueError as exc:
                        raise OpenAIError("Resposta inesperada da OpenAI") from exc
                    texto, fontes = _texto(dados), _fontes(dados)
                    if tentativa > 0:
                        logs.info("openai", f"{modelo} respondeu na tentativa {tentativa + 1}/{TENTATIVAS} em {t.texto}")
                    if log_content:
                        logs.detalhe("openai", f"resposta: {logs.curto(texto, 300)} · fontes: {len(fontes)}")
                    return texto, fontes
                erro = f"{resposta.status_code} {resposta.text if log_content else 'conteúdo omitido'}"
                if resposta.status_code not in RETRYABLE_STATUS:
                    raise OpenAIError(f"OpenAI {logs.curto(erro, 300)}")
            logs.aviso("openai", f"tentativa {tentativa + 1}/{TENTATIVAS} falhou: {logs.curto(erro)}")
            if tentativa < TENTATIVAS - 1:
                await asyncio.sleep(2 ** (tentativa + 1))
    raise OpenAIError(f"OpenAI indisponível após {TENTATIVAS} tentativas: {logs.curto(erro)}")
