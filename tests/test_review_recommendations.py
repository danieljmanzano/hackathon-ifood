from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.domain import rank
from app.schemas.macro import MealCandidate, MealRequest, UserProfile
from app.schemas.reviews import Review, ReviewAspects
from app.services.mock_ifood import catalog
from app.services.review_recommendations import ReviewContext, review_context, review_signal
from app.storage.database import Database


def candidate(merchant='a', item='item', **fields):
    return MealCandidate(merchant_id=merchant, item_id=item, merchant_name=merchant,
                         name='Prato da casa', description='Almoço', price_cents=2500,
                         simulated=True, **fields)


def review(merchant='a', rating=5, item='item', user='user'):
    return Review(id=f'{user}-{merchant}-{item}', merchant_id=merchant, item_id=item,
                  user_id=user, rating=rating, comment='Minha experiência',
                  aspects=ReviewAspects(taste=rating, delivery=rating,
                                       value_for_money=rating, portion_size=rating),
                  created_at=datetime.now(timezone.utc))


def test_history_changes_order_and_transfers_to_other_merchants():
    a, b = candidate('a'), candidate('b')
    cuisines = {'a': ['vegana'], 'b': ['hambúrguer'], 'past': ['vegana']}
    context = ReviewContext(history=[review('past', 5)], cuisines=cuisines, simulated=True)
    results = rank([b, a], MealRequest(text='almoço'), UserProfile(id='user'), None, context)
    assert results[0].candidate.merchant_id == 'a'
    assert results[0].review_signal.source == 'personalized'
    context.history = [review('past', 1)]
    assert rank([a, b], MealRequest(text='almoço'), UserProfile(id='user'), None, context)[0].candidate.merchant_id == 'b'
    # Feedback negativo diretamente sobre um restaurante tem efeito mesmo sem cozinhas.
    context = ReviewContext(history=[review('a', 1)], simulated=True)
    assert rank([a, b], MealRequest(text='almoço'), UserProfile(id='user'), None, context)[0].candidate.merchant_id == 'b'


def test_community_fallback_and_small_sample_smoothing():
    context = ReviewContext(community=[review('a', 5)], simulated=True)
    signal, _ = review_signal(candidate(), context)
    assert signal.source == 'community'
    assert signal.community_rating == 5
    assert 0 < signal.score < 1  # Uma única nota máxima não vira confiança máxima.
    signal, _ = review_signal(candidate('unknown'), context)
    assert signal.source == 'unavailable'
    assert signal.score == 0


def test_filters_and_availability_override_positive_reviews():
    context = ReviewContext(history=[review('a', 5)], simulated=True)
    a = candidate()
    req = MealRequest(text='almoço')
    assert rank([a], req, UserProfile(id='user'), 2400, context) == []
    assert rank([a], req, UserProfile(id='user', dislikes=['almoço']), None, context) == []
    assert rank([a], MealRequest(text='almoço', restrictions=['almoço']), UserProfile(id='user'), None, context) == []
    a.available = False
    assert rank([a], req, UserProfile(id='user'), None, context) == []


def test_context_updates_seed_excludes_own_reviews_and_isolates_live(tmp_path):
    db = Database(tmp_path / 'test.sqlite3')
    initial = review_context(db, 'one', True)
    assert len(initial.history) == 6
    assert not any(r.user_id == 'demo-user' for r in initial.community)
    old = initial.history[0]
    changed = old.model_copy(update={'rating': 1, 'id': 'updated'})
    db.save_review(changed)
    db = Database(db.path)  # Persistência após reabrir o banco.
    updated = review_context(db, 'one', True)
    assert len(updated.history) == 6
    assert next(r for r in updated.history if r.item_id == old.item_id).rating == 1
    assert all(r.user_id != 'one' for r in updated.community)
    another = review_context(db, 'two', True)
    assert next(r for r in another.history if r.item_id == old.item_id).rating == old.rating
    assert review_context(db, 'one', False).history == []
    assert review_context(db, 'one', False).community == []
    signal, _ = review_signal(candidate().model_copy(update={'simulated': False}), updated)
    assert signal.source == 'unavailable'


