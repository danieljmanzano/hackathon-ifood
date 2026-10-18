import asyncio
import json

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.domain import rank
from app.schemas.macro import MealRequest, UserProfile
from app.services import llm_meal_intent as service
from app.services.mock_ifood import catalog
from app.services.openrouter import OpenRouterError


@pytest.fixture(autouse=True)
def clear_cache():
    service._cache.clear()
    yield
    service._cache.clear()


def settings(**overrides):
    return Settings(_env_file=None, openrouter_api_key='test-key', intent_llm_enabled=True, **overrides)


def result(**changes):
    return json.dumps({
        'goals': ['large_portion', 'protein'], 'food_query': '',
        'context_summary': 'Você treinou musculação; vou priorizar uma refeição mais substanciosa.',
        'inferences': ['Uma porção maior pode combinar com o contexto, sem assumir seu nível de fome.'],
        'budget_cents': None, 'party_size': None, 'max_delivery_minutes': None,
        **changes,
    })


def test_llm_context_reaches_ranking_and_cache_preserves_rotation(monkeypatch):
    calls = []
    async def complete(messages, **kwargs):
        calls.append(messages)
        assert 'message' in messages[-1]['content']
        assert 'test-key' not in str(messages)
        return result()
    monkeypatch.setattr(service, 'chat_completion', complete)
    request = MealRequest(text='Treinei musculação hoje')
    intent = asyncio.run(service.interpret_intent(request, settings()))
    assert intent.interpretation_source == 'llm'
    assert set(intent.inferred_goals) == {'large_portion', 'protein'}
    assert not intent.food_query
    first = rank(catalog(), request, UserProfile(id='user'), None, intent=intent)
    assert all(r.candidate.features.portion_size in ('large', 'sharing') for r in first)
    assert all('protein' in r.candidate.features.tags for r in first)
    assert 'Você disse que está com muita fome' not in first[0].reasons[0]
    cached = asyncio.run(service.interpret_intent(request, settings()))
    assert cached == intent
    assert len(calls) == 1
    second = rank(catalog(), request, UserProfile(id='user'), None,
                  recently_shown=[(r.candidate.merchant_id, r.candidate.item_id) for r in first], intent=cached)
    assert [r.candidate.item_id for r in first] != [r.candidate.item_id for r in second]


def test_pre_workout_context_prefers_light_small_portions(monkeypatch):
    async def complete(*args, **kwargs):
        return result(goals=['light', 'small_portion'],
                      context_summary='Você vai treinar em breve; vou favorecer algo mais leve.')
    monkeypatch.setattr(service, 'chat_completion', complete)
    request = MealRequest(text='Quero uma refeição pré-treino')
    intent = asyncio.run(service.interpret_intent(request, settings()))
    assert intent.interpretation_source == 'llm'
    assert intent.food_query == ''
    items = rank(catalog(), request, UserProfile(id='user'), None, intent=intent)
    assert all('light' in r.candidate.features.tags and r.candidate.features.portion_size == 'small' for r in items)


def test_explicit_limits_and_appetite_override_model_inferences(monkeypatch):
    async def complete(*args, **kwargs):
        return result(goals=['small_portion', 'protein'], food_query='frango', budget_cents=9999,
                      context_summary='Vou respeitar sua pouca fome e o pedido de frango.')
    monkeypatch.setattr(service, 'chat_completion', complete)
    request = MealRequest(text='treinei, estou com pouca fome, quero frango até R$ 25')
    intent = asyncio.run(service.interpret_intent(request, settings()))
    assert intent.budget_cents == 2500
    assert intent.food_query == 'frango'
    assert intent.goals == ['small_portion', 'protein']
    assert 'small_portion' not in intent.inferred_goals


@pytest.mark.parametrize('response', [
    'not json', result(goals=['place_order']), result(party_size=100),
    result(goals=['large_portion', 'small_portion']), result(tool='submit_order'),
])
def test_invalid_or_action_like_outputs_fall_back_to_rules(monkeypatch, response):
    async def complete(*args, **kwargs):
        return response
    monkeypatch.setattr(service, 'chat_completion', complete)
    intent = asyncio.run(service.interpret_intent(MealRequest(text='muita fome'), settings()))
    assert intent.interpretation_source == 'rules'
    assert intent.goals == ['large_portion']
    assert intent.fallback_reason == 'invalid_response'


