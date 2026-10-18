"""Enriquecimento incremental: catálogo real → fila persistida → pipeline existente."""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from app.core.nutrition_budget import Budget, current_budget
from app.schemas.macro import MealCandidate, NutritionResult
from app.storage.catalog import CatalogStore
from app.services.nutrition.produtos import chave_produto
from app.services.nutrition.pipeline import PIPELINE_VERSION

log = logging.getLogger(__name__)


def job_key(candidate):
    return f'{PIPELINE_VERSION}:{chave_produto(candidate)}'


def observe_and_enqueue(recommendations, settings):
    """A ordem do ranking define a prioridade; somente N produtos novos por busca entram na fila."""
    from app.services.nutrition.service import cached_candidates
    store = CatalogStore(settings.database_path)
    known = cached_candidates([r.candidate for r in recommendations], settings)
    queued = 0
    for rec in recommendations:
        c = rec.candidate
        if c.simulated:
            continue
        store.observe(c, job_key(c))
        if (c.merchant_id, c.item_id) not in known and queued < settings.catalog_products_per_search:
            store.enqueue(c, job_key(c))
            queued += 1
    log.info('catalog.enqueued observed=%s queued=%s', len(recommendations), queued)
    return known


async def process_one(settings):
    """Uma tarefa por worker. Lease e reserva SQLite impedem execução duplicada e estouro da cota."""
    from app.services.nutrition.service import estimate_nutrition, cached_candidates
    store = CatalogStore(settings.database_path)
    job = store.claim(settings.nutrition_timeout_seconds, settings.catalog_max_attempts)
    if not job:
        return False
    c = MealCandidate.model_validate_json(job['payload'])
    if cached_candidates([c], settings):
        store.finish(job['id'], 'ready', attempted=False)
        return True
    budget = Budget(store, settings, job['id'])
    token = current_budget.set(budget)
    try:
        # Fontes em cascata e uma amostra: o pipeline completo continua disponível nas outras rotas.
        economical = settings.model_copy(update={'calorias_estimar_sempre': False, 'calorias_amostras': 1})
        result = await estimate_nutrition(c, economical)
        if result.state == 'ready':
            store.finish(job['id'], 'ready')
        elif budget.reason == 'daily_limit':
            tomorrow = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            store.finish(job['id'], 'deferred', budget.reason,
                         (tomorrow-datetime.now(timezone.utc)).total_seconds(), attempted=False)
        else:
            store.finish(job['id'], 'error', budget.reason or result.state,
                         settings.catalog_retry_seconds)
        log.info('catalog.processed state=%s budget=%s', result.state, budget.reason)
    except asyncio.CancelledError:
        store.finish(job['id'], 'queued', 'shutdown', attempted=False)
        raise
    except Exception:
        log.exception('catalog.processing_failed')
        store.finish(job['id'], 'error', 'processing_failed', settings.catalog_retry_seconds)
    finally:
        current_budget.reset(token)
    return True


async def worker(settings):
    from app.services.nutrition_batch_search import process_search
    CatalogStore(settings.database_path).recover_searches()
    while True:
        try:
            if await process_search(settings):
                continue
            if settings.nutrition_enabled:
                processed = await asyncio.gather(*(process_one(settings) for _ in range(min(3, settings.nutrition_concurrency))))
                if any(processed):
                    continue
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception('catalog.worker_failed')
        await asyncio.sleep(2)


def enrichment_results(recommendations, settings):
    """Resposta imediata, sem criar tarefas fora da fila; unknown não é uma adequação verificada."""
    from app.services.nutrition.service import _com_nutricao
    known = observe_and_enqueue(recommendations[:10], settings)
    store = CatalogStore(settings.database_path)
    with store.connection() as db:
        states = {row['id']: row['state'] for row in db.execute('SELECT id,state FROM nutrition_jobs')}
    result = []
    for rec in recommendations:
        nutrition = known.get((rec.candidate.merchant_id, rec.candidate.item_id))
        if nutrition is None:
            state = states.get(job_key(rec.candidate))
            nutrition = NutritionResult(state='pending' if settings.nutrition_enabled and state in ('queued','running') else 'unavailable',
                                        pipeline_version=PIPELINE_VERSION,
                                        evidence='Enriquecimento em fila ou pausado pelo limite de uso; adequação não verificada.')
        result.append(_com_nutricao(rec, nutrition))
    return result
