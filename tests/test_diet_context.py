import asyncio
from datetime import date, datetime, timedelta, timezone
import json

from fastapi.testclient import TestClient
import pytest

from app.core.config import Settings, get_settings
from app.domain import rank
from app.schemas.macro import (ConsumptionRecord, DailyNutrients, DietPlan, FoodDiaryEntry,
                               MealRequest, NutritionResult, UserProfile)
from app.services import llm_meal_intent
from app.services.diet_context import apply_diet_context, build_diet_context, split_daily_message
from app.services.meal_intent import parse_intent
from app.services.mock_ifood import catalog

DAY = date(2026, 10, 18)
AT = datetime(2026, 10, 18, 15, tzinfo=timezone.utc)


def nutrition(calories, protein):
    return NutritionResult(state='ready', calories=calories, minimum=calories * .9,
                           maximum=calories * 1.1, protein_g=protein, carbs_g=40, fat_g=15,
                           method='estimated', portion_basis='um prato')


def profile(**plan):
    return UserProfile(id='diet-user', diet_plan=DietPlan(goal='gain_muscle', **plan))


def context(user=None, entries=None, consumption=None, message='quero almoço'):
    return build_diet_context(user or profile(), entries or [], consumption or [],
                              'America/Sao_Paulo', on_date=DAY, message=message)


def test_muscle_goal_and_fruit_records_favor_substantial_protein_meal():
    user = profile()
    daily, clean = context(user, [FoodDiaryEntry(description='Só comi banana e maçã hoje', consumed_at=AT)])
    request = MealRequest(text=clean)
    intent = apply_diet_context(parse_intent(request), daily, clean)
    assert intent.goals == ['protein', 'large_portion']
    assert set(intent.inferred_goals) == {'protein', 'large_portion'}
    assert intent.nutrition_preferences.goals == ['high_protein']
    assert intent.nutrition_preferences.min_protein_g is None
    assert daily.known_intake.protein_g is None
    ranked = rank(catalog(), request, user, None, intent=intent)
    assert all(r.candidate.features.portion_size in ('large', 'sharing') for r in ranked)
    assert all('protein' in r.candidate.features.tags for r in ranked)
    assert all(any('apenas frutas' in r for r in rec.reasons) for rec in ranked)


@pytest.mark.parametrize('message, expected', [
    ('só comi frutas hoje, estou com pouca fome', 'small_portion'),
    ('só comi frutas hoje, quero uma refeição pré-treino', 'small_portion'),
    ('só comi frutas hoje, quero algo leve', 'light'),
])
def test_context_does_not_override_appetite_or_preworkout(message, expected):
    daily, clean = context(message=message)
    intent = apply_diet_context(parse_intent(MealRequest(text=clean)), daily, clean)
    assert expected in intent.goals
    assert 'large_portion' not in intent.goals


def test_inline_food_and_goal_are_context_not_search_terms_or_permanent_profile():
    user = UserProfile(id='u')
    daily, clean = context(user, message='meu objetivo é ganhar massa muscular, só comi frutas hoje, quero frango até R$ 30')
    intent = apply_diet_context(parse_intent(MealRequest(text=clean)), daily, clean)
    assert daily.goal == 'gain_muscle'
    assert intent.food_query == 'frango'
    assert intent.budget_cents == 3000
    assert 'large_portion' in intent.goals
    assert user.diet_plan.goal is None
    assert 'frutas' not in intent.provider_query
    clean, foods, _ = split_daily_message('não comi frutas hoje, quero frango')
    assert not foods
    assert parse_intent(MealRequest(text=clean)).food_query == 'frango'


def test_goals_without_records_do_not_assume_fasting_or_invent_targets():
    daily, clean = context()
    intent = apply_diet_context(parse_intent(MealRequest(text=clean)), daily, clean)
    assert 'protein' in intent.goals
    assert 'large_portion' not in intent.goals
    assert all(v is None for v in daily.known_intake.model_dump().values())
    assert all(v is None for v in daily.remaining.model_dump().values())
    assert any('não presumimos' in limitation for limitation in daily.limitations)


