"""Pipeline nutricional como serviço.

Fachada usada pela API: base local de produtos → pipeline (bases, web, estimativas, validação).
Gemini vê a imagem; o OpenRouter faz o texto. Veja pipeline.py e pipeline_calorias_v2.dot.

Sempre devolve um NutritionResult: falhas viram state="error" para não derrubar a busca.
"""
import asyncio
import hashlib
import json
import logging
from datetime import datetime, timezone

from jsonschema import ValidationError as SchemaError
from pydantic import ValidationError

from app.core.config import Settings
from app.core.exceptions import AppError
from app.schemas.macro import MealCandidate, NutritionResult, Recommendation, SelectedItem
from .etapas.estimar import EstimativaInvalida
from .pipeline import PIPELINE_VERSION, calcular
from .produtos import chave_produto, repositorio

LIMITACAO_SEM_NUTRICAO = "Informação nutricional indisponível"

log = logging.getLogger(__name__)

# Resultados prontos por item; estimativas que passam do prazo da resposta terminam aqui em segundo plano.
_cache: dict[str, NutritionResult] = {}
_em_andamento: dict[str, asyncio.Task] = {}


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _resultado(state: str, **campos) -> NutritionResult:
    return NutritionResult(state=state, pipeline_version=PIPELINE_VERSION, obtained_at=_agora(), **campos)


def _partes(item: MealCandidate | SelectedItem) -> tuple[MealCandidate, list[str] | None]:
    """Candidato e opções escolhidas (None quando o usuário ainda não escolheu)."""
    if isinstance(item, SelectedItem):
        return item.candidate, item.option_labels
    return item, None


def _chave(candidate: MealCandidate, opcoes: list[str] | None) -> str:
    bruto = json.dumps([PIPELINE_VERSION, candidate.merchant_id, candidate.merchant_name, candidate.simulated,
                        candidate.item_id, candidate.name, candidate.description, candidate.image_url, opcoes],
                       ensure_ascii=False)
    return hashlib.sha256(bruto.encode()).hexdigest()


def pipeline_disponivel(settings: Settings) -> bool:
    return bool(settings.gemini_api_key or settings.openrouter_api_key)


async def estimate_nutrition(item: MealCandidate | SelectedItem, settings: Settings) -> NutritionResult:
    """Calorias de uma unidade do item (a quantidade comprada é aplicada por quem chama)."""
    if not pipeline_disponivel(settings):
        return _resultado("unavailable",
                          evidence="Pipeline nutricional não configurada (GEMINI_API_KEY e OPENROUTER_API_KEY ausentes).")

    candidate, opcoes = _partes(item)
    chave = _chave(candidate, opcoes)
    if chave in _cache:
        return _cache[chave]

    base = repositorio(str(settings.calorias_base_path))
    salvo = base.get(chave_produto(item), PIPELINE_VERSION)
    if salvo is not None:
        _cache[chave] = salvo
        return salvo

    try:
        resultado = await asyncio.wait_for(calcular(settings, candidate, opcoes), settings.nutrition_timeout_seconds)
    except (asyncio.TimeoutError, AppError, json.JSONDecodeError, SchemaError, KeyError, ValidationError,
            EstimativaInvalida) as e:
        log.warning("Estimativa nutricional falhou para %s: %s", candidate.name, e)
        return _resultado("error", evidence="Não foi possível obter a informação nutricional agora.")
    if resultado.state == "ready":  # indisponível por queda temporária não pode ficar preso no cache
        _cache[chave] = resultado
        base.put(chave_produto(item), resultado, candidate)
    return resultado


def _com_nutricao(rec: Recommendation, nutricao: NutritionResult) -> Recommendation:
    limitacoes = rec.limitations
    if nutricao.state == "ready":
        limitacoes = [l for l in limitacoes if not l.startswith(LIMITACAO_SEM_NUTRICAO)]
    return rec.model_copy(update={"nutrition": nutricao, "limitations": limitacoes})


async def enrich_recommendations(recommendations: list[Recommendation], settings: Settings) -> list[Recommendation]:
    """Preenche a nutrição das recomendações sem passar do prazo da resposta HTTP.

    O que não termina a tempo volta como "pending" e continua em segundo plano, indo para o cache:
    a próxima busca pelo mesmo item já recebe o resultado.
    """
    if not pipeline_disponivel(settings) or not recommendations:
        return [_com_nutricao(r, await estimate_nutrition(r.candidate, settings)) for r in recommendations]

    limite = asyncio.Semaphore(settings.nutrition_concurrency)

    async def uma(candidate: MealCandidate) -> NutritionResult:
        async with limite:
            return await estimate_nutrition(candidate, settings)

    tarefas = [_tarefa(rec.candidate, lambda c=rec.candidate: uma(c)) for rec in recommendations]
    await asyncio.wait(tarefas, timeout=settings.nutrition_response_budget_seconds)
    return [_com_nutricao(rec, _estado_da_tarefa(t)) for rec, t in zip(recommendations, tarefas)]


async def estimate_selected(selected: SelectedItem, settings: Settings, aguardar: bool = True) -> NutritionResult:
    """Calorias do prato montado (com as opções escolhidas), dentro do prazo da resposta HTTP.

    Com aguardar=False só consulta: devolve o resultado se já terminou, ou "pending" se ainda está calculando.
    """
    if not pipeline_disponivel(settings):
        return await estimate_nutrition(selected, settings)
    chave = _chave(*_partes(selected))
    if chave in _cache:
        return _cache[chave]
    if not aguardar and chave not in _em_andamento:
        return _resultado("error", evidence="O cálculo foi interrompido. Escolha o prato de novo para recalcular.")
    tarefa = _tarefa(selected.candidate, lambda: estimate_nutrition(selected, settings), chave)
    if aguardar:
        await asyncio.wait([tarefa], timeout=settings.nutrition_response_budget_seconds)
    return _estado_da_tarefa(tarefa)


def _tarefa(candidate: MealCandidate, criar, chave: str | None = None) -> asyncio.Task:
    """Reaproveita o cálculo em andamento para o mesmo item, ou inicia um novo em segundo plano."""
    chave = chave or _chave(candidate, None)
    tarefa = _em_andamento.get(chave)
    if tarefa is None or tarefa.done():
        tarefa = asyncio.create_task(criar())
        _em_andamento[chave] = tarefa
        tarefa.add_done_callback(lambda t, c=chave: _em_andamento.pop(c, None) if _em_andamento.get(c) is t else None)
    return tarefa


def _estado_da_tarefa(tarefa: asyncio.Task) -> NutritionResult:
    if not tarefa.done():
        return NutritionResult(state="pending", pipeline_version=PIPELINE_VERSION)
    if tarefa.exception() is not None:
        log.error("Erro inesperado na pipeline nutricional", exc_info=tarefa.exception())
        return _resultado("error", evidence="Não foi possível obter a informação nutricional agora.")
    return tarefa.result()
