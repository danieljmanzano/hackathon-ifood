import asyncio
import json
import logging

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.core import search_logs
from app.domain import rank
from app.schemas.macro import MealCandidate, MealRequest, UserProfile
from app.services import llm_meal_intent
from app.services.openrouter import OpenRouterError


class Collector(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(record)


@pytest.fixture
def records():
    collector = Collector()
    loggers = [logging.getLogger(name) for name in ('app.busca', 'app.nutricao')]
    levels = [logger.level for logger in loggers]
    for logger in loggers:
        logger.addHandler(collector)
        logger.setLevel(logging.DEBUG)
    yield collector.records
    for logger, level in zip(loggers, levels):
        logger.removeHandler(collector)
        logger.setLevel(level)


@pytest.fixture
def client(tmp_path, monkeypatch, records):
    import app.main as main
    settings = Settings(_env_file=None, database_path=tmp_path / 'logs.sqlite3',
                        ifood_mode='mock', intent_llm_enabled=False, busca_log='detalhe', calorias_log='off',
                        openrouter_api_key='', openai_api_key='')
    monkeypatch.setattr(main, 'get_settings', lambda: settings)
    application = main.create_app()
    application.dependency_overrides[get_settings] = lambda: settings
    with TestClient(application) as client:
        client.get('/api/session')
        yield client


def events(records):
    return [r for r in records if hasattr(r, 'event')]


def test_search_logs_have_correlation_timings_filters_and_no_private_text(client, records):
    session = client.get('/api/session').json()
    client.put('/api/profile', json={**session['profile'], 'restrictions': ['PRIVATE-INGREDIENT']})
    client.put('/api/session/address', json={'address_id': 'demo-address'})
    response = client.post('/api/search', json={'text': 'muita fome, frango até R$ 30 PRIVATE-MESSAGE'})
    assert response.status_code == 200
    trace_id = response.headers['X-Search-Id']
    entries = events(records)
    assert all(r.search_id == trace_id for r in entries)
    names = [r.event for r in entries]
    expected = ['search.started', 'intent.ready', 'catalog.completed', 'reviews.ready',
                'ranking.started', 'ranking.completed', 'nutrition.prepared', 'search.completed']
    assert [names.index(name) for name in expected] == sorted(names.index(name) for name in expected)
    summary = next(r.fields for r in entries if r.event == 'ranking.completed')
    assert summary['candidate_count'] == summary['eligible_count'] + sum(summary['excluded'].values())
    assert summary['result_count'] == len(response.json()['recommendations'])
    assert len(summary['selected']) == summary['result_count']
    assert summary['sort_order'] == ['relevance', 'intent_score', 'score']
    assert all(r.fields['duration_ms'] >= 0 for r in entries if 'duration_ms' in r.fields)
    text = '\n'.join(r.getMessage() for r in records)
    assert 'PRIVATE-MESSAGE' not in text
    assert 'PRIVATE-INGREDIENT' not in text
    assert session['id'] not in text
    assert 'Rua Exemplo' not in text


def test_search_failure_records_stage_and_does_not_log_exception_body(client, records, monkeypatch):
    from app.api.endpoints import macro
    from app.core.exceptions import MacroError
    class FailingProvider:
        async def search(self, *args):
            raise MacroError('PRIVATE-PROVIDER-ERROR', 502)
    client.put('/api/session/address', json={'address_id': 'demo-address'})
    client.app.dependency_overrides[macro.get_provider] = lambda: FailingProvider()
    response = client.post('/api/search', json={'text': 'almoço'})
    assert response.status_code == 502
    failure = next(r for r in events(records) if r.event == 'search.failed')
    assert failure.fields['stage'] == 'catalog'
    assert failure.fields['status_code'] == 502
    assert failure.fields['error_type'] == 'MacroError'
    assert not any(r.event == 'search.completed' for r in events(records))
    assert 'PRIVATE-PROVIDER-ERROR' not in '\n'.join(r.getMessage() for r in records)
    records.clear()
    search_logs.event('probe')
    assert events(records)[0].search_id is None


def test_ranking_details_explain_filters_and_rotation(records):
    def item(mid, **changes):
        return MealCandidate(merchant_id=mid, merchant_name=mid, item_id=mid,
                             name='Prato', description='Arroz', price_cents=2500).model_copy(update=changes)
    candidates = [item('off', available=False), item('expensive', price_cents=4000),
                  item('disliked', description='PRIVATE-DISLIKE'),
                  item('restricted', description='PRIVATE-RESTRICTION'), item('allowed')]
    rank(candidates, MealRequest(text='almoço'), UserProfile(id='test', dislikes=['PRIVATE-DISLIKE'],
         restrictions=['PRIVATE-RESTRICTION']), 3000, recently_shown=[('allowed', 'allowed')])
    rejected = [r.fields['reason'] for r in events(records) if r.event == 'ranking.rejected']
    assert set(rejected) == {'unavailable', 'budget', 'dislike', 'restriction'}
    selected = next(r.fields['selected'] for r in events(records) if r.event == 'ranking.completed')
    assert selected[0]['rotation_penalty'] == 2.5
    assert selected[0]['reviews_score'] == 0
    assert 'PRIVATE-' not in '\n'.join(r.getMessage() for r in records)


def test_concurrent_requests_keep_separate_trace_ids(records):
    async def task():
        with search_logs.trace_search('mock') as trace:
            await asyncio.sleep(0)
            search_logs.event('probe', expected_id=trace.id)
            return trace.id
    async def scenario():
        return await asyncio.gather(task(), task())
    ids = asyncio.run(scenario())
    assert len(set(ids)) == 2
    assert all(r.search_id == r.fields['expected_id'] for r in events(records) if r.event == 'probe')
    search_logs.event('outside')
    assert events(records)[-1].search_id is None


def test_intent_cache_and_fallback_have_safe_logs(records, monkeypatch):
    llm_meal_intent._cache.clear()
    async def complete(*args, **kwargs):
        assert kwargs['log_content'] is False
        return json.dumps({'goals': ['large_portion'], 'context_summary': 'PRIVATE-MODEL-OUTPUT',
                           'food_query': '', 'inferences': []})
    monkeypatch.setattr(llm_meal_intent, 'chat_completion', complete)
    settings = Settings(_env_file=None, intent_llm_enabled=True, openrouter_api_key='PRIVATE-API-KEY')
    request = MealRequest(text='muita fome PRIVATE-PROMPT')
    async def scenario():
        with search_logs.trace_search('mock'):
            await llm_meal_intent.interpret_intent(request, settings)
            await llm_meal_intent.interpret_intent(request, settings)
    asyncio.run(scenario())
    assert any(r.event == 'intent.llm_completed' for r in events(records))
    assert any(r.event == 'intent.cache_hit' for r in events(records))
    async def fail(*args, **kwargs):
        raise OpenRouterError('PRIVATE-ERROR-BODY')
    monkeypatch.setattr(llm_meal_intent, 'chat_completion', fail)
    llm_meal_intent._cache.clear()
    asyncio.run(llm_meal_intent.interpret_intent(request, settings))
    assert any(r.event == 'intent.fallback' and r.fields['reason'] == 'unavailable' for r in events(records))
    assert 'PRIVATE-' not in '\n'.join(r.getMessage() for r in records)
    llm_meal_intent._cache.clear()


def test_logging_levels_are_independent_from_nutrition(records):
    parent = logging.getLogger('app')
    level = parent.level
    try:
        parent.setLevel(logging.WARNING)
        search_logs.configurar_busca_logs('resumo')
        search_logs.event('summary')
        search_logs.event('details', level=logging.DEBUG)
        assert [r.event for r in events(records)] == ['summary']
        records.clear()
        search_logs.configurar_busca_logs('off')
        search_logs.event('summary')
        search_logs.event('failure', level=logging.WARNING)
        assert [r.event for r in events(records)] == ['failure']
    finally:
        parent.setLevel(level)


def test_intent_client_omits_response_content_even_at_debug_level(records, monkeypatch):
    import httpx
    from app.services import openrouter
    original = httpx.AsyncClient
    responses = [httpx.Response(200, json={'choices': [{'message': {'content': 'PRIVATE-MODEL-OUTPUT'}}]}),
                 httpx.Response(400, json={'error': {'message': 'PRIVATE-ERROR-BODY'}})]
    monkeypatch.setattr(openrouter.httpx, 'AsyncClient', lambda **kwargs:
                        original(**kwargs, transport=httpx.MockTransport(lambda _: responses.pop(0))))
    settings = Settings(_env_file=None, openrouter_api_key='PRIVATE-KEY', openrouter_model='safe-model',
                        openrouter_fallback_models=[])
    async def scenario():
        result = await openrouter.chat_completion([{'role': 'user', 'content': 'PRIVATE-PROMPT'}],
                                                 settings=settings, log_content=False)
        assert result == 'PRIVATE-MODEL-OUTPUT'
        with pytest.raises(OpenRouterError) as error:
            await openrouter.chat_completion([{'role': 'user', 'content': 'PRIVATE-PROMPT'}],
                                             settings=settings, log_content=False)
        assert 'PRIVATE-' not in str(error.value)
    asyncio.run(scenario())
    assert 'PRIVATE-' not in '\n'.join(record.getMessage() for record in records)