def test_known_totals_apply_fraction_and_quantity_without_counting_pending_macros():
    user = profile(daily_protein_g=100)
    user.daily_calorie_goal = 2000
    diary = [FoodDiaryEntry(description='Café da manhã', consumed_at=AT,
                           nutrition=DailyNutrients(calories=300, protein_g=10))]
    consumed = [ConsumptionRecord(order_id='order', item_id='item', name='Frango', consumed_at=AT,
                                  fraction=.5, quantity=2, nutrition=nutrition(600, 40))]
    daily, _ = context(user, diary, consumed)
    assert daily.known_intake.calories == 900
    assert daily.known_intake.protein_g == 50
    assert daily.remaining.calories == 1100
    assert daily.remaining.protein_g == 50
    assert daily.remaining.carbs_g is None
    assert 'protein_target_remaining' in daily.signals
    diary.append(FoodDiaryEntry(description='Frutas', consumed_at=AT))
    partial, _ = context(user, diary, consumed)
    assert partial.known_intake.protein_g == 50
    assert partial.remaining.protein_g is None
    assert partial.known_counts['protein_g'] == 2


def test_target_already_reached_does_not_force_more_protein_or_skip_meals():
    user = profile(daily_protein_g=40)
    user.daily_calorie_goal = 600
    diary = [FoodDiaryEntry(description='Arroz, feijão e frango', consumed_at=AT,
                           nutrition=DailyNutrients(calories=650, protein_g=45))]
    daily, clean = context(user, diary, message='estou com muita fome')
    intent = apply_diet_context(parse_intent(MealRequest(text=clean)), daily, clean)
    assert 'protein_target_reached' in daily.signals
    assert 'protein' not in intent.goals
    assert 'large_portion' in intent.goals
    assert 'small_portion' not in intent.goals
    assert intent.nutrition_preferences.max_calories is None
    assert daily.remaining.calories == 0


def test_previous_day_and_utc_boundary_use_local_date():
    # 01:00 UTC de 18/10 ainda é 17/10 no Brasil.
    previous = FoodDiaryEntry(description='Frango', consumed_at=datetime(2026, 10, 18, 1, tzinfo=timezone.utc))
    today = FoodDiaryEntry(description='Frutas', consumed_at=AT)
    daily, _ = context(entries=[previous, today])
    assert daily.meal_count == 1
    assert daily.foods == ['Frutas']
    assert daily.signals == ['fruit_only_records']
    old_message, clean = context(message='ontem só comi frutas, quero frango hoje')
    assert old_message.meal_count == 0
    assert 'frutas' not in parse_intent(MealRequest(text=clean)).food_query


def test_mixed_meals_and_negated_fruit_do_not_trigger_fruit_only_rule():
    for description in ('Frutas com whey e iogurte', 'Frutas e pizza', 'não comi frutas'):
        daily, _ = context(entries=[FoodDiaryEntry(description=description, consumed_at=AT)])
        assert 'fruit_only_records' not in daily.signals


def test_llm_context_cache_changes_with_diary_and_excludes_identity(monkeypatch):
    calls = []
    async def complete(messages, **kwargs):
        assert kwargs['log_content'] is False
        calls.append(json.loads(messages[-1]['content']))
        return json.dumps({'goals': [], 'food_query': 'frango', 'context_summary': 'Vou considerar seu contexto.'})
    monkeypatch.setattr(llm_meal_intent, 'chat_completion', complete)
    llm_meal_intent._cache.clear()
    settings = Settings(_env_file=None, intent_llm_enabled=True, openrouter_api_key='test-key')
    first, _ = context(entries=[FoodDiaryEntry(description='Frutas', consumed_at=AT)])
    second, _ = context(entries=[FoodDiaryEntry(description='Arroz e frango', consumed_at=AT)])
    async def scenario():
        for daily in (first, first, second):
            await llm_meal_intent.interpret_intent(MealRequest(text='frango'), settings, diet_context=daily)
    asyncio.run(scenario())
    assert len(calls) == 2
    assert calls[0]['diet_context']['foods'] == ['Frutas']
    assert 'diet-user' not in json.dumps(calls)
    assert 'test-key' not in json.dumps(calls)
    llm_meal_intent._cache.clear()


