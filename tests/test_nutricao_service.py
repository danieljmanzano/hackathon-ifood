import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from app.schemas.macro import NutritionResult
from app.services.nutrition import service
from tests.nutricao_comum import candidato, settings


def _pronto():
    return NutritionResult(state="ready", method="estimated", portion_basis="prato", calories=600, minimum=500,
                           maximum=700, pipeline_version=service.PIPELINE_VERSION,
                           obtained_at=datetime.now(timezone.utc))


def test_base_local_evita_recalcular(tmp_path):
    service._cache.clear()
    s = settings(tmp_path)
    c = candidato(item_id="item-base-local")
    with patch.object(service, "calcular", AsyncMock(return_value=_pronto())) as calc:
        primeiro = asyncio.run(service.estimate_nutrition(c, s))
        assert primeiro.calories == 600 and calc.await_count == 1
        assert (tmp_path / "produtos.json").exists()

        service._cache.clear()  # simula reinício do servidor
        segundo = asyncio.run(service.estimate_nutrition(c, s))
        assert segundo.calories == 600 and calc.await_count == 1  # veio da base


def test_falha_nao_e_gravada_na_base(tmp_path):
    service._cache.clear()
    s = settings(tmp_path)
    with patch.object(service, "calcular", AsyncMock(side_effect=asyncio.TimeoutError())):
        r = asyncio.run(service.estimate_nutrition(candidato(item_id="item-falha"), s))
    assert r.state == "error"
    assert not (tmp_path / "produtos.json").exists()


def test_sem_chaves_fica_indisponivel(tmp_path):
    service._cache.clear()
    s = settings(tmp_path, openrouter_api_key="")
    r = asyncio.run(service.estimate_nutrition(candidato(item_id="item-sem-chave"), s))
    assert r.state == "unavailable"
