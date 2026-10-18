import asyncio
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import AsyncMock

import httpx
import pytest

from app.core.config import Settings
from app.core.nutrition_budget import Budget, NutritionBudgetExceeded, current_budget, reserve_call
from app.domain import rank
from app.schemas.macro import MealRequest, NutritionPreferences, Recommendation, UserProfile
from app.services import catalog_enrichment as catalog
from app.services.catalog_reviews import attach_reviews
from app.services.nutrition import service
from app.services.nutrition.produtos import chave_produto, repositorio
from app.services.review_recommendations import review_context, review_signal
from app.storage.catalog import CatalogStore
from app.storage.database import Database
from tests.nutricao_comum import candidato
from tests.test_nutricao_service import _pronto


@pytest.fixture
def config(tmp_path):
    service._cache.clear()
    repositorio.cache_clear()
    return Settings(_env_file=None, database_path=tmp_path/'catalog.sqlite3',
                    calorias_base_path=tmp_path/'nutrition.json', ifood_mode='live',
                    openrouter_api_key='test', nutrition_provider='openrouter',
                    catalog_retry_seconds=1, intent_llm_enabled=False, busca_replanejar=False,
                    calorias_log='off', busca_log='off')


def recs(n):
    return [Recommendation(candidate=candidato(item_id=f'i-{i}'), reasons=[], limitations=[]) for i in range(n)]


def test_queue_is_limited_persistent_and_cache_is_reused(config, monkeypatch):
    calls = []
    async def calculate(settings, candidate, options):
        assert current_budget.get() is not None
        assert settings.calorias_estimar_sempre is False
        reserve_call('test')
        calls.append(candidate.item_id)
        return _pronto().model_copy(update={'pipeline_version': catalog.PIPELINE_VERSION})
    monkeypatch.setattr(service, 'calcular', calculate)
    pending = asyncio.run(service.enrich_recommendations(recs(10), config))
    assert sum(r.nutrition.state == 'pending' for r in pending) == 3
    store = CatalogStore(config.database_path)
    assert store.status()['jobs'] == {'queued': 3}
    assert store.status()['observed_products'] == 10
    for _ in range(3):
        assert asyncio.run(catalog.process_one(config))
    assert not asyncio.run(catalog.process_one(config))
    service._cache.clear()  # simula reinício; a nutrição continua no disco
    refreshed = service.refresh_recommendations(pending, config)
    assert sum(r.nutrition.state == 'ready' for r in refreshed) == 3
    assert len(calls) == 3
    assert store.status()['calls'] == 3
    # Polling não cria trabalho para os sete que ficaram fora do limite.
    assert store.status()['jobs'] == {'ready': 3}


def test_composition_invalidates_cache_but_price_and_temporary_image_do_not(config):
    c = candidato()
    result = _pronto().model_copy(update={'pipeline_version': catalog.PIPELINE_VERSION})
    repositorio(str(config.calorias_base_path)).put(chave_produto(c), result, c)
    price = c.model_copy(update={'price_cents': 9999, 'image_url': 'https://image/new-token'})
    changed = c.model_copy(update={'description': 'Receita nova, porção 800 g'})
    assert chave_produto(c) == chave_produto(price)
    assert chave_produto(c) != chave_produto(changed)
    assert service.cached_candidates([price], config)
    assert not service.cached_candidates([changed], config)


def test_atomic_daily_reservations_survive_restart(config):
    def reserve(_):
        return CatalogStore(config.database_path).reserve('same', 3, 10, 20)
    CatalogStore(config.database_path)
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(reserve, range(12)))
    assert results.count(None) == 3
    assert CatalogStore(config.database_path).status()['calls'] == 3


def test_expired_running_job_is_recovered_and_retries_are_capped(config, monkeypatch):
    store = CatalogStore(config.database_path)
    c = candidato()
    store.enqueue(c, catalog.job_key(c))
    assert store.claim(1, 2)
    with store.connection() as db:
        db.execute('UPDATE nutrition_jobs SET lease=0')
    assert store.claim(1, 2)
    store.finish(catalog.job_key(c), 'error')
    assert store.claim(1, 2)
    store.finish(catalog.job_key(c), 'error')
    assert store.claim(1, 2) is None


