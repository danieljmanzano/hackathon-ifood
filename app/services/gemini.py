import asyncio
import base64
from typing import Any

import httpx

from app.core.config import Settings, get_settings
from app.core.exceptions import AppError


# Falhas transitórias: vale tentar de novo / trocar de modelo.
RETRYABLE_STATUS = {404, 429, 500, 503, 504}


class GeminiError(AppError):
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message, status_code=status_code, code="gemini_error")


async def analyze_image(
    image: bytes,
    prompt: str,
    *,
    mime_type: str = "image/jpeg",
    model: str | None = None,
    settings: Settings | None = None,
) -> str:
    """Envia uma imagem + prompt ao Gemini (VLM) e retorna o texto da resposta."""
    settings = settings or get_settings()
    if not settings.gemini_api_key:
        raise GeminiError("GEMINI_API_KEY não configurada", status_code=500)

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
                        parts = response.json()["candidates"][0]["content"]["parts"]
                        return "".join(part.get("text", "") for part in parts)
                    except (KeyError, IndexError, ValueError) as exc:
                        raise GeminiError("Resposta inesperada do Gemini (possível bloqueio de conteúdo)") from exc

                errors.append(f"{current}: {response.status_code} {response.text[:150]}")
                if response.status_code not in RETRYABLE_STATUS:
                    raise GeminiError("\n".join(errors))
                if response.status_code == 404:
                    break  # modelo inexistente: tentar o próximo, sem repetir
                await asyncio.sleep(2 ** (attempt + 1))

    raise GeminiError("Todos os modelos falharam:\n" + "\n".join(errors))
