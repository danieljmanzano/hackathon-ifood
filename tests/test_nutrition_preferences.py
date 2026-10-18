import asyncio
import json

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings, get_settings
from app.domain import rank
from app.schemas.macro import (MealCandidate, MealRequest, NutritionPreferences,
                               NutritionResult, Recommendation, UserProfile)
from app.services import llm_meal_intent
from app.services.meal_intent import parse_intent
from app.services.nutrition_preferences import (apply_profile_preferences, assess_nutrition,
                                               update_explanation)
from app.services.nutrition.pipeline import PIPELINE_VERSION
from app.services.nutrition.produtos import RepositorioProdutos, chave_produto


def item(index):
    return MealCandidate(merchant_id=f'nutrition-{index}', merchant_name=f'Restaurante {index}',
                         item_id=f'prato-{index}', name='Frango', description='Frango e acompanhamentos',
                         price_cents=2500)


def nutrition(calories=500, protein=30, carbs=40, fat=15, **changes):
    return NutritionResult(state='ready', portion_basis='um prato', calories=calories,
                           minimum=calories * .9, maximum=calories * 1.1,
                           method='estimated', protein_g=protein, carbs_g=carbs, fat_g=fat,
                           pipeline_version=PIPELINE_VERSION, **changes)


@pytest.mark.parametrize('text, field, value', [
    ('frango até 600 kcal', 'max_calories', 600),
    ('frango no máximo 550 calorias', 'max_calories', 550),
    ('frango pelo menos 30 g de proteína', 'min_protein_g', 30),
    ('frango até 25,5g de carboidratos', 'max_carbs_g', 25.5),
    ('frango no máximo 15 gramas de gordura', 'max_fat_g', 15),
])
def test_limits_are_not_food_or_budget(text, field, value):
    intent = parse_intent(MealRequest(text=text))
    assert getattr(intent.nutrition_preferences, field) == value
    assert intent.food_query == 'frango'
    assert intent.budget_cents is None


def test_nutritional_and_price_limits_coexist_and_daily_goal_is_not_a_meal_limit():
    intent = parse_intent(MealRequest(text='frango até 600 kcal e pelo menos 30 g de proteína até R$ 35'))
    assert intent.budget_cents == 3500
    assert intent.nutrition_preferences.max_calories == 600
    assert intent.nutrition_preferences.min_protein_g == 30
    assert intent.food_query == 'frango'
    for text in ('minha meta diária de 2000 kcal, quero frango', 'até 2000 kcal por dia, quero frango'):
        daily = parse_intent(MealRequest(text=text))
        assert not daily.nutrition_preferences.active
        assert daily.budget_cents is None
        assert daily.food_query == 'frango'


@pytest.mark.parametrize('text, expected', [
    ('quero mais proteína', ['high_protein']), ('quero low carb', ['low_carb']),
    ('quero menos gordura', ['low_fat']), ('quero poucas calorias', ['low_calorie']),
    ('não quero low carb', []),
])
def test_qualitative_preferences(text, expected):
    assert parse_intent(MealRequest(text=text)).nutrition_preferences.goals == expected


def test_request_overrides_profile_without_mutating_saved_defaults():
    profile = UserProfile(id='u', daily_calorie_goal=2000,
                          nutrition_preferences=NutritionPreferences(max_calories=500, min_protein_g=30))
    request = MealRequest(text='frango até 700 kcal', nutrition_preferences=NutritionPreferences(max_calories=650))
    intent = apply_profile_preferences(parse_intent(request), profile)
    assert intent.nutrition_preferences.max_calories == 650
    assert intent.nutrition_preferences.min_protein_g == 30
    assert profile.nutrition_preferences.max_calories == 500
    assert 'até 650 kcal por prato' in intent.labels
    assert all('2000' not in label for label in intent.labels)


@pytest.mark.parametrize('goal, best', [
    ('high_protein', 1), ('low_carb', 0), ('low_fat', 0), ('low_calorie', 0),
])
def test_actual_macros_change_ranking(goal, best):
    candidates = [item(i) for i in range(3)]
    known = {('nutrition-0', 'prato-0'): nutrition(400, 10, 10, 5),
             ('nutrition-1', 'prato-1'): nutrition(900, 60, 90, 40)}
    profile = UserProfile(id='u', nutrition_preferences=NutritionPreferences(goals=[goal]))
    ranked = rank(candidates, MealRequest(text='frango'), profile, None, nutrition_by_item=known)
    assert ranked[0].candidate.item_id == f'prato-{best}'
    assert ranked[-1].candidate.item_id == 'prato-2'
    assert any('estimativa' in reason for reason in ranked[0].reasons)
    assert any('ainda não verificadas' in limit for limit in ranked[-1].limitations)