def test_catalog_covers_all_fixture_items_and_diversifies_recommendations(tmp_path):
    from app.services.mock_reviews import review_dataset
    data = review_dataset()
    assert {(c.merchant_id, c.item_id) for c in catalog()} == {
        (m.merchant_id, item) for m in data.establishments for item in m.item_ids
    }
    context = review_context(Database(tmp_path / 'test.sqlite3'), 'user', True)
    results = rank(catalog(), MealRequest(text='almoço'), UserProfile(id='user'), None, context)
    assert len({r.candidate.merchant_id for r in results}) == 3


@pytest.fixture
def client(tmp_path, monkeypatch):
    import app.main as main
    settings = Settings(_env_file=None, ifood_mode='mock', database_path=tmp_path / 'test.sqlite3', openai_api_key='', intent_llm_enabled=False)
    monkeypatch.setattr(main, 'get_settings', lambda: settings)
    application = main.create_app()
    application.dependency_overrides[get_settings] = lambda: settings
    with TestClient(application) as client:
        yield client


def test_review_api_reranks_persists_and_validates_identity(client):
    assert client.get('/api/reviews/me').status_code == 401
    session = client.get('/api/session').json()
    client.put('/api/session/address', json={'address_id': 'demo-address'})
    before = client.post('/api/search', json={'text': 'almoço'}).json()
    first = before['recommendations'][0]['candidate']
    payload = dict(merchant_id=first['merchant_id'], item_id=first['item_id'], rating=1,
                   comment='Não gostei deste prato.',
                   aspects=dict(taste=1, delivery=3, value_for_money=1, portion_size=3))
    response = client.put('/api/reviews', json=payload)
    assert response.status_code == 200
    assert response.json()['user_id'] == session['profile']['id']
    after = client.post('/api/search', json={'text': 'almoço'}).json()
    assert after['recommendations'][0]['candidate']['merchant_id'] != first['merchant_id']
    history = client.get('/api/reviews/me').json()
    assert any(r['comment'] == payload['comment'] for r in history)
    # Atualização do mesmo item não duplica o histórico.
    payload['rating'] = 5
    assert client.put('/api/reviews', json=payload).status_code == 200
    assert len(client.get('/api/reviews/me').json()) == len(history)
    assert client.put('/api/reviews', json={**payload, 'user_id': 'another'}).status_code == 422
    assert client.put('/api/reviews', json={**payload, 'rating': 6}).status_code == 422
    assert client.put('/api/reviews', json={**payload, 'rating': True}).status_code == 422
    assert client.put('/api/reviews', json={**payload, 'comment': '  '}).status_code == 422
    assert client.put('/api/reviews', json={**payload, 'item_id': 'unknown'}).status_code == 422
    # Histórico e notas são da sessão; trocar o cookie cria outra identidade.
    client.cookies.clear()
    client.get('/api/session')
    assert not any(r['comment'] == payload['comment'] for r in client.get('/api/reviews/me').json())


def test_explanations_cite_cuisine_and_actual_rating_without_inventing_tastes():
    context = ReviewContext(
        history=[review('past', 5)],
        cuisines={'a': ['vegana'], 'past': ['vegana']}, simulated=True,
    )
    _, reasons = review_signal(candidate('a'), context)
    assert any('cozinha vegana' in reason and '5/5' in reason for reason in reasons)
    context.history = [review('a', 1)]
    _, reasons = review_signal(candidate('a'), context)
    assert any('1/5' in reason and 'experiência anterior' in reason for reason in reasons)
    assert not any('já gostou' in reason for reason in reasons)
    result = rank(
        [candidate('a')], MealRequest(text='almoço'),
        UserProfile(id='user', preferences=['almoço']), None, context,
    )[0]
    assert result.reasons[0] == 'Este prato inclui algo que você gosta: almoço.'


def test_preprocessing_handles_explicit_negation_and_aspects():
    from app.services.review_processing import preprocess_review
    item = review().model_copy(update={'comment': 'Nada oleoso, ingredientes frescos e sem atraso.'})
    processed = preprocess_review(item)
    assert processed.traits['lightness'] > 0
    assert processed.traits['delivery'] > 0
    assert processed.traits['freshness'] > 0
    assert processed.aspect_scores['taste'] == 1
    negative = preprocess_review(item.model_copy(update={'comment': 'Muito oleoso. Não estava fresco. Houve atraso.'}))
    assert negative.traits['lightness'] < 0
    assert negative.traits['freshness'] < 0
    assert negative.traits['delivery'] < 0
    assert negative.fingerprint != processed.fingerprint