def test_daily_budget_defers_without_burning_attempts(config, monkeypatch):
    config = config.model_copy(update={'catalog_calls_per_day': 0})
    async def calculate(*args):
        reserve_call('test')
    monkeypatch.setattr(service, 'calcular', calculate)
    catalog.observe_and_enqueue(recs(1), config)
    asyncio.run(catalog.process_one(config))
    store = CatalogStore(config.database_path)
    with store.connection() as db:
        row = db.execute('SELECT * FROM nutrition_jobs').fetchone()
    assert row['state'] == 'deferred' and row['attempts'] == 0
    assert row['reason'] == 'daily_limit'
    assert store.status()['calls'] == 0
    assert not asyncio.run(catalog.process_one(config))


def test_http_retries_and_fallback_count_before_sending(config, monkeypatch):
    from app.services import openrouter
    sent = []
    async def post(self, url, **kwargs):
        sent.append(kwargs['json'])
        return httpx.Response(429, json={'error': 'limit'})
    monkeypatch.setattr(httpx.AsyncClient, 'post', post)
    config = config.model_copy(update={'catalog_calls_per_product': 1})
    budget = Budget(CatalogStore(config.database_path), config, 'one-product')
    async def run():
        token = current_budget.set(budget)
        try:
            with pytest.raises(NutritionBudgetExceeded):
                await openrouter.chat_completion([{'role':'user','content':'test'}], settings=config)
        finally:
            current_budget.reset(token)
    asyncio.run(run())
    assert len(sent) == 1
    assert sent[0]['max_tokens'] == config.catalog_max_output_tokens
    assert budget.store.status()['calls'] == 1


def test_live_reviews_are_stable_labeled_and_opt_out_restores_real_context(config):
    db = Database(config.database_path)
    profile = UserProfile(id='user')
    ctx = review_context(db, profile.id, False, profile)
    c = candidato()
    attach_reviews(ctx, [c], config, db, profile)
    signal, reasons = review_signal(c, ctx)
    assert not c.simulated and signal.simulated and signal.review_count == 3
    assert any('simuladas' in reason for reason in reasons)
    again = review_context(db, profile.id, False, profile)
    attach_reviews(again, [c], config, db, profile)
    assert [(r.id,r.rating) for r in ctx.community] == [(r.id,r.rating) for r in again.community]
    attach_reviews(again, [c], config, db, profile)
    assert len(again.community) == 3
    off = review_context(db, profile.id, False, profile)
    attach_reviews(off, [c], config.model_copy(update={'live_mock_reviews':False}), db, profile)
    assert not off.community and not off.synthetic_catalog
    assert not review_signal(c, off)[0].simulated
    assert db.reviews(False) == []


def test_numeric_limits_exclude_known_failures_but_unknown_is_explicit(config):
    candidates = [candidato(item_id=str(i)) for i in range(3)]
    known = {(c.merchant_id,c.item_id): _pronto().model_copy(update={'calories': calories, 'minimum':calories-10,'maximum':calories+10})
             for c,calories in zip(candidates,[400,900])}
    profile = UserProfile(id='u', nutrition_preferences=NutritionPreferences(max_calories=600))
    results = rank(candidates, MealRequest(text='pizza'), profile, None, nutrition_by_item=known, strict_nutrition=True)
    assert [r.candidate.item_id for r in results] == ['0','2']
    assert any('Não foi possível verificar' in s or 'ainda não verificadas' in s for s in results[1].limitations)


