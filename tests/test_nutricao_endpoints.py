"""Endpoints de calorias pelo caminho real de tarefas em segundo plano (sem substituir refresh/estimate)."""
import asyncio
import time

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.schemas.macro import NutritionResult
from app.services.nutrition import service

PRONTO = NutritionResult(state='ready', portion_basis='uma porção', method='database', calories=600,
                         minimum=550, maximum=650, protein_g=40, carbs_g=60, fat_g=20, portion_grams=500,
                         source_name='Base de teste', evidence='Dados fictícios de teste')


@pytest.fixture
def client(tmp_path, monkeypatch):
    import app.main as main
    settings = Settings(_env_file=None, ifood_mode='mock', database_path=tmp_path / 'test.sqlite3',
                        calorias_base_path=tmp_path / 'produtos.json', nutrition_provider='openrouter',
                        openrouter_api_key='test', openai_api_key='', gemini_api_key='', calorias_log='off',
                        intent_llm_enabled=False, review_llm_enabled=False,
                        nutrition_search_budget_seconds=0, nutrition_selection_budget_seconds=0.05)

    async def calcular_devagar(*args):
        await asyncio.sleep(0.3)
        return PRONTO

    monkeypatch.setattr(service, 'calcular', calcular_devagar)
    monkeypatch.setattr(service, '_cache', {})
    monkeypatch.setattr(service, '_em_andamento', {})
    monkeypatch.setattr(main, 'get_settings', lambda: settings)
    application = main.create_app()
    application.dependency_overrides[get_settings] = lambda: settings
    with TestClient(application) as client:
        client.get('/api/session')
        client.put('/api/session/address', json={'address_id': 'demo-address'})
        yield client


def until_ready(client, path, states):
    for _ in range(100):
        response = client.get(path)
        assert response.status_code == 200, response.text
        if all(state(response.json()) == 'ready' for state in states):
            return response.json()
        time.sleep(0.02)
    raise AssertionError(f'{path} não ficou pronto')


def test_recommendation_nutrition_refresh_restarts_lost_tasks_without_crashing(client):
    before = client.post('/api/search', json={'text': 'almoço'}).json()
    assert all(r['nutrition']['state'] == 'pending' for r in before['recommendations'])
    # Simula um cálculo perdido (servidor reiniciado): o refresh precisa reiniciá-lo num loop ativo.
    service._em_andamento.clear()
    after = until_ready(client, '/api/recommendations/nutrition',
                        [lambda s, i=i: s['recommendations'][i]['nutrition']['state']
                         for i in range(len(before['recommendations']))])
    assert after['recommendations'][0]['nutrition']['calories'] == 600


def test_selection_answers_before_nutrition_and_finishes_in_background(client):
    recommendations = client.post('/api/search', json={'text': 'almoço'}).json()['recommendations']
    candidate = next(r['candidate'] for r in recommendations
                     if not any(g['min_selections'] > 0 for g in r['candidate']['option_groups']))
    started = time.monotonic()
    response = client.put('/api/selection', json={'merchant_id': candidate['merchant_id'],
                                                  'item_id': candidate['item_id']})
    assert response.status_code == 200
    assert time.monotonic() - started < 0.3  # não esperou o cálculo inteiro
    assert response.json()['selected']['nutrition']['state'] == 'pending'
    done = until_ready(client, '/api/selection/nutrition', [lambda s: s['selected']['nutrition']['state']])
    assert done['selected']['nutrition']['calories'] == 600
