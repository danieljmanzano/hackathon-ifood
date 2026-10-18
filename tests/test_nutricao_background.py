"""Cálculo em segundo plano: a busca não espera as calorias (prazo curto) e o refresh entrega depois."""
import asyncio
from unittest.mock import patch

from app.schemas.macro import Recommendation
from app.services.nutrition import service
from tests.nutricao_comum import candidato, settings
from tests.test_nutricao_service import _pronto


def _rec(item_id):
    return Recommendation(candidate=candidato(item_id=item_id), nutrition=service._resultado("pending"),
                          reasons=[], limitations=["Informação nutricional indisponível. Calorias e macros."])


def test_prazo_zero_devolve_pending_e_o_refresh_entrega_quando_termina(tmp_path):
    service._cache.clear(); service._em_andamento.clear(); service._limites.clear()
    s = settings(tmp_path)

    async def calculo(item, settings):
        await asyncio.sleep(0.05)
        resultado = _pronto()
        service._cache[service._chave(item, None)] = resultado  # o estimate_nutrition real também grava aqui
        return resultado

    async def cenario():
        with patch.object(service, "estimate_nutrition", calculo):
            recs = await service.enrich_recommendations([_rec("bg-1")], s, prazo=0)
            assert recs[0].nutrition.state == "pending"
            await asyncio.sleep(0.2)
            recs = service.refresh_recommendations(recs, s)
            assert recs[0].nutrition.state == "ready" and recs[0].nutrition.calories == 600
            assert not any(l.startswith("Informação nutricional indisponível") for l in recs[0].limitations)

    asyncio.run(cenario())


def test_refresh_sem_chaves_nao_inicia_nada(tmp_path):
    s = settings(tmp_path, gemini_api_key="", openrouter_api_key="")
    rec = _rec("bg-2")
    assert service.refresh_recommendations([rec], s)[0].nutrition.state == "pending"
    assert not service._em_andamento
