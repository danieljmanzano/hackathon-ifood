"""Estimativas independentes: A (OpenRouter, só texto) e B (Gemini, texto + imagem)."""
import asyncio
import json
import logging
import math

from jsonschema import validate

from app.core.config import Settings
from app.schemas.macro import MealCandidate
from app.services.gemini import analyze_image
from ..entrada import extrair_json, montar_prompt
from ..modelos import Ingrediente, Leitura, Macros
from ..prompts import (INSTRUCOES_DECOMPOR, INSTRUCOES_ESTIMATIVA, SCHEMA_DECOMPOR, SCHEMA_ESTIMATIVA)
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


def leitura_de_json(dados: dict, fonte: str) -> Leitura | None:
    """Converte a resposta validada em Leitura. None se o modelo disse que não há base para estimar."""
    if not dados["suficiente"]:
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
        suposicoes=list(dados["suposicoes"]), justificativa=dados["justificativa"],
    )


async def estimar_a(settings: Settings, candidate: MealCandidate, opcoes: list[str] | None,
                    peso_g: float | None) -> Leitura | None:
    """OpenRouter, só texto. Com N amostras, devolve o consenso entre elas."""
    prompt = f"Estime as calorias e macros deste item.\n\n{montar_prompt(candidate, opcoes, peso_g)}"
    temperatura = 0.2 if settings.calorias_amostras == 1 else 0.7

    async def uma() -> Leitura | None:
        dados = await perguntar_json(settings, INSTRUCOES_ESTIMATIVA, prompt, SCHEMA_ESTIMATIVA,
                                     temperature=temperatura)
        return leitura_de_json(dados, "openrouter")

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
        fonte="openrouter", macros=junto.macros, faixa_min=junto.faixa_min, faixa_max=junto.faixa_max,
        confianca=junto.confianca_modelos, porcao_base=base.porcao_base, peso_g=junto.peso_g,
        ingredientes=base.ingredientes, suposicoes=junto.suposicoes, justificativa=base.justificativa,
    )


async def estimar_b(settings: Settings, candidate: MealCandidate, opcoes: list[str] | None, peso_g: float | None,
                    imagem: tuple[bytes, str] | None) -> Leitura | None:
    """Gemini com texto + imagem (a única fonte que enxerga o prato). Sem imagem ou chave, não roda."""
    if imagem is None or not settings.gemini_api_key:
        return None
    prompt = (f"{INSTRUCOES_ESTIMATIVA}\n\nResponda SOMENTE com um objeto JSON que siga este JSON Schema:\n"
              f"{json.dumps(SCHEMA_ESTIMATIVA, ensure_ascii=False)}\n\n"
              f"Estime as calorias e macros deste item.\n\n{montar_prompt(candidate, opcoes, peso_g)}")
    texto = await analyze_image(imagem[0], prompt, mime_type=imagem[1], json_mode=True, settings=settings)
    dados = extrair_json(texto)
    validate(dados, SCHEMA_ESTIMATIVA)
    return leitura_de_json(dados, "gemini")


async def decompor_ingredientes(settings: Settings, candidate: MealCandidate, opcoes: list[str] | None,
                                peso_g: float | None) -> list[Ingrediente]:
    """Só usado quando nenhuma estimativa trouxe ingredientes."""
    dados = await perguntar_json(settings, INSTRUCOES_DECOMPOR,
                                 f"Decomponha este item.\n\n{montar_prompt(candidate, opcoes, peso_g)}",
                                 SCHEMA_DECOMPOR)
    return [Ingrediente(i["nome"], float(i["gramas"])) for i in dados["ingredientes"] if i["gramas"] > 0]
