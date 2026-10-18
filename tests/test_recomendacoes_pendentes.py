"""GET /api/recommendations/nutrition não pode dar 500 quando um cálculo "pending" se perdeu (ex.: reload do servidor)."""
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app
from app.schemas.macro import NutritionResult, Recommendation
from app.services.nutrition import service
from tests.nutricao_comum import candidato, settings

client = TestClient(app)


def _pendente(item_id):
    return Recommendation(candidate=candidato(item_id=item_id), nutrition=service._resultado("pending"),
                          reasons=[], limitations=[])


def _pronto():
    return NutritionResult(state="ready", method="estimated", portion_basis="prato", calories=600, minimum=500,
                           maximum=700, pipeline_version=service.PIPELINE_VERSION,
                           obtained_at=datetime.now(timezone.utc))


def test_servico_fora_do_loop_nao_estoura_e_entrega_o_que_esta_no_cache(tmp_path):
    service._cache.clear(); service._em_andamento.clear()
    s = settings(tmp_path)
    sem_cache, com_cache = _pendente("a"), _pendente("b")
    service._cache[service._chave(com_cache.candidate, None)] = _pronto()
    a, b = service.refresh_recommendations([sem_cache, com_cache], s)  # chamada de thread comum: sem loop
    assert a.nutrition.state == "pending" and b.nutrition.state == "ready" and b.nutrition.calories == 600
    assert not service._em_andamento  # nada foi iniciado (e nenhuma corrotina ficou sem await)


def test_endpoint_reinicia_o_calculo_perdido_em_vez_de_dar_500():
    anterior = dict(app.dependency_overrides)
    app.dependency_overrides[get_settings] = lambda: get_settings().model_copy(
        update={"openrouter_api_key": "k", "nutrition_provider": "openrouter"})

    async def calculo(item, settings):  # como o estimate_nutrition real: o resultado pronto vai para o cache
        resultado = _pronto()
        service._cache[service._chave(item, None)] = resultado
        return resultado
    try:
        with TestClient(app) as c, patch.object(service, "estimate_nutrition", calculo):  # `with`: um loop só
            sid = c.get("/api/session").json()["id"]
            sessao = app.state.db.get(sid)
            sessao.recommendations = [_pendente("perdido")]
            app.state.db.save(sessao)
            service._cache.clear(); service._em_andamento.clear()  # como após um reload: ninguém está calculando
            estados = []
            for _ in range(20):
                r = c.get("/api/recommendations/nutrition", cookies={"macro_session": sid})
                assert r.status_code == 200  # antes: 500 "no running event loop"
                estados.append(r.json()["recommendations"][0]["nutrition"]["state"])
                if estados[-1] == "ready":
                    break
            assert estados[0] == "pending" and estados[-1] == "ready"  # recomeçou em segundo plano e entregou
    finally:
        app.dependency_overrides.clear(); app.dependency_overrides.update(anterior)