def test_model_cannot_reverse_explicit_negations(monkeypatch):
    async def complete(*args, **kwargs):
        return result(goals=['large_portion', 'fast'])
    monkeypatch.setattr(service, 'chat_completion', complete)
    intent = asyncio.run(service.interpret_intent(MealRequest(text='não estou com muita fome e sem pressa'), settings()))
    assert intent.goals == ['small_portion']
    assert intent.fallback_reason == 'invalid_response'


@pytest.mark.parametrize('failure, reason', [('timeout', 'timeout'), ('provider', 'unavailable')])
def test_provider_failure_keeps_search_available(monkeypatch, failure, reason):
    async def complete(*args, **kwargs):
        if failure == 'timeout':
            await asyncio.sleep(1)
        raise OpenRouterError('provider unavailable')
    monkeypatch.setattr(service, 'chat_completion', complete)
    intent = asyncio.run(service.interpret_intent(MealRequest(text='muita fome'), settings(intent_llm_timeout_seconds=0.01)))
    assert intent.goals == ['large_portion']
    assert intent.fallback_reason == reason


def test_no_key_and_disabled_mode_never_call_provider(monkeypatch):
    async def unexpected(*args, **kwargs):
        raise AssertionError('External request')
    monkeypatch.setattr(service, 'chat_completion', unexpected)
    request = MealRequest(text='muita fome')
    intent = asyncio.run(service.interpret_intent(request, Settings(_env_file=None, openrouter_api_key='', intent_llm_enabled=True)))
    assert intent.fallback_reason == 'not_configured'
    intent = asyncio.run(service.interpret_intent(request, Settings(_env_file=None, intent_llm_enabled=False)))
    assert intent.fallback_reason == 'disabled'


def test_api_uses_validated_llm_intent_not_local_reparse(tmp_path, monkeypatch):
    import app.main as main
    configured = settings(database_path=tmp_path / 'test.sqlite3', ifood_mode='mock', openai_api_key='')
    async def complete(*args, **kwargs):
        return result()
    monkeypatch.setattr(service, 'chat_completion', complete)
    monkeypatch.setattr(main, 'get_settings', lambda: configured)
    app = main.create_app()
    app.dependency_overrides[get_settings] = lambda: configured
    with TestClient(app) as client:
        client.get('/api/session')
        client.put('/api/session/address', json={'address_id': 'demo-address'})
        response = client.post('/api/search', json={'text': 'Hoje foi dia de musculação na academia'})
        assert response.status_code == 200
        data = response.json()
        assert data['request_intent']['interpretation_source'] == 'llm'
        assert all(r['candidate']['features']['portion_size'] in ('large', 'sharing') for r in data['recommendations'])
        assert 'musculação' in data['messages'][-1]['text']


@pytest.mark.parametrize('message, fallback_expected', [
    ('broken-model is not a valid model ID', True),
    ('Invalid input: unsupported field', False),
])
def test_openrouter_only_retries_400_when_model_is_invalid(monkeypatch, message, fallback_expected):
    import httpx
    from app.services import openrouter
    calls = []
    original_client = httpx.AsyncClient
    def handler(request):
        payload = json.loads(request.content)
        calls.append(payload['model'])
        if payload['model'] == 'broken-model':
            return httpx.Response(400, json={'error': {'message': message}})
        return httpx.Response(200, json={'choices': [{'message': {'content': 'OK'}}]})
    monkeypatch.setattr(openrouter.httpx, 'AsyncClient', lambda **kwargs:
                        original_client(**kwargs, transport=httpx.MockTransport(handler)))
    configured = settings(openrouter_model='broken-model', openrouter_fallback_models=['configured-fallback'])
    if fallback_expected:
        output = asyncio.run(openrouter.chat_completion([{'role': 'user', 'content': 'OK'}], settings=configured))
        assert output == 'OK'
        assert calls == ['broken-model', 'configured-fallback']
    else:
        with pytest.raises(OpenRouterError):
            asyncio.run(openrouter.chat_completion([{'role': 'user', 'content': 'OK'}], settings=configured))
        assert calls == ['broken-model']


def test_training_time_is_not_delivery_deadline_and_fallback_understands_context():
    from app.services.meal_intent import parse_intent
    pre = parse_intent(MealRequest(text='Vou treinar daqui a 30 minutos, quero um pré-treino'))
    assert pre.max_delivery_minutes is None
    assert pre.budget_cents is None
    assert 'fast' not in pre.goals
    assert set(pre.goals) == {'light', 'small_portion'}
    post = parse_intent(MealRequest(text='Treinei musculação hoje, mas estou com pouca fome'))
    assert post.goals == ['small_portion', 'protein']
    assert post.inferred_goals == ['protein']
    assert 'large_portion' not in post.goals