def test_missing_macros_and_failed_targets_have_explicit_limitations():
    preferences = NutritionPreferences(min_protein_g=40, max_calories=600)
    missing = assess_nutrition(nutrition(protein=None), preferences)
    assert any('Não foi possível verificar' in limitation for limitation in missing.limitations)
    failed = assess_nutrition(nutrition(800, 10), preferences)
    assert failed.score < 3
    assert any('800 kcal' in limitation for limitation in failed.limitations)
    assert any('10 g de proteína' in limitation for limitation in failed.limitations)
    assert not failed.reasons
    assert assess_nutrition(NutritionResult(state='pending'), preferences).score == 0


def test_similar_nutrition_still_allows_rotation():
    candidates = [item(i) for i in range(4)]
    known = {(c.merchant_id, c.item_id): nutrition(protein=40 + index / 10)
             for index, c in enumerate(candidates)}
    profile = UserProfile(id='u', nutrition_preferences=NutritionPreferences(goals=['high_protein']))
    first = rank(candidates, MealRequest(text='frango'), profile, None, nutrition_by_item=known)
    second = rank(candidates, MealRequest(text='frango'), profile, None, nutrition_by_item=known,
                  recently_shown=[(r.candidate.merchant_id, r.candidate.item_id) for r in first])
    assert second[0].candidate.item_id == 'prato-0'
    assert first[0].candidate.item_id != second[0].candidate.item_id


def test_pending_explanations_are_replaced_without_losing_review_reasons():
    preferences = NutritionPreferences(min_protein_g=30)
    pending = NutritionResult(state='pending')
    before = Recommendation(candidate=item(0), nutrition=pending, reasons=['Sua avaliação foi positiva.'],
                            limitations=assess_nutrition(pending, preferences).limitations)
    after = update_explanation(before, before.model_copy(update={'nutrition': nutrition(protein=40)}), preferences)
    assert 'Sua avaliação foi positiva.' in after.reasons
    assert any('40 g de proteína' in reason for reason in after.reasons)
    assert all('ainda não verificadas' not in limit for limit in after.limitations)
    assert update_explanation(after, after, preferences) == after


def test_llm_can_extract_nutrition_but_cannot_invent_targets(monkeypatch):
    async def complete(*args, **kwargs):
        return json.dumps({'goals': [], 'food_query': 'frango', 'context_summary': 'Vou comparar as opções.',
                           'budget_cents': 60000,
                           'nutrition_preferences': {'goals': ['low_carb'], 'max_calories': 600,
                                                     'min_protein_g': 30}})
    monkeypatch.setattr(llm_meal_intent, 'chat_completion', complete)
    llm_meal_intent._cache.clear()
    settings = Settings(_env_file=None, intent_llm_enabled=True, openrouter_api_key='test')
    explicit = asyncio.run(llm_meal_intent.interpret_intent(MealRequest(text='frango low carb até 600 kcal'), settings))
    assert explicit.interpretation_source == 'llm'
    assert explicit.nutrition_preferences.max_calories == 600
    assert explicit.nutrition_preferences.min_protein_g is None
    assert explicit.budget_cents is None
    implicit = asyncio.run(llm_meal_intent.interpret_intent(MealRequest(text='treinei hoje, quero frango'), settings))
    assert implicit.nutrition_preferences.max_calories is None
    assert implicit.nutrition_preferences.min_protein_g is None
    llm_meal_intent._cache.clear()


@pytest.mark.parametrize('fields', [{'max_calories': -1}, {'min_protein_g': float('inf')},
                                   {'max_carbs_g': float('nan')}, {'goals': ['invalid']}])
def test_invalid_preferences_are_rejected(fields):
    with pytest.raises(ValidationError):
        NutritionPreferences(**fields)


