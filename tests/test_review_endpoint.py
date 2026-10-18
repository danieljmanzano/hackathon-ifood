"""Avaliação facilitada: texto livre e nota opcional na confirmação; o LLM estrutura em segundo plano."""
import json
import time

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
import app.services.review_interpretation as interpretation


@pytest.fixture
def make_client(tmp_path, monkeypatch):
    clients = []

    def make(**overrides):
        import app.main as main
        settings = Settings(_env_file=None, **{
            'ifood_mode': 'mock', 'database_path': tmp_path / 'test.sqlite3', 'openai_api_key': '',
            'openrouter_api_key': '', 'intent_llm_enabled': False, **overrides})
        monkeypatch.setattr(main, 'get_settings', lambda: settings)
        application = main.create_app()
        application.dependency_overrides[get_settings] = lambda: settings
        client = TestClient(application)
        clients.append(client.__enter__())
        return client

    yield make
    for client in clients:
        client.__exit__(None, None, None)


@pytest.fixture
def client(make_client):
    return make_client()


def llm_replies(monkeypatch, reply):
    calls = []

    async def fake(messages, **kwargs):
        calls.append(json.loads(messages[-1]['content']))
        if isinstance(reply, Exception):
            raise reply
        return reply

    monkeypatch.setattr(interpretation, 'chat_completion', fake)
    return calls


def checkout(client):
    """Percorre sessão → endereço → busca → seleção → resumo e devolve o prato e a versão do resumo."""
    client.get('/api/session')
    client.put('/api/session/address', json={'address_id': 'demo-address'})
    recommendations = client.post('/api/search', json={'text': 'almoço'}).json()['recommendations']
    # Um prato sem grupos obrigatórios pode ser selecionado sem opções.
    candidate = next(r['candidate'] for r in recommendations
                     if not any(g['min_selections'] > 0 for g in r['candidate'].get('option_groups', [])))
    selected = client.put('/api/selection', json={'merchant_id': candidate['merchant_id'],
                                                  'item_id': candidate['item_id']})
    assert selected.status_code == 200, selected.text
    summary = client.post('/api/checkout/review', json={'delivery_id': 'demo-standard',
                                                        'payment_id': 'demo-payment'})
    assert summary.status_code == 200, summary.text
    return candidate, summary.json()['summary']['version']


def confirm(client, version, review=None):
    body = {'version': version, 'confirmed': True}
    if review is not None:
        body['review'] = review
    return client.post('/api/checkout/confirm', json=body)


def settled(client):
    for _ in range(100):
        review = client.get('/api/checkout/order').json()['order']['review']
        if review['interpretation_state'] != 'pending':
            return review
        time.sleep(0.02)
    raise AssertionError('Interpretação não terminou')


def saved_review(client, candidate):
    return next((r for r in client.get('/api/reviews/me').json()
                 if (r['merchant_id'], r['item_id']) == (candidate['merchant_id'], candidate['item_id'])), None)


def test_without_llm_user_values_are_kept_literally(client):
    candidate, version = checkout(client)
    response = confirm(client, version, {'rating': 2, 'comment': '  Chegou frio.  ' + 'x' * 300})
    assert response.status_code == 200, response.text
    review = response.json()['order']['review']
    assert review['rating'] == 2 and review['interpretation_state'] == 'none'
    assert review['comment'].startswith('Chegou frio.') and len(review['comment']) == 200
    assert client.get('/api/session').json()['order']['review'] == review
    saved = saved_review(client, candidate)
    assert saved['rating'] == 2 and saved['comment'] == review['comment']
    # Sem leitura do comentário, nenhum aspecto é inventado: todos ficam neutros.
    assert set(saved['aspects'].values()) == {3}
    # Reconfirmar não altera a avaliação já registrada.
    assert confirm(client, version, {'rating': 5}).json()['order']['review'] == review


def test_confirm_without_review_is_backward_compatible(client):
    _, version = checkout(client)
    history = client.get('/api/reviews/me').json()
    response = confirm(client, version)
    assert response.status_code == 200
    assert response.json()['order']['id'].startswith('demo-order-')
    assert response.json()['order']['review'] is None
    assert client.get('/api/reviews/me').json() == history


