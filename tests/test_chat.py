import json

import pytest
from pydantic import SecretStr
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from tests.test_review_endpoint import checkout, confirm, settled


@pytest.fixture
def client(tmp_path, monkeypatch):
    import app.main as main
    settings = Settings(_env_file=None, database_path=tmp_path / 'chat.sqlite3', ifood_mode='mock',
                        intent_llm_enabled=False, openrouter_api_key='', openai_api_key='', calorias_base_path=tmp_path / 'nutrition.json')
    monkeypatch.setattr(main, 'get_settings', lambda: settings)
    application = main.create_app()
    application.dependency_overrides[get_settings] = lambda: settings
    with TestClient(application) as client:
        client.get('/api/session')
        yield client


def test_context_is_saved_without_address_or_unrequested_search(client):
    payload = {'text': 'Meu objetivo é ganhar massa e hoje só comi frutas', 'message_id': 'context-1'}
    response = client.post('/api/chat', json=payload)
    assert response.status_code == 200, response.text
    session = response.json()
    assert session['last_chat_action'] == 'context'
    assert session['profile']['diet_plan']['goal'] == 'gain_muscle'
    assert session['recommendations'] == []
    assert session['order'] is None
    assert session['messages'][-2]['text'] == payload['text']
    assert client.post('/api/chat', json=payload).status_code == 200
    assert len(client.get('/api/daily-context').json()['entries']) == 1


def test_combined_message_searches_without_double_counting_consumption(client):
    client.put('/api/session/address', json={'address_id': 'demo-address'})
    text = 'Meu objetivo é ganhar massa muscular, só comi frutas hoje, quero almoço até R$ 40'
    response = client.post('/api/chat', json={'text': text, 'message_id': 'context-and-search'})
    assert response.status_code == 200, response.text
    session = response.json()
    assert session['last_chat_action'] == 'search'
    assert session['messages'][-2]['text'] == text
    assert session['request_intent']['diet_context']['meal_count'] == 1
    assert session['recommendations']
    assert all(r['candidate']['features']['portion_size'] in ('large', 'sharing') for r in session['recommendations'])
    next_result = client.post('/api/chat', json={'text': 'quero frango'}).json()
    assert next_result['request_intent']['diet_context']['goal'] == 'gain_muscle'
    assert next_result['request_intent']['diet_context']['meal_count'] == 1


def test_new_order_preserves_profile_and_review_learning(client):
    session = client.get('/api/session').json()
    client.put('/api/profile', json={**session['profile'], 'diet_plan': {'goal': 'balanced'}})
    candidate, version = checkout(client)
    assert confirm(client, version).status_code == 200
    response = client.post('/api/checkout/order/review', json={'rating': 4, 'comment': 'Bom sabor e entrega rápida'})
    assert response.status_code == 200
    review = next(r for r in client.get('/api/reviews/me').json() if r['item_id'] == candidate['item_id'] and r['merchant_id'] == candidate['merchant_id'])
    assert review['rating'] == 4
    new = client.post('/api/session/new-order', json={}).json()
    assert new['order'] is None and new['summary'] is None and new['selected'] is None
    assert new['profile']['diet_plan']['goal'] == 'balanced'
    assert any(r['id'] == review['id'] for r in client.get('/api/reviews/me').json())
    assert client.post('/api/chat', json={'text': 'quero almoço'}).status_code == 200


def test_post_order_review_validates_and_can_be_corrected(client):
    assert client.post('/api/checkout/order/review', json={'comment': 'Bom'}).status_code == 422
    _, version = checkout(client)
    confirm(client, version)
    assert client.post('/api/checkout/order/review', json={}).status_code == 422
    assert client.post('/api/checkout/order/review', json={'rating': 6}).status_code == 422
    review = client.post('/api/checkout/order/review', json={'comment': 'Gostei muito'}).json()['order']['review']
    assert review['rating'] is None and review['comment'] == 'Gostei muito'
    response = client.put('/api/checkout/order/review', json={'rating': 5, 'aspects': {'taste': 5}})
    assert response.status_code == 200
    assert response.json()['order']['review']['rating'] == 5


def test_new_search_after_confirmed_order_starts_next_order_without_confirming_it(client):
    _, version = checkout(client)
    confirm(client, version)
    response = client.post('/api/chat', json={'text': 'quero almoço'})
    assert response.status_code == 200
    result = response.json()
    assert result['order'] is None and result['summary'] is None and result['selected'] is None
    assert result['recommendations']


def test_post_order_review_uses_existing_llm_pipeline_and_blocks_reset_while_pending(client, monkeypatch):
    import app.services.review_interpretation as interpretation
    import asyncio
    configured = client.app.dependency_overrides[get_settings]().model_copy(update={
        'openai_api_key': SecretStr('test'), 'nutrition_provider': 'openai', 'review_llm_enabled': True,
    })
    client.app.dependency_overrides[get_settings] = lambda: configured
    async def complete(*args, **kwargs):
        await asyncio.sleep(.1)
        return json.dumps({'rating': 4, 'aspects': {'taste': 5}, 'summary': 'Gostou do sabor.'})
    monkeypatch.setattr(interpretation, 'chat_completion', complete)
    _, version = checkout(client)
    confirm(client, version)
    response = client.post('/api/checkout/order/review', json={'comment': 'Estava delicioso'})
    assert response.status_code == 200
    assert response.json()['order']['review']['interpretation_state'] == 'pending'
    assert client.post('/api/session/new-order', json={}).status_code == 409
    assert settled(client)['interpretation']['aspects']['taste'] == 5
    assert client.post('/api/session/new-order', json={}).status_code == 200
