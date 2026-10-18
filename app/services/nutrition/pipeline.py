"""Pipeline de calorias (ver pipeline_calorias_v2.dot): fontes em cascata e junções finais.

online (bases → web) e estimativa (A + B + TACO) rodam em paralelo; fundir, calcular_porcao e validar fecham.
"""
import asyncio
import json
import logging
from datetime import datetime, timezone

from jsonschema import ValidationError as SchemaError

from app.core.config import Settings
from app.core.exceptions import AppError
from app.schemas.macro import MealCandidate, NutritionResult
from .entrada import baixar_imagem, foto_ilustrativa, montar_prompt, restaurante_valido
from .etapas.bases import carregar_taco, consultar_bases
from .etapas.consenso import consenso, fundir
from .etapas.estimar import EstimativaInvalida, decompor_ingredientes, estimar_a, estimar_b
from .etapas.ingredientes import casar_ingredientes, somar_ingredientes
from .etapas.porcao import calcular_porcao, converter_em_gramas, extrair_porcao
from .etapas.validar import validar
from .etapas.web import buscar_na_web
from .modelos import Estimativa, InfoOnline

PIPELINE_VERSION = "calorias-v3"
ERROS_ETAPA = (AppError, json.JSONDecodeError, SchemaError, KeyError, EstimativaInvalida)

log = logging.getLogger(__name__)


async def _seguro(coro, etapa: str):
    """Falha de uma etapa vira None: as outras fontes continuam."""
    try:
        return await coro
    except ERROS_ETAPA as e:
        log.warning("Etapa %s falhou: %s", etapa, e)
        return None


async def _nada():
    return None


async def _online(settings: Settings, candidate: MealCandidate, opcoes: list[str] | None,
                  descricao: str) -> InfoOnline | None:
    """Bases de dados primeiro; a web só roda se elas não acharem."""
    info = None
    if settings.calorias_buscar_bases and settings.openrouter_api_key:
        info = await _seguro(consultar_bases(settings, candidate, descricao), "bases")
    if (info is None and settings.calorias_busca_web and settings.gemini_api_key
            and restaurante_valido(candidate)):
        info = await _seguro(buscar_na_web(settings, candidate, opcoes), "web")
    return info


async def _estimativa(settings: Settings, candidate: MealCandidate, opcoes: list[str] | None,
                      peso_g: float | None, imagem) -> Estimativa | None:
    """A (OpenRouter, texto) e B (Gemini, texto + imagem) em paralelo, mais a soma de ingredientes pela TACO."""
    a, b = await asyncio.gather(
        _seguro(estimar_a(settings, candidate, opcoes, peso_g), "estimar_a") if settings.openrouter_api_key
        else _nada(),
        _seguro(estimar_b(settings, candidate, opcoes, peso_g, imagem), "estimar_b"),
    )
    leituras = [x for x in (a, b) if x is not None]

    alimentos = carregar_taco(str(settings.calorias_dados_dir)) if settings.calorias_buscar_bases else ()
    if alimentos and settings.openrouter_api_key:
        ingredientes = next((l.ingredientes for l in (b, a) if l is not None and l.ingredientes), [])
        if not ingredientes:
            ingredientes = await _seguro(decompor_ingredientes(settings, candidate, opcoes, peso_g),
                                         "decompor") or []
        if ingredientes:
            casados = await _seguro(casar_ingredientes(settings, ingredientes, alimentos), "casar_taco")
            soma = somar_ingredientes(ingredientes, casados) if casados else None
            if soma is not None:
                leituras.append(soma)
    return consenso(leituras)


def _indisponivel(motivo: str) -> NutritionResult:
    return NutritionResult(state="unavailable", pipeline_version=PIPELINE_VERSION,
                           obtained_at=datetime.now(timezone.utc), evidence=motivo)


async def calcular(settings: Settings, candidate: MealCandidate, opcoes: list[str] | None) -> NutritionResult:
    porcao = extrair_porcao(candidate, opcoes)
    ilustrativa = foto_ilustrativa(candidate)
    imagem = None if ilustrativa else await baixar_imagem(candidate.image_url, settings.nutrition_timeout_seconds)
    descricao = montar_prompt(candidate, opcoes, porcao.gramas)

    online = _online(settings, candidate, opcoes, descricao)
    estimativa = _estimativa(settings, candidate, opcoes, porcao.gramas, imagem)
    est: Estimativa | None = None
    if settings.calorias_estimar_sempre:
        info, est = await asyncio.gather(online, estimativa)
    else:
        info = await online
        if info is None:
            est = await estimativa
        else:
            estimativa.close()

    peso_estimado = (est.peso_g if est else None) or (info.porcao_g if info else None)
    gramas, origem_gramas, avisos = converter_em_gramas(porcao, peso_estimado)

    info_macros = calcular_porcao(info, gramas) if info else None
    if info is not None and info_macros is None:
        avisos.append(f"Fonte {info.fonte_nome} é por 100 g e o peso do prato é desconhecido: não foi usada.")
        info = None
        if not settings.calorias_estimar_sempre and est is None:  # modo econômico: ainda não rodou
            est = await _estimativa(settings, candidate, opcoes, porcao.gramas, imagem)

    fundido = fundir(info, info_macros, est)
    if fundido is None:
        return _indisponivel("Não foi possível obter calorias de nenhuma fonte para este item.")

    validacao = validar(fundido, gramas, settings.calorias_limiar_confianca)
    suposicoes = list(est.suposicoes) if est else []
    if ilustrativa:
        suposicoes.append("Foto ilustrativa: não foi usada para medir a porção.")
    elif candidate.image_url and imagem is None:
        suposicoes.append("Imagem indisponível: estimativa feita só com o texto.")
    suposicoes += avisos + validacao.motivos

    porcao_base = fundido.porcao_base or "unidade do item"
    if gramas:
        porcao_base += f" (~{gramas:.0f} g, peso {origem_gramas})"
    macros = fundido.macros
    evidencia = fundido.info.evidencia if fundido.info else (est.justificativa if est else "") or "Estimativa."
    return NutritionResult(
        state="ready", method=fundido.method, portion_basis=porcao_base,
        calories=round(macros.kcal), minimum=round(fundido.faixa_min), maximum=round(fundido.faixa_max),
        protein_g=_arred(macros.proteina_g), carbs_g=_arred(macros.carbo_g), fat_g=_arred(macros.gordura_g),
        portion_grams=round(gramas) if gramas else None, confidence=validacao.confianca,
        source_name=fundido.info.fonte_nome if fundido.info else None,
        source_url=fundido.info.fonte_url if fundido.info else None,
        evidence=evidencia, assumptions=suposicoes, revisar=validacao.revisar,
        motivo_revisao="; ".join(validacao.motivos) if validacao.revisar and validacao.motivos else None,
        pipeline_version=PIPELINE_VERSION, obtained_at=datetime.now(timezone.utc),
    )


def _arred(valor: float | None) -> float | None:
    return None if valor is None else round(valor, 1)
