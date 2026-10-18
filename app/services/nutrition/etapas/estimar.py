"""Estimativas independentes: A (OpenAI/OpenRouter, só texto) e B (OpenAI, texto + imagem)."""
import asyncio
import logging
import math

from jsonschema import validate

from app.core import logs
from app.core.config import Settings
from app.schemas.macro import MealCandidate
from app.services.openai_client import responder
from ..entrada import extrair_json, montar_prompt
from ..modelos import Ingrediente, Leitura, Macros
from app.skills import nutricao_estimativa, nutricao_ingredientes
from .consenso import consenso
from .llm import perguntar_json

log = logging.getLogger(__name__)

CONFIANCA = {"baixa": 0.35, "media": 0.6, "alta": 0.8}


class EstimativaInvalida(Exception):
    """Resposta do modelo inutilizável (números inválidos, formato inesperado)."""


def _numero(valor) -> float | None:
    if valor is None:
        return None
    if not isinstance(valor, (int, float)) or not math.isfinite(valor) or valor < 0:
        raise EstimativaInvalida(f"valor inválido: {valor!r}")
    return float(valor)


def leitura_de_json(dados: dict, fonte: str, etapa: str | None = None) -> Leitura | None:
    """Converte a resposta validada em Leitura. None se o modelo disse que não há base para estimar."""
    if not dados["suficiente"]:
        etapa = etapa or "estimar A"
        logs.info(etapa, f"o modelo ({fonte}) respondeu que NÃO há informação suficiente: "
                         f"{logs.curto(dados['justificativa'], 200)}")
        return None
    kcal, minimo, maximo = _numero(dados["calorias"]), _numero(dados["faixa_min"]), _numero(dados["faixa_max"])
    if None in (kcal, minimo, maximo):
        raise EstimativaInvalida("faixa ou calorias ausentes")
    ingredientes = [Ingrediente(i["nome"], float(i["gramas"])) for i in dados["ingredientes"] if i["gramas"] > 0]
    return Leitura(
        fonte=fonte,
        macros=Macros(kcal, _numero(dados["proteina_g"]), _numero(dados["carbo_g"]), _numero(dados["gordura_g"])),
        faixa_min=min(minimo, kcal), faixa_max=max(maximo, kcal),
        confianca=CONFIANCA[dados["confianca"]], porcao_base=dados["porcao_base"],
        peso_g=_numero(dados["peso_estimado_g"]), ingredientes=ingredientes,
        itens_na_imagem=[str(i).strip() for i in dados.get("itens_visiveis_na_imagem", []) if str(i).strip()],
        suposicoes=list(dados["suposicoes"]), justificativa=dados["justificativa"],
    )


async def estimar_a(settings: Settings, candidate: MealCandidate, opcoes: list[str] | None,
                    peso_g: float | None) -> Leitura | None:
    """OpenRouter, só texto. Com N amostras, devolve o consenso entre elas."""
    pedido = nutricao_estimativa.pedido_a(montar_prompt(candidate, opcoes, peso_g))
    temperatura = 0.2 if settings.calorias_amostras == 1 else 0.7

    async def uma() -> Leitura | None:
        dados = await perguntar_json(settings, nutricao_estimativa.INSTRUCOES, pedido, nutricao_estimativa.SCHEMA,
                                     temperature=temperatura)
        return leitura_de_json(dados, settings.nutrition_provider)

    resultados = await asyncio.gather(*(uma() for _ in range(settings.calorias_amostras)), return_exceptions=True)
    leituras = [r for r in resultados if isinstance(r, Leitura)]
    if not leituras:
        erros = [r for r in resultados if isinstance(r, Exception)]
        if erros:
            raise erros[0]
        return None
    if len(leituras) == 1:
        return leituras[0]
    junto = consenso(leituras)
    base = leituras[0]
    return Leitura(
        fonte=settings.nutrition_provider, macros=junto.macros, faixa_min=junto.faixa_min, faixa_max=junto.faixa_max,
        confianca=junto.confianca_modelos, porcao_base=base.porcao_base, peso_g=junto.peso_g,
        ingredientes=base.ingredientes, suposicoes=junto.suposicoes, justificativa=base.justificativa,
    )


async def estimar_b(settings: Settings, candidate: MealCandidate, opcoes: list[str] | None, peso_g: float | None,
                    imagem: tuple[bytes, str] | None) -> Leitura | None:
    """OpenAI com texto + imagem (a única fonte que enxerga o prato). Sem imagem ou chave, não roda."""
    if imagem is None or not settings.web_api_key:
        return None
    prompt = nutricao_estimativa.pedido_b(montar_prompt(candidate, opcoes, peso_g))
    texto, _ = await responder(prompt, schema=nutricao_estimativa.SCHEMA, imagem=imagem, settings=settings)
    dados = extrair_json(texto)
    validate(dados, nutricao_estimativa.SCHEMA)
    return leitura_de_json(dados, "openai-imagem", etapa="estimar B")


async def decompor_ingredientes(settings: Settings, candidate: MealCandidate, opcoes: list[str] | None,
                                peso_g: float | None) -> list[Ingrediente]:
    """Só usado quando nenhuma estimativa trouxe ingredientes."""
    dados = await perguntar_json(settings, nutricao_ingredientes.INSTRUCOES_DECOMPOR,
                                 nutricao_ingredientes.pedido_decompor(montar_prompt(candidate, opcoes, peso_g)),
                                 nutricao_ingredientes.SCHEMA_DECOMPOR)
    return [Ingrediente(i["nome"], float(i["gramas"])) for i in dados["ingredientes"] if i["gramas"] > 0]
