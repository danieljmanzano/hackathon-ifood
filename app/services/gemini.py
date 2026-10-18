import asyncio
import base64
from typing import Any

import httpx

from app.core import logs
from app.core.nutrition_budget import reserve_call, output_limit, check_input
from app.core.config import Settings, get_settings
from app.core.exceptions import AppError


# Falhas transitórias: vale tentar de novo / trocar de modelo.
RETRYABLE_STATUS = {404, 429, 500, 503, 504}


class GeminiError(AppError):
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message, status_code=status_code, code="gemini_error")


async def _gerar(payload: dict[str, Any], model: str | None, settings: Settings) -> dict[str, Any]:
    """generateContent com retry (backoff) e fallback de modelo. Retorna o JSON da resposta."""
    if not settings.gemini_api_key:
        raise GeminiError("GEMINI_API_KEY não configurada", status_code=500)

    check_input([p.get("text", "") for c in payload.get("contents", []) for p in c.get("parts", [])])
    if output_limit():
        payload.setdefault("generationConfig", {})["maxOutputTokens"] = output_limit()
    models = list(dict.fromkeys([model or settings.gemini_model, *settings.gemini_fallback_models]))
    errors: list[str] = []

    async with httpx.AsyncClient(timeout=settings.gemini_timeout) as client:
        for current in models:
            url = f"{settings.gemini_base_url}/models/{current}:generateContent"
            for attempt in range(settings.gemini_retries):
                with logs.Cronometro() as t:
                    try:
                        reserve_call("gemini")
                        response = await client.post(url, json=payload,
                                                     headers={"x-goog-api-key": settings.gemini_api_key})
                    except httpx.HTTPError as exc:
                        response = None
                        errors.append(f"{current}: rede ({exc})")
                        logs.aviso("gemini", f"{current}: falha de rede ({logs.curto(exc, 100)}) → próximo modelo")
                if response is None:
                    break
                logs.detalhe("gemini", f"{current} → {response.status_code} em {t.texto} (tentativa {attempt + 1})")

                if response.status_code == 200:
                    try:
                        dados = response.json()
                    except ValueError as exc:
                        raise GeminiError("Resposta inesperada do Gemini") from exc
                    if current != models[0]:
                        logs.info("gemini", f"RESERVA respondeu: {current} no lugar de {models[0]} em {t.texto}")
                        logs.info("gemini", f"resposta da reserva: {logs.curto(_texto_ou_vazio(dados), 500) or '(vazia)'}")
                    elif attempt > 0:
                        logs.info("gemini", f"{current} respondeu na tentativa {attempt + 1}/{settings.gemini_retries}"
                                            f" em {t.texto}")
                    return dados

                errors.append(f"{current}: {response.status_code} {response.text[:150]}")
                logs.aviso("gemini", f"{current}: {response.status_code} {logs.curto(response.text, 110)}")
                if response.status_code not in RETRYABLE_STATUS:
                    raise GeminiError("\n".join(errors))
                if response.status_code == 404:
                    break  # modelo inexistente: tentar o próximo, sem repetir
                await asyncio.sleep(2 ** (attempt + 1))

    raise GeminiError("Todos os modelos falharam:\n" + "\n".join(errors))


def _texto_ou_vazio(dados: dict[str, Any]) -> str:
    try:
        return _texto(dados)
    except GeminiError:
        return ""


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
    imagem: tuple[bytes, str] | None = None,
    model: str | None = None,
    settings: Settings | None = None,
) -> tuple[str, list[str]]:
    """Pergunta ao Gemini com Google Search (grounding). Retorna (texto, domínios realmente consultados).

    A ferramenta de busca não combina com saída JSON forçada, então o JSON é pedido no prompt.
    """
    settings = settings or get_settings()
    partes: list[dict[str, Any]] = [{"text": prompt}]
    if imagem is not None:
        partes.append({"inline_data": {"mime_type": imagem[1], "data": base64.b64encode(imagem[0]).decode()}})
    payload = {"contents": [{"parts": partes}], "tools": [{"google_search": {}}]}
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