def test_preprocessing_and_tastes_survive_restart_and_invalidate_on_edit(tmp_path, monkeypatch):
    import app.services.review_processing as processing
    db = Database(tmp_path / 'pipeline.sqlite3')
    profile = UserProfile(id='user', preferences=['frango'], restrictions=['amendoim'])
    original = review_context(db, 'user', True, profile)
    stored = Database(db.path).get_tastes('user', True)
    assert stored.preferences == ['frango']
    assert stored.restrictions == ['amendoim']
    assert stored.source_hash == original.tastes.source_hash
    count = len(db.processed_reviews(True))
    # Uma consulta após reiniciar deve reutilizar o pré-processamento persistido.
    with monkeypatch.context() as patch:
        def unexpected(_):
            raise AssertionError('Review inalterada foi processada outra vez')
        patch.setattr(processing, 'preprocess_review', unexpected)
        again = review_context(Database(db.path), 'user', True, profile)
    assert again.tastes.updated_at == original.tastes.updated_at
    assert len(db.processed_reviews(True)) == count
    edited = original.history[0].model_copy(update={'comment': 'Muito oleoso e porção pequena.', 'rating': 1})
    db.save_review(edited)
    changed = review_context(db, 'user', True, profile)
    assert changed.tastes.source_hash != original.tastes.source_hash
    assert changed.processed[edited.id].traits['lightness'] < 0
    assert len(db.processed_reviews(True)) == count + 1
    assert Database(db.path).get_tastes('user', False) is None
    assert Database(db.path).get_tastes('another', True) is None


def test_text_features_affect_unseen_restaurant_recommendations(tmp_path):
    db = Database(tmp_path / 'text.sqlite3')
    for value in [
        review('past', 3, user='me').model_copy(update={'comment': 'Ingredientes frescos.', 'simulated': False}),
        review('good', 3, user='other').model_copy(update={'comment': 'Tudo fresco.', 'simulated': False}),
        review('bad', 3, user='other').model_copy(update={'comment': 'Tudo ressecado.', 'simulated': False}),
    ]:
        db.save_review(value)
    context = review_context(db, 'me', False)
    good = candidate('good').model_copy(update={'simulated': False})
    bad = candidate('bad').model_copy(update={'simulated': False})
    good_signal, reasons = review_signal(good, context)
    bad_signal, _ = review_signal(bad, context)
    assert good_signal.personal_rating is None
    assert good_signal.text_affinity > 0 > bad_signal.text_affinity
    assert good_signal.score > bad_signal.score
    assert any('frescor' in reason and 'outras pessoas' in reason for reason in reasons)


def test_new_mock_restaurants_have_community_reviews_but_no_user_reviews(tmp_path):
    context = review_context(Database(tmp_path / 'new.sqlite3'), 'user', True)
    visited = {r.merchant_id for r in context.history}
    unseen = {c.merchant_id for c in catalog()} - visited
    assert len(unseen) == 18
    assert all(any(r.merchant_id == mid for r in context.community) for mid in unseen)
    horta = next(c for c in catalog() if c.merchant_id == 'demo-horta')
    signal, reasons = review_signal(horta, context)
    assert signal.personal_rating is None
    assert signal.cuisine_affinity > 0
    assert signal.source == 'personalized'
    assert not any('Você já gostou deste prato' in reason for reason in reasons)


