"""Busca na web (Gemini + Google Search). Último recurso: só roda quando as bases não acharam."""
import json
import logging
import math
from urllib.parse import urlparse

from jsonschema import validate

from app.core.config import Settings
from app.schemas.macro import MealCandidate
from app.services.gemini import search_web
from ..entrada import extrair_json, montar_prompt
from ..modelos import InfoOnline, Macros
from ..prompts import INSTRUCOES_JUIZ_WEB, INSTRUCOES_WEB, SCHEMA_JUIZ_WEB, SCHEMA_WEB
from .llm import perguntar_json

log = logging.getLogger(__name__)


def dominio(valor: str) -> str:
    """Domínio de uma URL ou de um título que já é domínio (o grounding devolve os dois)."""
    texto = valor.strip().lower()
    host = urlparse(texto).netloc if "://" in texto else texto.split("/")[0]
    return host.removeprefix("www.")


def _numero_valido(v) -> bool:
    return isinstance(v, (int, float)) and math.isfinite(v) and v >= 0


async def buscar_na_web(settings: Settings, candidate: MealCandidate, opcoes: list[str] | None) -> InfoOnline | None:
    prompt = (f"{INSTRUCOES_WEB}\n\nFormato (JSON Schema):\n{json.dumps(SCHEMA_WEB, ensure_ascii=False)}\n\n"
              f"Procure a informação nutricional oficial deste item.\n\n{montar_prompt(candidate, opcoes)}")
    texto, consultados = await search_web(prompt, settings=settings)
    dados = extrair_json(texto)
    validate(dados, SCHEMA_WEB)
    if not dados["encontrado"]:
        return None
    if not dados["fonte_url"] or not dados["trecho_fonte"].strip():
        log.info("Busca sem fonte ou trecho para %s; descartada.", candidate.name)
        return None
    if dominio(dados["fonte_url"]) not in {dominio(c) for c in consultados}:
        log.info("Fonte %s não está entre os sites consultados; descartada.", dados["fonte_url"])
        return None
    kcal = dados["calorias"]
    if not _numero_valido(kcal):
        return None
    faixa = None
    if _numero_valido(dados["faixa_min"]) and _numero_valido(dados["faixa_max"]) \
            and dados["faixa_min"] <= kcal <= dados["faixa_max"]:
        faixa = (float(dados["faixa_min"]), float(dados["faixa_max"]))

    juiz = await perguntar_json(
        settings, INSTRUCOES_JUIZ_WEB,
        f"Pedido:\n{montar_prompt(candidate, opcoes)}\n\nEncontrado na web:\nProduto: {dados['produto_na_fonte']}\n"
        f"Fonte: {dados['fonte_nome']} ({dados['fonte_url']})\nTrecho: {dados['trecho_fonte']}\n"
        f"Base dos valores: {dados['porcao_base']}", SCHEMA_JUIZ_WEB)
    if not juiz["corresponde"]:
        log.info("Juiz rejeitou a fonte para %s: %s", candidate.name, juiz["motivo"])
        return None

    def opcional(v):
        return float(v) if _numero_valido(v) else None

    return InfoOnline(
        macros=Macros(float(kcal), opcional(dados["proteina_g"]), opcional(dados["carbo_g"]),
                      opcional(dados["gordura_g"])),
        base="item", porcao_base=dados["porcao_base"], fonte_nome=dados["fonte_nome"] or dominio(dados["fonte_url"]),
        fonte_url=dados["fonte_url"], method="web", porcao_g=opcional(dados["porcao_g"]), faixa=faixa,
        evidencia=f"“{dados['trecho_fonte'].strip()}” {dados['justificativa']}".strip(),
    )