def test_api_ranks_using_stored_nutrition_and_preserves_preferences(tmp_path, monkeypatch):
    import app.main as main
    from app.api.endpoints import macro
    candidates = [item(i) for i in range(6)]
    known = [nutrition(400, 10, 10), nutrition(900, 20, 80), nutrition(550, 50, 35),
             nutrition(450, 30, 15), nutrition(1000, 60, 60), nutrition(500, 40, 25)]
    settings = Settings(_env_file=None, ifood_mode='mock', intent_llm_enabled=False,
                        openrouter_api_key='', gemini_api_key='', openai_api_key='',
                        database_path=tmp_path / 'sessions.sqlite3', calorias_base_path=tmp_path / 'products.json')
    repository = RepositorioProdutos(settings.calorias_base_path)
    for candidate, result in zip(candidates, known):
        repository.put(chave_produto(candidate), result, candidate)
    queries = []

    class Provider:
        async def search(self, query, address, budget):
            queries.append((query, budget))
            return candidates

    monkeypatch.setattr(main, 'get_settings', lambda: settings)
    app = main.create_app()
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as client:
        session = client.get('/api/session').json()
        client.put('/api/session/address', json={'address_id': 'demo-address'})
        profile = {**session['profile'], 'nutrition_preferences': {'max_calories': 600, 'min_protein_g': 40}}
        assert client.put('/api/profile', json=profile).status_code == 200
        app.dependency_overrides[macro.get_provider] = Provider
        response = client.post('/api/search', json={'text': 'frango até R$ 30'})
        assert response.status_code == 200
        data = response.json()
        assert data['request_intent']['nutrition_preferences']['max_calories'] == 600
        assert [r['candidate']['item_id'] for r in data['recommendations']][:2] == ['prato-2', 'prato-5']
        assert all(r['nutrition']['state'] == 'ready' for r in data['recommendations'])
        assert all('ainda não verificadas' not in ' '.join(r['limitations']) for r in data['recommendations'])
        override = client.post('/api/search', json={'text': 'frango até 800 kcal'}).json()
        assert override['request_intent']['nutrition_preferences']['max_calories'] == 800
        assert override['profile']['nutrition_preferences']['max_calories'] == 600
        assert queries == [('frango', 3000), ('frango', None)]
        cookie = client.cookies.get('macro_session')
    # Uma nova instância restaura o perfil persistido, inclusive os novos campos.
    restarted = main.create_app()
    restarted.dependency_overrides[get_settings] = lambda: settings
    with TestClient(restarted) as client:
        client.cookies.set('macro_session', cookie)
        assert client.get('/api/session').json()['profile']['nutrition_preferences']['min_protein_g'] == 40


def test_api_limits_estimation_pool_and_refreshes_nutritional_reasons(tmp_path, monkeypatch):
    import app.main as main
    from app.api.endpoints import macro
    settings = Settings(_env_file=None, ifood_mode='mock', intent_llm_enabled=False,
                        openrouter_api_key='', gemini_api_key='', openai_api_key='',
                        database_path=tmp_path / 'pending.sqlite3', calorias_base_path=tmp_path / 'empty.json')
    class Provider:
        async def search(self, *args):
            return [item(i + 100) for i in range(30)]
    sizes = []
    async def pending(recommendations, settings, prazo):
        sizes.append(len(recommendations))
        return [r.model_copy(update={'nutrition': NutritionResult(state='pending')}) for r in recommendations]
    def ready(recommendations, settings):
        return [r.model_copy(update={'nutrition': nutrition(protein=45)}) for r in recommendations]
    monkeypatch.setattr(main, 'get_settings', lambda: settings)
    monkeypatch.setattr(macro, 'enrich_recommendations', pending)
    monkeypatch.setattr(macro, 'refresh_recommendations', ready)
    application = main.create_app()
    application.dependency_overrides[get_settings] = lambda: settings
    with TestClient(application) as client:
        client.get('/api/session')
        client.put('/api/session/address', json={'address_id': 'demo-address'})
        application.dependency_overrides[macro.get_provider] = Provider
        response = client.post('/api/search', json={'text': 'frango pelo menos 40 g de proteína'})
        assert response.status_code == 200
        before = response.json()['recommendations']
        assert sizes == [12]
        assert len(before) == 3
        assert all(r['nutrition']['state'] == 'pending' for r in before)
        after = client.get('/api/recommendations/nutrition').json()['recommendations']
        assert [r['candidate'] for r in before] == [r['candidate'] for r in after]
        assert all(any('45 g de proteína' in reason for reason in r['reasons']) for r in after)
        assert all('ainda não verificadas' not in ' '.join(r['limitations']) for r in after)
