import json
from pathlib import Path

from app.core.exceptions import MacroError
from app.schemas.macro import (
    Address,
    DeliveryChoice,
    MealCandidate,
    MerchantSummary,
    PaymentChoice,
)

from app.services.mock_reviews import review_dataset


def catalog() -> list[MealCandidate]:
    path = Path(__file__).resolve().parents[2] / 'data' / 'mocks' / 'menu.json'
    return [MealCandidate.model_validate(item) for item in json.loads(path.read_text(encoding='utf-8'))]


class MockIFood:
    simulated = True

    async def addresses(self) -> list[Address]:
        return [
            Address(
                id="demo-address",
                label="Casa de demonstração",
                formatted="Rua Exemplo, 100 — endereço fictício",
                latitude=-22.0,
                longitude=-47.9,
            )
        ]

    async def search(
        self, query: str, address: Address, budget_cents: int | None
    ) -> list[MealCandidate]:
        return catalog()

    async def item(
        self, merchant_id: str, item_id: str, address: Address
    ) -> MealCandidate:
        for it in catalog():
            if (it.merchant_id, it.item_id) == (merchant_id, item_id):
                return it
        raise MacroError("Item indisponível. Faça outra busca.", 404)

    async def merchants(self, address: Address) -> list[MerchantSummary]:
        return [MerchantSummary(
            merchant_id=m.merchant_id, name=m.name, rating=m.rating,
            rating_count=m.rating_count, eta_min=m.eta_min, eta_max=m.eta_max,
            delivery_fee_cents=m.delivery_fee_cents, simulated=True,
        ) for m in review_dataset().establishments]

    async def menu(self, merchant_id: str, address: Address) -> list[MealCandidate]:
        items = [item for item in catalog() if item.merchant_id == merchant_id]
        if not items:
            raise MacroError("Estabelecimento fictício não encontrado.", 404)
        return items

    async def diagnostic(self) -> dict:
        return {
            "connected": False,
            "simulated": True,
            "tools": [],
            "message": "Simulação local ativa. Nenhuma ferramenta real foi acessada.",
        }

    def checkout_choices(self) -> dict[str, list]:
        return {
            "delivery": [
                DeliveryChoice(
                    id="demo-standard",
                    label="Entrega simulada • 30–40 min",
                    fee_cents=590,
                ),
                DeliveryChoice(
                    id="demo-express",
                    label="Entrega simulada • 20–30 min",
                    fee_cents=990,
                ),
            ],
            "payment": [
                PaymentChoice(
                    id="demo-payment", label="Pagamento fictício — nenhuma cobrança"
                )
            ],
        }