def test_skill_is_registered_and_used_only_under_nutrition_context(config, monkeypatch):
    from app.agent.skills import load_skill
    from app.services.nutrition.etapas import llm
    captured = []
    async def complete(messages, **kwargs):
        captured.append(messages[0]['content'])
        return '{}'
    monkeypatch.setattr(llm, 'chat_completion_fallback', complete)
    async def run():
        await llm.perguntar_json(config,'base','item',{'type':'object'})
        token = current_budget.set(Budget(CatalogStore(config.database_path),config,'x'))
        try:
            await llm.perguntar_json(config,'base','item',{'type':'object'})
        finally:
            current_budget.reset(token)
    asyncio.run(run())
    assert captured[0] == 'base'
    assert load_skill('nutrition_enrichment').content in captured[1]


def test_live_api_search_queue_polling_and_limits(config, monkeypatch):
    from fastapi.testclient import TestClient
    import app.main as main
    from app.api.endpoints import macro
    from app.core.config import get_settings
    from app.schemas.macro import Address
    class Provider:
        async def addresses(self):
            return [Address(id='real-address',label='Casa',formatted='Endereço de teste',latitude=-23,longitude=-46)]
        async def search(self, *args):
            return [r.candidate for r in recs(5)]
    async def calculate(*args):
        reserve_call('test')
        return _pronto().model_copy(update={'pipeline_version':catalog.PIPELINE_VERSION})
    monkeypatch.setattr(main, 'get_settings', lambda: config)
    monkeypatch.setattr(service, 'calcular', calculate)
    app = main.create_app()
    app.dependency_overrides[get_settings] = lambda: config
    app.dependency_overrides[macro.get_provider] = Provider
    # Sem lifespan: o worker é avançado explicitamente para testar os dois momentos da resposta.
    client = TestClient(app)
    assert client.get('/api/session').status_code == 200
    assert client.put('/api/session/address',json={'address_id':'real-address'}).status_code == 200
    response = client.post('/api/search',json={'text':'pizza até 500 kcal'})
    assert response.status_code == 200
    assert response.json()['recommendations'] == []
    assert response.json()['nutrition_search']['state'] == 'pending'
    from app.services.nutrition_batch_search import process_search
    asyncio.run(process_search(config,provider=Provider()))
    after = client.get('/api/recommendations/nutrition').json()
    # Os cinco itens do catálogo são 600 kcal e não podem ser oferecidos como <=500.
    assert after['recommendations'] == []
    assert after['nutrition_search']['tested'] == 5
    assert after['nutrition_search']['reason'] == 'catalog_exhausted'
    status = client.get('/api/catalog/enrichment/status').json()
    assert status['calls'] == 5
    assert client.get('/api/health').json()['live_orders_enabled'] is False
    client.close()


def test_selected_addon_quantities_do_not_share_memory_cache(config, monkeypatch):
    from app.schemas.macro import SelectedItem, SelectedOption
    count = []
    async def calculate(*args):
        count.append(1)
        return _pronto().model_copy(update={'pipeline_version':catalog.PIPELINE_VERSION})
    monkeypatch.setattr(service, 'calcular', calculate)
    def selected(qty):
        return SelectedItem(candidate=candidato(), quantity=1,
                            options=[SelectedOption(group_id='g',option_id='o',quantity=qty)],
                            option_labels=['Queijo'], unit_total_cents=3000)
    async def run():
        await service.estimate_nutrition(selected(1),config)
        await service.estimate_nutrition(selected(2),config)
        await service.estimate_nutrition(selected(1),config)
    asyncio.run(run())
    assert len(count) == 2


def test_selected_and_worker_share_concurrency_limit(config, monkeypatch):
    active = 0
    peak = 0
    async def calculate(*args):
        nonlocal active, peak
        active += 1
        peak = max(peak,active)
        await asyncio.sleep(.01)
        active -= 1
        return _pronto().model_copy(update={'pipeline_version':catalog.PIPELINE_VERSION})
    monkeypatch.setattr(service, 'calcular', calculate)
    async def run():
        await asyncio.gather(*(service.estimate_nutrition(candidato(item_id=str(i)),config) for i in range(3)))
    asyncio.run(run())
    assert peak == min(3,config.nutrition_concurrency)