def test_tastes_endpoint_updates_on_profile_and_review_save(client):
    assert client.get('/api/profile/tastes').status_code == 401
    session = client.get('/api/session').json()
    initial = client.get('/api/profile/tastes').json()
    assert initial['history_count'] == 6
    profile = {**session['profile'], 'preferences': ['frango'], 'dislikes': ['cebola']}
    assert client.put('/api/profile', json=profile).status_code == 200
    changed = client.get('/api/profile/tastes').json()
    assert changed['preferences'] == ['frango']
    assert changed['dislikes'] == ['cebola']
    assert changed['source_hash'] != initial['source_hash']
    client.put('/api/session/address', json={'address_id': 'demo-address'})
    client.get('/api/merchants/demo-horta/menu')
    payload = dict(merchant_id='demo-horta', item_id='demo-horta-bowl', rating=5,
                   comment='Ingredientes frescos e nada oleoso.',
                   aspects=dict(taste=5, delivery=4, value_for_money=4, portion_size=4))
    assert client.put('/api/reviews', json=payload).status_code == 200
    current = client.get('/api/profile/tastes').json()
    assert current['history_count'] == 7
    assert current['source_hash'] != changed['source_hash']
    assert current['trait_interests']['freshness'] > 0
    client.cookies.clear()
    client.get('/api/session')
    assert client.get('/api/profile/tastes').json()['preferences'] == []


def test_repeated_searches_rotate_without_losing_budget_or_preferences(client):
    client.get('/api/session')
    client.put('/api/session/address', json={'address_id': 'demo-address'})
    batches = []
    for _ in range(4):
        response = client.post('/api/search', json={'text': 'almoço até R$ 35'})
        assert response.status_code == 200
        data = response.json()
        items = [r['candidate'] for r in data['recommendations']]
        assert len(items) == 3
        assert len({item['merchant_id'] for item in items}) == 3
        assert all(item['price_cents'] <= 3500 for item in items)
        batches.append({(item['merchant_id'], item['item_id']) for item in items})
    assert all(batches[i] != batches[i+1] for i in range(3))
    assert len(set.union(*batches)) >= 9
    assert len(data['recent_recommendations']) == 12
    restored = client.get('/api/session').json()
    assert restored['recent_recommendations'] == data['recent_recommendations']


def test_specific_searches_prioritize_requested_food_even_after_rotation(client):
    client.get('/api/session')
    client.put('/api/session/address', json={'address_id': 'demo-address'})
    results = []
    for _ in range(2):
        response = client.post('/api/search', json={'text': 'frango até R$ 30'})
        items = [r['candidate'] for r in response.json()['recommendations']]
        assert len(items) == 3
        assert all('frango' in (item['name'] + ' ' + item['description']).lower() for item in items)
        assert all(item['price_cents'] <= 3000 for item in items)
        results.append({item['item_id'] for item in items})
    assert results[0] != results[1]
    # Se a comida pedida existe mas não cabe no orçamento, não trocar por outro tipo de prato.
    assert client.post('/api/search', json={'text': 'pizza até R$ 10'}).json()['recommendations'] == []


def test_rotation_never_reintroduces_filtered_items():
    allowed = candidate('allowed')
    rejected = candidate('rejected').model_copy(update={'description': 'Almoço com amendoim'})
    context = ReviewContext(simulated=True)
    results = rank([allowed, rejected], MealRequest(text='almoço'),
                   UserProfile(id='user', restrictions=['amendoim']), 3000, context,
                   [('allowed', 'item')] * 6)
    assert [r.candidate.merchant_id for r in results] == ['allowed']


@pytest.mark.parametrize('text, expected', [
    ('estou com muita fome', ['large_portion']),
    ('Tô morrendo de fome', ['large_portion']),
    ('estou com pouca fome', ['small_portion']),
    ('não estou com muita fome', ['small_portion']),
    ('muita fome, mas quero algo leve', ['large_portion', 'light']),
    ('quero economizar, estou com pressa', ['cheap', 'fast']),
    ('quero comer depois do treino', ['protein']),
    ('cheat meal', ['indulgent']),
    ('quero comida caseira', ['comfort']),
    ('quero algo sem carne', ['vegetarian']),
    ('sem pressa, não quero comida leve', []),
])
def test_parse_natural_meal_intents(text, expected):
    from app.services.meal_intent import parse_intent
    intent = parse_intent(MealRequest(text=text))
    assert intent.goals == expected
    assert intent.food_query == ''


