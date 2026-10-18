"""Busca na web (OpenAI web_search ou Gemini + Google Search). Só roda quando as bases não acharam.

Dois resultados possíveis, conforme o tipo do item:
- industrializado (produto de mercado): tabela nutricional oficial do produto exato -> InfoOnline (vence as estimativas).
- prato (comida de restaurante): não existe tabela; o modelo pesquisa uma ESTIMATIVA, olhando a foto, a partir de
  pratos equivalentes -> Leitura (entra no consenso junto com as outras estimativas).
"""
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
from ..modelos import InfoOnline, Ingrediente, Leitura, Macros
from ..prompts import INSTRUCOES_JUIZ_WEB, INSTRUCOES_WEB, SCHEMA_JUIZ_WEB, SCHEMA_WEB
from .llm import perguntar_json


def dominio(valor: str) -> str:
    """Domínio de uma URL ou de um título que já é domínio (o grounding devolve os dois)."""
    texto = valor.strip().lower()
    host = urlparse(texto).netloc if "://" in texto else texto.split("/")[0]
    return host.removeprefix("www.")


def _numero_valido(v) -> bool:
    return isinstance(v, (int, float)) and math.isfinite(v) and v >= 0


CONFIANCA_WEB = {"baixa": 0.35, "media": 0.5, "alta": 0.65}  # estimativa pesquisada nunca passa de 0,65


async def _pesquisar(settings: Settings, prompt: str, imagem: tuple[bytes, str] | None) -> tuple[str, list[str]]:
    """Texto da resposta e as fontes realmente consultadas, pelo provedor escolhido (com a foto, se houver)."""
    if settings.nutrition_provider == "openai":
        return await responder(prompt, instrucoes="Pesquise na web e responda somente com JSON.", web=True,
                               schema=SCHEMA_WEB, imagem=imagem, settings=settings)
    return await search_web(prompt, imagem=imagem, settings=settings)


def _opcional(v) -> float | None:
    return float(v) if _numero_valido(v) else None


async def buscar_na_web(settings: Settings, candidate: MealCandidate, opcoes: list[str] | None,
                        imagem: tuple[bytes, str] | None = None) -> InfoOnline | Leitura | None:
    prompt = (f"{INSTRUCOES_WEB}\n\nFormato (JSON Schema):\n{json.dumps(SCHEMA_WEB, ensure_ascii=False)}\n\n"
              f"Pesquise a informação nutricional deste item"
              f"{' (a foto dele está anexada)' if imagem else ' (sem foto)'}.\n\n{montar_prompt(candidate, opcoes)}")
    fornecedor = "OpenAI web_search" if settings.nutrition_provider == "openai" else "Gemini + Google Search"
    logs.info("web", f"pesquisando \"{candidate.name}\" de {candidate.merchant_name} via {fornecedor}"
                     f"{' com a foto' if imagem else ' (sem foto)'}")
    with logs.Cronometro() as t:
        texto, consultados = await _pesquisar(settings, prompt, imagem)
    logs.info("web", f"busca terminou em {t.texto}; {len(consultados)} fontes consultadas")
    logs.detalhe("web", "domínios consultados: " + (", ".join(sorted({dominio(c) for c in consultados})) or "nenhum"))
    logs.detalhe("web", f"resposta: {logs.curto(texto, 400)}")
    dados = extrair_json(texto)
    validate(dados, SCHEMA_WEB)
    logs.info("web", f"o modelo classificou o item como: {dados['tipo_item']}")

    if not dados["encontrado"]:
        logs.info("web", "o modelo não achou base para "
                         + ("a tabela do produto" if dados["tipo_item"] == "industrializado" else "uma estimativa"))
        return None
    if not dados["fonte_url"] or not dados["trecho_fonte"].strip():
        logs.info("web", "descartada: resposta sem URL da fonte ou sem trecho que a sustente")
        return None
    if dominio(dados["fonte_url"]) not in {dominio(c) for c in consultados}:
        logs.info("web", f"descartada: {dominio(dados['fonte_url'])} não está entre os sites realmente consultados")
        return None
    kcal = dados["calorias"]
    if not _numero_valido(kcal) or kcal == 0 and dados["tipo_item"] == "prato":
        logs.info("web", "descartada: calorias ausentes ou inválidas na resposta")
        return None
    faixa = None
    if _numero_valido(dados["faixa_min"]) and _numero_valido(dados["faixa_max"]) \
            and dados["faixa_min"] <= kcal <= dados["faixa_max"]:
        faixa = (float(dados["faixa_min"]), float(dados["faixa_max"]))
    macros = Macros(float(kcal), _opcional(dados["proteina_g"]), _opcional(dados["carbo_g"]),
                    _opcional(dados["gordura_g"]))
    fonte = f"{dados['fonte_nome'] or dominio(dados['fonte_url'])} ({dominio(dados['fonte_url'])})"

    if dados["tipo_item"] == "prato":
        return _estimativa_pesquisada(dados, macros, faixa, fonte)
    return await _tabela_oficial(settings, candidate, opcoes, dados, macros, faixa)


