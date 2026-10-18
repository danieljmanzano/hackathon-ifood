import asyncio

from app.api.endpoints.macro import _com_descricoes
from app.schemas.macro import Address, MealCandidate, Recommendation
from app.services.ifood_live import DESCRICAO_PENDENTE


class _Provider:
    async def descricoes(self, candidates, address):
        return {(c.merchant_id, c.item_id): "Bolo Ana Maria 70g" for c in candidates if c.item_id == "1"}


def _rec(item_id):
    c = MealCandidate(merchant_id="m", merchant_name="Loja", item_id=item_id, name="Bolo", description=DESCRICAO_PENDENTE,
                      price_cents=500)
    return Recommendation.model_construct(candidate=c)


def test_descricao_real_substitui_a_pendente():
    addr = Address(id="a", label="x", formatted="y", latitude=0, longitude=0)
    out = asyncio.run(_com_descricoes(_Provider(), [_rec("1"), _rec("2")], addr))
    assert out[0].candidate.description == "Bolo Ana Maria 70g"
    assert out[1].candidate.description == DESCRICAO_PENDENTE


def test_provider_sem_descricoes_nao_muda_nada():
    recs = [_rec("1")]
    assert asyncio.run(_com_descricoes(object(), recs, None)) is recs
