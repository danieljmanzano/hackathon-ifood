"""Busca na web (Gemini + Google Search). Último recurso: só roda quando as bases não acharam."""
import json
import math
from urllib.parse import urlparse

from jsonschema import validate

from app.core import logs
from app.core.config import Settings
from app.schemas.macro import MealCandidate
from app.services.gemini import search_web
from app.services.openai_client import responder
from ..entrada import extrair_json, montar_prompt
from ..modelos import InfoOnline, Macros
from ..prompts import INSTRUCOES_JUIZ_WEB, INSTRUCOES_WEB, SCHEMA_JUIZ_WEB, SCHEMA_WEB
from .llm import perguntar_json


def dominio(valor: str) -> str:
    """Domínio de uma URL ou de um título que já é domínio (o grounding devolve os dois)."""
    texto = valor.strip().lower()
    host = urlparse(texto).netloc if "://" in texto else texto.split("/")[0]
    return host.removeprefix("www.")


def _numero_valido(v) -> bool:
    return isinstance(v, (int, float)) and math.isfinite(v) and v >= 0


async def _pesquisar(settings: Settings, prompt: str) -> tuple[str, list[str]]:
    """Texto da resposta e as fontes realmente consultadas, pelo provedor escolhido."""
    if settings.nutrition_provider == "openai":
        return await responder(prompt, instrucoes="Pesquise na web e responda somente com JSON.", web=True,
                               schema=SCHEMA_WEB, settings=settings)
    return await search_web(prompt, settings=settings)


async def buscar_na_web(settings: Settings, candidate: MealCandidate, opcoes: list[str] | None) -> InfoOnline | None:
    prompt = (f"{INSTRUCOES_WEB}\n\nFormato (JSON Schema):\n{json.dumps(SCHEMA_WEB, ensure_ascii=False)}\n\n"
              f"Procure a informação nutricional oficial deste item.\n\n{montar_prompt(candidate, opcoes)}")
    fornecedor = "OpenAI web_search" if settings.nutrition_provider == "openai" else "Gemini + Google Search"
    logs.info("web", f"buscando \"{candidate.name}\" de {candidate.merchant_name} via {fornecedor}")
    with logs.Cronometro() as t:
        texto, consultados = await _pesquisar(settings, prompt)
    logs.info("web", f"busca terminou em {t.texto}; {len(consultados)} fontes consultadas")
    logs.detalhe("web", "domínios consultados: " + (", ".join(sorted({dominio(c) for c in consultados})) or "nenhum"))
    logs.detalhe("web", f"resposta: {logs.curto(texto, 400)}")
    dados = extrair_json(texto)
    validate(dados, SCHEMA_WEB)
    if not dados["encontrado"]:
        logs.info("web", "o modelo não encontrou tabela nutricional publicada deste produto")
        return None
    if not dados["fonte_url"] or not dados["trecho_fonte"].strip():
        logs.info("web", "descartada: resposta sem URL da fonte ou sem trecho citado")
        return None
    if dominio(dados["fonte_url"]) not in {dominio(c) for c in consultados}:
        logs.info("web", f"descartada: {dominio(dados['fonte_url'])} não está entre os sites realmente consultados")
        return None
    kcal = dados["calorias"]
    if not _numero_valido(kcal):
        logs.info("web", "descartada: calorias ausentes ou inválidas na resposta")
        return None
    logs.info("web", f"candidata: {kcal:.0f} kcal em {dominio(dados['fonte_url'])} (\"{dados['produto_na_fonte']}\")")
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
        logs.info("web", f"descartada: juiz diz que é outro produto ({logs.curto(juiz['motivo'], 160)})")
        return None
    logs.info("web", f"juiz confirmou o mesmo produto ({logs.curto(juiz['motivo'], 120)}) → fonte aceita")

    def opcional(v):
        return float(v) if _numero_valido(v) else None

    return InfoOnline(
        macros=Macros(float(kcal), opcional(dados["proteina_g"]), opcional(dados["carbo_g"]),
                      opcional(dados["gordura_g"])),
        base="item", porcao_base=dados["porcao_base"], fonte_nome=dados["fonte_nome"] or dominio(dados["fonte_url"]),
        fonte_url=dados["fonte_url"], method="web", porcao_g=opcional(dados["porcao_g"]), faixa=faixa,
        evidencia=f"“{dados['trecho_fonte'].strip()}” {dados['justificativa']}".strip(),
    )