def test_blank_review_is_ignored_and_text_without_rating_stays_off_history(client):
    _, version = checkout(client)
    assert confirm(client, version, {'comment': '   '}).json()['order']['review'] is None

    client.cookies.clear()
    candidate, version = checkout(client)
    review = confirm(client, version, {'comment': 'Bem embalado'}).json()['order']['review']
    assert (review['rating'], review['comment'], review['interpretation']) == (None, 'Bem embalado', None)
    # Sem LLM e sem nota escolhida, a avaliação vai sem nota e não gera sinal de gosto.
    assert saved_review(client, candidate) is None or saved_review(client, candidate)['comment'] != 'Bem embalado'


@pytest.mark.parametrize('review', [{'rating': 0}, {'rating': 6}, {'rating': True}, {'rating': 3, 'extra': 1},
                                    {'comment': 'x', 'interpretation_state': 'done'}])
def test_invalid_review_is_rejected(client, review):
    _, version = checkout(client)
    assert confirm(client, version, review).status_code == 422
    assert client.get('/api/session').json()['order'] is None


def test_llm_structures_free_text_in_background(make_client, monkeypatch):
    calls = llm_replies(monkeypatch, json.dumps({
        'rating': 4, 'aspects': {'taste': 5, 'delivery': 2},
        'summary': 'Gostou do sabor, mas a entrega atrasou.', 'tags': ['entrega atrasada'],
    }))
    client = make_client(openrouter_api_key='test')
    candidate, version = checkout(client)
    first = confirm(client, version, {'comment': 'demorou muito mas tava uma delícia'}).json()['order']['review']
    assert first['interpretation_state'] == 'pending'
    review = settled(client)
    assert review['interpretation_state'] == 'done'
    assert review['interpretation']['aspects'] == {'taste': 5, 'delivery': 2, 'value_for_money': None,
                                                   'portion_size': None}
    assert review['comment'] == 'demorou muito mas tava uma delícia'
    assert calls == [{'prato': candidate['name'], 'restaurante': candidate['merchant_name'],
                      'comentario': 'demorou muito mas tava uma delícia'}]
    saved = saved_review(client, candidate)
    assert saved['rating'] == 4
    assert saved['aspects'] == {'taste': 5, 'delivery': 2, 'value_for_money': 3, 'portion_size': 3}


def test_user_stars_prevail_over_interpretation(make_client, monkeypatch):
    llm_replies(monkeypatch, '```json\n{"rating": 1, "aspects": {"portion_size": 1}}\n```')
    client = make_client(openrouter_api_key='test')
    candidate, version = checkout(client)
    confirm(client, version, {'rating': 5, 'comment': 'pouca comida'})
    review = settled(client)
    assert review['interpretation']['rating'] == 1
    saved = saved_review(client, candidate)
    assert saved['rating'] == 5 and saved['aspects']['portion_size'] == 1


@pytest.mark.parametrize('reply', ['não é json', '{"rating": 9}', '{"rating": 3, "nota": 1}', TimeoutError()])
def test_llm_failure_falls_back_to_what_the_user_filled(make_client, monkeypatch, reply):
    llm_replies(monkeypatch, reply)
    client = make_client(openrouter_api_key='test')
    candidate, version = checkout(client)
    confirm(client, version, {'rating': 2, 'comment': 'veio frio'})
    review = settled(client)
    assert (review['interpretation_state'], review['interpretation']) == ('failed', None)
    assert review['rating'] == 2 and review['comment'] == 'veio frio'
    assert saved_review(client, candidate)['rating'] == 2


def test_user_can_correct_the_interpretation(make_client, monkeypatch):
    llm_replies(monkeypatch, '{"rating": 2, "aspects": {"delivery": 1}}')
    client = make_client(openrouter_api_key='test')
    assert client.get('/api/session').status_code == 200
    assert client.put('/api/checkout/order/review', json={'rating': 4}).status_code == 422
    candidate, version = checkout(client)
    confirm(client, version, {'comment': 'atrasou'})
    settled(client)
    response = client.put('/api/checkout/order/review', json={'rating': 4, 'aspects': {'taste': 5}})
    assert response.status_code == 200, response.text
    review = response.json()['order']['review']
    assert review['rating'] == 4 and review['interpretation']['rating'] == 2
    saved = saved_review(client, candidate)
    # A correção prevalece; o que não foi corrigido continua vindo da interpretação.
    assert saved['rating'] == 4
    assert saved['aspects'] == {'taste': 5, 'delivery': 1, 'value_for_money': 3, 'portion_size': 3}
    assert client.put('/api/checkout/order/review', json={'rating': 6}).status_code == 422