def test_llm_cannot_search_for_already_consumed_food_instead_of_current_request(monkeypatch):
    async def complete(*args, **kwargs):
        return json.dumps({'goals': [], 'food_query': 'frutas', 'context_summary': 'Considerando seu dia.'})
    monkeypatch.setattr(llm_meal_intent, 'chat_completion', complete)
    llm_meal_intent._cache.clear()
    daily, _ = context(entries=[FoodDiaryEntry(description='Frutas', consumed_at=AT)])
    settings = Settings(_env_file=None, intent_llm_enabled=True, openrouter_api_key='test')
    async def scenario():
        return [await llm_meal_intent.interpret_intent(MealRequest(text='quero frango'), settings,
                                                     diet_context=daily) for _ in range(2)]
    assert all(intent.food_query == 'frango' for intent in asyncio.run(scenario()))
    llm_meal_intent._cache.clear()


@pytest.fixture
def api(tmp_path, monkeypatch):
    import app.main as main
    settings = Settings(_env_file=None, ifood_mode='mock', intent_llm_enabled=False,
                        openrouter_api_key='', openai_api_key='', database_path=tmp_path / 'diet.sqlite3', calorias_base_path=tmp_path / 'nutrition.json')
    monkeypatch.setattr(main, 'get_settings', lambda: settings)
    application = main.create_app()
    application.dependency_overrides[get_settings] = lambda: settings
    with TestClient(application) as client:
        client.get('/api/session')
        yield client, settings


def test_api_persists_goals_diary_and_consumption_and_search_uses_them(api):
    import app.main as main
    client, settings = api
    session = client.get('/api/session').json()
    assert session['profile']['diet_plan']['goal'] is None
    updated = client.put('/api/profile', json={**session['profile'], 'diet_plan': {
        'goal': 'gain_muscle', 'details': 'Refeições variadas', 'daily_protein_g': 100,
    }})
    assert updated.status_code == 200
    created = client.post('/api/food-diary', json={'description': 'Só comi frutas hoje'})
    assert created.status_code == 200
    client.put('/api/session/address', json={'address_id': 'demo-address'})
    result = client.post('/api/search', json={'text': 'quero almoço'}).json()
    assert result['request_intent']['diet_context']['meal_count'] == 1
    assert 'large_portion' in result['request_intent']['goals']
    assert all(r['candidate']['features']['portion_size'] in ('large', 'sharing') for r in result['recommendations'])
    record = {'order_id': 'order', 'item_id': 'item', 'name': 'Frango', 'quantity': 1, 'fraction': .5,
              'consumed_at': datetime.now(timezone.utc).isoformat(), 'nutrition': nutrition(600, 40).model_dump(mode='json')}
    assert client.put('/api/consumption', json=[record]).status_code == 200
    assert client.put('/api/consumption', json=[record]).status_code == 200
    diary = client.get('/api/daily-context').json()
    assert diary['context']['meal_count'] == 2
    assert diary['context']['known_intake']['protein_g'] == 20
    assert diary['context']['remaining']['protein_g'] is None
    assert diary['context']['signals'] == []
    cookie = client.cookies.get('macro_session')
    restarted = main.create_app()
    restarted.dependency_overrides[get_settings] = lambda: settings
    with TestClient(restarted) as restored:
        restored.cookies.set('macro_session', cookie)
        assert restored.get('/api/session').json()['profile']['diet_plan']['goal'] == 'gain_muscle'
        assert len(restored.get('/api/daily-context').json()['entries']) == 1
        assert len(restored.get('/api/consumption').json()) == 1
        assert restored.delete('/api/food-diary/' + created.json()['id']).status_code == 204
        assert restored.get('/api/daily-context').json()['entries'] == []


def test_diary_is_scoped_to_session_and_validates_inputs(api):
    client, _ = api
    created = client.post('/api/food-diary', json={'description': 'Frutas'}).json()
    future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    assert client.post('/api/food-diary', json={'description': 'Frutas', 'consumed_at': future}).status_code == 422
    assert client.post('/api/food-diary', json={'description': 'Frutas', 'consumed_at': '2026-10-18T15:00:00'}).status_code == 422
    assert client.post('/api/food-diary', json={'description': 'Frutas', 'nutrition': {'protein_g': -1}}).status_code == 422
    original = client.cookies.get('macro_session')
    client.cookies.clear()
    client.get('/api/session')
    assert client.get('/api/daily-context').json()['entries'] == []
    client.delete('/api/food-diary/' + created['id'])
    client.cookies.clear()
    client.cookies.set('macro_session', original)
    assert len(client.get('/api/daily-context').json()['entries']) == 1
