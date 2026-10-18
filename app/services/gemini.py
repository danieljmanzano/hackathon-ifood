import asyncio
import base64
import logging
from typing import Any

import httpx

from app.core.config import Settings, get_settings
from app.core.exceptions import AppError


log = logging.getLogger(__name__)

# Falhas transitórias: vale tentar de novo / trocar de modelo.
RETRYABLE_STATUS = {404, 429, 500, 503, 504}


class GeminiError(AppError):
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message, status_code=status_code, code="gemini_error")


async def _gerar(payload: dict[str, Any], model: str | None, settings: Settings) -> dict[str, Any]:
    """generateContent com retry (backoff) e fallback de modelo. Retorna o JSON da resposta."""
    if not settings.gemini_api_key:
        raise GeminiError("GEMINI_API_KEY não configurada", status_code=500)

    models = list(dict.fromkeys([model or settings.gemini_model, *settings.gemini_fallback_models]))
    errors: list[str] = []

    async with httpx.AsyncClient(timeout=settings.gemini_timeout) as client:
        for current in models:
            url = f"{settings.gemini_base_url}/models/{current}:generateContent"
            for attempt in range(settings.gemini_retries):
                try:
                    response = await client.post(url, json=payload, headers={"x-goog-api-key": settings.gemini_api_key})
                except httpx.HTTPError as exc:
                    errors.append(f"{current}: rede ({exc})")
                    break

                if response.status_code == 200:
                    try:
                        return response.json()
                    except ValueError as exc:
                        raise GeminiError("Resposta inesperada do Gemini") from exc

                errors.append(f"{current}: {response.status_code} {response.text[:150]}")
                log.warning("Gemini: %s", errors[-1])
                if response.status_code not in RETRYABLE_STATUS:
                    raise GeminiError("\n".join(errors))
                if response.status_code == 404:
                    break  # modelo inexistente: tentar o próximo, sem repetir
                await asyncio.sleep(2 ** (attempt + 1))

    raise GeminiError("Todos os modelos falharam:\n" + "\n".join(errors))


def _texto(dados: dict[str, Any]) -> str:
    try:
        parts = dados["candidates"][0]["content"]["parts"]
        return "".join(part.get("text", "") for part in parts)
    except (KeyError, IndexError) as exc:
        raise GeminiError("Resposta inesperada do Gemini (possível bloqueio de conteúdo)") from exc


async def analyze_image(
    image: bytes,
    prompt: str,
    *,
    mime_type: str = "image/jpeg",
    model: str | None = None,
    json_mode: bool = False,
    settings: Settings | None = None,
) -> str:
    """Envia uma imagem + prompt ao Gemini (VLM) e retorna o texto da resposta."""
    settings = settings or get_settings()
    payload: dict[str, Any] = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": mime_type, "data": base64.b64encode(image).decode()}},
                ]
            }
        ]
    }
    if json_mode:
        payload["generationConfig"] = {"responseMimeType": "application/json"}
    return _texto(await _gerar(payload, model, settings))


async def search_web(
    prompt: str,
    *,
    model: str | None = None,
    settings: Settings | None = None,
) -> tuple[str, list[str]]:
    """Pergunta ao Gemini com Google Search (grounding). Retorna (texto, domínios realmente consultados).

    A ferramenta de busca não combina com saída JSON forçada, então o JSON é pedido no prompt.
    """
    settings = settings or get_settings()
    payload = {"contents": [{"parts": [{"text": prompt}]}], "tools": [{"google_search": {}}]}
    dados = await _gerar(payload, model, settings)
    dominios: list[str] = []
    try:
        chunks = dados["candidates"][0].get("groundingMetadata", {}).get("groundingChunks", [])
    except (KeyError, IndexError):
        chunks = []
    for chunk in chunks:
        web = chunk.get("web") or {}
        for valor in (web.get("title"), web.get("uri")):
            if valor:
                dominios.append(valor)
    return _texto(dados), dominios


async def generate_text(prompt: str, *, model: str | None = None, settings: Settings | None = None) -> str:
    """Pergunta só de texto (usada para checar se o Gemini está de pé)."""
    settings = settings or get_settings()
    return _texto(await _gerar({"contents": [{"parts": [{"text": prompt}]}]}, model, settings))
