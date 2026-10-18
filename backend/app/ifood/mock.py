from ..errors import MacroError
from ..schemas import Address, DeliveryChoice, MealCandidate, MerchantSummary, Option, OptionGroup, PaymentChoice


def catalog() -> list[MealCandidate]:
    base = OptionGroup(id="demo-base", name="Escolha a base", min_selections=1, max_selections=1,
                       options=[Option(id="demo-arroz", name="Arroz integral"),
                                Option(id="demo-pure", name="Purê de batata", price_cents=200)])
    extras = OptionGroup(id="demo-extra", name="Complemente seu prato", min_selections=0, max_selections=2,
                         options=[Option(id="demo-legumes", name="Legumes assados", price_cents=400),
                                  Option(id="demo-feijao", name="Feijão", price_cents=300)])
    return [MealCandidate(merchant_id="demo-cozinha", merchant_name="Cozinha do treino (demo)",
                          item_id=item_id, name=name, description=description, price_cents=price,
                          simulated=True, option_groups=[base, extras])
            for item_id, name, description, price in [
                ("demo-frango", "Frango grelhado da casa", "Frango grelhado, salada fresca e a base que você escolher.", 2790),
                ("demo-vegetal", "Prato de grão-de-bico", "Grão-de-bico refogado, abóbora assada, couve e sua escolha de base.", 2590),
                ("demo-carne", "Carne de panela", "Carne de panela com cenoura, salada e sua escolha de base.", 3290),
            ]]


class MockIFood:
    simulated = True

    async def addresses(self):
        return [Address(id="demo-address", label="Casa de demonstração", formatted="Rua Exemplo, 100 — endereço fictício",
                        latitude=-22.0, longitude=-47.9)]

    async def search(self, query: str, address: Address, budget_cents: int | None):
        return catalog()

    async def merchants(self, address: Address):
        return [MerchantSummary(merchant_id="demo-cozinha", name="Cozinha do treino (demo)", distance_km=1.2, rating=4.8,
                                rating_count=120, eta_min=30, eta_max=40, delivery_fee_cents=590,
                                minimum_order_cents=2000, simulated=True)]

    async def menu(self, merchant_id: str, address: Address):
        return [item for item in catalog() if item.merchant_id == merchant_id]

    async def item(self, merchant_id: str, item_id: str, address: Address):
        for item in catalog():
            if (item.merchant_id, item.item_id) == (merchant_id, item_id):
                return item
        raise MacroError("Item indisponível. Faça outra busca.", 404)

    async def diagnostic(self):
        return {"connected": False, "simulated": True, "tools": [],
                "message": "Simulação local ativa. Nenhuma ferramenta real foi acessada."}

    def checkout_choices(self):
        return {
            "delivery": [DeliveryChoice(id="demo-standard", label="Entrega simulada • 30–40 min", fee_cents=590),
                         DeliveryChoice(id="demo-express", label="Entrega simulada • 20–30 min", fee_cents=990)],
            "payment": [PaymentChoice(id="demo-payment", label="Pagamento fictício — nenhuma cobrança")],
        }