def test_intent_keeps_food_budget_and_delivery_separate():
    from app.services.meal_intent import parse_intent
    intent = parse_intent(MealRequest(text='muita fome, quero frango até R$ 35,50 e entrega em até 30 minutos'))
    assert intent.food_query == 'frango'
    assert intent.budget_cents == 3550
    assert intent.max_delivery_minutes == 30
    assert set(intent.goals) == {'large_portion', 'fast'}
    intent = parse_intent(MealRequest(text='quero pizza para duas pessoas em até 20 minutos'))
    assert intent.budget_cents is None
    assert intent.party_size == 2
    assert intent.food_query == 'pizza'
    assert parse_intent(MealRequest(text='pizza para compartilhar')).party_size == 2
    assert parse_intent(MealRequest(text='frango até 30 reais', budget_cents=2500)).budget_cents == 2500


@pytest.mark.parametrize('text, predicate', [
    ('estou com muita fome', lambda item: item['features']['portion_size'] in ('large', 'sharing')),
    ('estou com pouca fome', lambda item: item['features']['portion_size'] == 'small'),
    ('muita fome, mas quero algo leve', lambda item: item['features']['portion_size'] in ('large', 'sharing') and 'light' in item['features']['tags']),
    ('quero algo depois do treino', lambda item: 'protein' in item['features']['tags']),
    ('quero comida caseira', lambda item: 'comfort' in item['features']['tags']),
    ('cheat meal', lambda item: 'indulgent' in item['features']['tags']),
    ('quero algo sem carne', lambda item: 'vegetarian' in item['features']['tags']),
    ('estou com pressa, em até 25 minutos', lambda item: item['features']['eta_max_minutes'] <= 25),
    ('pizza para duas pessoas', lambda item: item['features']['serves'] >= 2),
])
def test_intents_actually_change_recommendations(client, text, predicate):
    client.get('/api/session')
    client.put('/api/session/address', json={'address_id': 'demo-address'})
    for _ in range(2):
        response = client.post('/api/search', json={'text': text})
        assert response.status_code == 200
        data = response.json()
        assert data['request_intent']['labels']
        assert 'Busquei opções considerando:' in data['messages'][-1]['text']
        assert len(data['recommendations']) == 3
        assert all(predicate(r['candidate']) for r in data['recommendations'])
        assert all(r['reasons'][0] for r in data['recommendations'])


def test_hunger_never_overrides_food_budget_or_restrictions(client):
    session = client.get('/api/session').json()
    profile = {**session['profile'], 'restrictions': ['amendoim']}
    client.put('/api/profile', json=profile)
    client.put('/api/session/address', json={'address_id': 'demo-address'})
    data = client.post('/api/search', json={'text': 'muita fome, quero frango até R$ 30'}).json()
    assert data['recommendations']
    for rec in data['recommendations']:
        item = rec['candidate']
        assert 'frango' in (item['name'] + ' ' + item['description']).lower()
        assert item['price_cents'] <= 3000
        assert 'amendoim' not in item['description'].lower()
        assert item['features']['portion_size'] == 'large'


def test_missing_live_metadata_does_not_invent_portions_or_delivery():
    from app.services.meal_intent import assess_intent, parse_intent
    item = candidate().model_copy(update={'simulated': False})
    fit = assess_intent(item, parse_intent(MealRequest(text='muita fome, estou com pressa')))
    assert not fit.reasons
    assert any('tamanho da porção' in limitation for limitation in fit.limitations)
    assert any('previsão de entrega' in limitation for limitation in fit.limitations)


def test_economy_intent_rotates_among_inexpensive_meals(client):
    client.get('/api/session')
    client.put('/api/session/address', json={'address_id': 'demo-address'})
    batches = []
    for _ in range(2):
        data = client.post('/api/search', json={'text': 'quero economizar, sem gastar muito'}).json()
        assert data['request_intent']['goals'] == ['cheap']
        assert len(data['recommendations']) == 3
        assert all(r['candidate']['price_cents'] <= 2500 for r in data['recommendations'])
        batches.append({r['candidate']['item_id'] for r in data['recommendations']})
    assert batches[0] != batches[1]


def test_explicit_vegetarian_request_does_not_return_mock_meat_dishes(client):
    client.get('/api/session')
    client.put('/api/session/address', json={'address_id': 'demo-address'})
    response = client.post('/api/search', json={'text': 'quero frango sem carne'})
    assert response.status_code == 200
    assert response.json()['recommendations'] == []
