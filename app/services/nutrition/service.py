"""Pipeline nutricional como serviço.

Fachada usada pela API: base local de produtos → pipeline (bases, web, estimativas, validação).
Gemini vê a imagem; o OpenRouter faz o texto. Veja pipeline.py e pipeline_calorias_v2.dot.

Sempre devolve um NutritionResult: falhas viram state="error" para não derrubar a busca.
"""
import asyncio
import hashlib
import json
from datetime import datetime, timezone

import httpx
from jsonschema import ValidationError as SchemaError
from pydantic import ValidationError

from app.core import logs
from app.core.config import Settings
from app.core.exceptions import AppError
from app.schemas.macro import MealCandidate, NutritionResult, Recommendation, SelectedItem
from .etapas.estimar import EstimativaInvalida
from .pipeline import PIPELINE_VERSION, calcular
from .produtos import chave_produto, repositorio

LIMITACAO_SEM_NUTRICAO = "Informação nutricional indisponível"

# Resultados prontos por item; estimativas que passam do prazo da resposta terminam aqui em segundo plano.
_cache: dict[str, NutritionResult] = {}
_em_andamento: dict[str, asyncio.Task] = {}
_limites: dict[int, asyncio.Semaphore] = {}  # estimativas simultâneas por loop (limite de uso do provedor)


def _semaforo(settings: Settings) -> asyncio.Semaphore:
    loop = id(asyncio.get_running_loop())
    if loop not in _limites:
        _limites[loop] = asyncio.Semaphore(settings.nutrition_concurrency)
    return _limites[loop]


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
    return settings.nutrition_enabled


async def estimate_nutrition(item: MealCandidate | SelectedItem, settings: Settings) -> NutritionResult:
    """Calorias de uma unidade do item (a quantidade comprada é aplicada por quem chama)."""
    if not pipeline_disponivel(settings):
        return _resultado("unavailable",
                          evidence="Pipeline nutricional não configurada (sem chave do provedor de texto nem do Gemini).")

    candidate, opcoes = _partes(item)
    logs.iniciar_item(candidate.name)
    chave = _chave(candidate, opcoes)
    if chave in _cache:
        logs.info("cache", "HIT na memória → resultado pronto, nada recalculado")
        return _cache[chave]

    base = repositorio(str(settings.calorias_base_path))
    salvo = base.get(chave_produto(item), PIPELINE_VERSION)
    if salvo is not None:
        _cache[chave] = salvo
        logs.info("base local", f"HIT ({chave_produto(item)}) → {salvo.calories:.0f} kcal, método {salvo.method}; "
                                "nada recalculado")
        return salvo
    logs.info("base local", f"MISS ({chave_produto(item)}) → calculando")

    try:
        resultado = await asyncio.wait_for(calcular(settings, candidate, opcoes), settings.nutrition_timeout_seconds)
    except (asyncio.TimeoutError, AppError, json.JSONDecodeError, SchemaError, KeyError, ValidationError,
            EstimativaInvalida) as e:
        causa = "tempo esgotado (NUTRITION_TIMEOUT_SECONDS)" if isinstance(e, asyncio.TimeoutError) else logs.curto(e)
        logs.aviso("ERRO", f"estimativa falhou: {causa}")
        return _resultado("error", evidence="Não foi possível obter a informação nutricional agora.")
    if resultado.state == "ready":  # indisponível por queda temporária não pode ficar preso no cache
        _cache[chave] = resultado
        base.put(chave_produto(item), resultado, candidate)
        logs.info("base local", f"gravado em {settings.calorias_base_path}")
    else:
        logs.info("base local", f"não gravado (estado {resultado.state}); será recalculado na próxima vez")
    return resultado


def _com_nutricao(rec: Recommendation, nutricao: NutritionResult) -> Recommendation:
    limitacoes = rec.limitations
    if nutricao.state == "ready":
        limitacoes = [l for l in limitacoes if not l.startswith(LIMITACAO_SEM_NUTRICAO)]
    return rec.model_copy(update={"nutrition": nutricao, "limitations": limitacoes})


def _iniciar(rec: Recommendation, settings: Settings) -> asyncio.Task:
    """Calcula a nutrição de uma recomendação em segundo plano (no máximo N cálculos ao mesmo tempo)."""
    async def uma() -> NutritionResult:
        async with _semaforo(settings):
            return await estimate_nutrition(rec.candidate, settings)
    return _tarefa(rec.candidate, uma)


async def enrich_recommendations(recommendations: list[Recommendation], settings: Settings,
                                 prazo: float | None = None) -> list[Recommendation]:
    """Inicia a nutrição das recomendações e espera no máximo `prazo` segundos.

    O que não termina a tempo volta como "pending" e continua em segundo plano, indo para o cache;
    refresh_recommendations entrega o resultado quando ficar pronto.
    """
    if not pipeline_disponivel(settings) or not recommendations:
        return [_com_nutricao(r, await estimate_nutrition(r.candidate, settings)) for r in recommendations]
    tarefas = [_iniciar(rec, settings) for rec in recommendations]
    espera = settings.nutrition_response_budget_seconds if prazo is None else prazo
    if espera > 0:
        await asyncio.wait(tarefas, timeout=espera)
    return [_com_nutricao(rec, _estado_da_tarefa(t)) for rec, t in zip(recommendations, tarefas)]


def refresh_recommendations(recommendations: list[Recommendation], settings: Settings) -> list[Recommendation]:
    """Atualiza, sem esperar, as recomendações ainda "pending".

    Se o cálculo se perdeu (ex.: o servidor reiniciou), ele é iniciado de novo em segundo plano.
    """
    if not pipeline_disponivel(settings):
        return list(recommendations)
    atualizadas = []
    for rec in recommendations:
        if rec.nutrition.state != "pending":
            atualizadas.append(rec)
            continue
        chave = _chave(rec.candidate, None)
        nutricao = _cache.get(chave) or _estado_da_tarefa(_iniciar(rec, settings))
        atualizadas.append(_com_nutricao(rec, nutricao))
    return atualizadas


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
        logs.aviso("ERRO", f"erro inesperado na pipeline: {logs.curto(tarefa.exception())}")
        return _resultado("error", evidence="Não foi possível obter a informação nutricional agora.")
    return tarefa.result()