def _estimativa_pesquisada(dados: dict, macros: Macros, faixa, fonte: str) -> Leitura:
    """Prato de restaurante: a pesquisa vira mais uma estimativa (não é fonte oficial, não atropela as outras)."""
    kcal = macros.kcal
    minimo, maximo = faixa or (kcal * 0.75, kcal * 1.25)
    ingredientes = [Ingrediente(i["nome"], float(i["gramas"])) for i in dados["ingredientes"] if i["gramas"] > 0]
    logs.info("web", f"estimativa pesquisada: {kcal:.0f} kcal ({minimo:.0f}–{maximo:.0f}) com base em "
                     f"\"{dados['produto_na_fonte']}\" · {fonte} · confiança {dados['confianca']}")
    return Leitura(
        fonte="web", macros=macros, faixa_min=min(minimo, kcal), faixa_max=max(maximo, kcal),
        confianca=CONFIANCA_WEB[dados["confianca"]], porcao_base=dados["porcao_base"],
        peso_g=_opcional(dados["porcao_g"]), ingredientes=ingredientes,
        suposicoes=[f"Estimativa pesquisada na web com base em “{dados['produto_na_fonte']}” — {fonte}.",
                    *dados["suposicoes"]],
        justificativa=f"“{dados['trecho_fonte'].strip()}” {dados['justificativa']}".strip(),
    )


async def _tabela_oficial(settings, candidate, opcoes, dados: dict, macros: Macros, faixa) -> InfoOnline | None:
    """Produto industrializado: a tabela precisa ser do mesmo produto; um juiz confirma antes de aceitar."""
    logs.info("web", f"candidata: {macros.kcal:.0f} kcal em {dominio(dados['fonte_url'])} "
                     f"(\"{dados['produto_na_fonte']}\")")
    juiz = await perguntar_json(
        settings, INSTRUCOES_JUIZ_WEB,
        f"Pedido:\n{montar_prompt(candidate, opcoes)}\n\nEncontrado na web:\nProduto: {dados['produto_na_fonte']}\n"
        f"Fonte: {dados['fonte_nome']} ({dados['fonte_url']})\nTrecho: {dados['trecho_fonte']}\n"
        f"Base dos valores: {dados['porcao_base']}", SCHEMA_JUIZ_WEB)
    if not juiz["corresponde"]:
        logs.info("web", f"descartada: juiz diz que é outro produto ({logs.curto(juiz['motivo'], 160)})")
        return None
    logs.info("web", f"juiz confirmou o mesmo produto ({logs.curto(juiz['motivo'], 120)}) → tabela aceita")
    return InfoOnline(
        macros=macros, base="item", porcao_base=dados["porcao_base"],
        fonte_nome=dados["fonte_nome"] or dominio(dados["fonte_url"]), fonte_url=dados["fonte_url"], method="web",
        porcao_g=_opcional(dados["porcao_g"]), faixa=faixa,
        evidencia=f"“{dados['trecho_fonte'].strip()}” {dados['justificativa']}".strip(),
    )
