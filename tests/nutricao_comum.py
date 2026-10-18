"""Fábricas compartilhadas pelos testes da pipeline de calorias."""
import json
from pathlib import Path

from app.core.config import get_settings
from app.schemas.macro import MealCandidate
from app.services.nutrition.modelos import Ingrediente, Leitura, Macros

FIXTURES = Path(__file__).parent / "fixtures"
DADOS = Path(__file__).resolve().parents[1] / "app/services/nutrition/dados"


def settings(tmp_path, **extra):
    base = dict(gemini_api_key="k", openrouter_api_key="k", calorias_base_path=tmp_path / "produtos.json",
                calorias_dados_dir=DADOS, calorias_busca_web=True, calorias_buscar_bases=True,
                calorias_estimar_sempre=True, calorias_amostras=1)
    base.update(extra)
    return get_settings().model_copy(update=base)


def candidato(**campos) -> MealCandidate:
    dados = dict(merchant_id="m1", merchant_name="Pizza Express", item_id="i1", name="Pizza Margherita",
                 description="Mussarela e manjericão. 400 g.", image_url="https://x/y.jpg", price_cents=3290,
                 currency="BRL", option_groups=[], available=True, simulated=False)
    dados.update(campos)
    return MealCandidate(**dados)


def candidato_do_mcp() -> MealCandidate:
    """Item montado a partir do payload real do getItem (tests/fixtures/getItem_pizza.json)."""
    item = json.loads((FIXTURES / "getItem_pizza.json").read_text(encoding="utf-8"))
    return candidato(merchant_id=item["merchantId"], merchant_name=item["merchantName"], item_id=item["itemId"],
                     name=item["itemName"], description=item["itemDescription"], image_url=item["itemImageUrl"])


def leitura(fonte="gemini", kcal=800.0, prot=35.0, carb=90.0, gord=30.0, peso=None, **extra) -> Leitura:
    dados = dict(fonte=fonte, macros=Macros(kcal, prot, carb, gord), faixa_min=kcal * 0.85, faixa_max=kcal * 1.15,
                 confianca=0.6, porcao_base="pizza inteira", peso_g=peso,
                 ingredientes=[Ingrediente("arroz", 200), Ingrediente("feijão", 100)],
                 suposicoes=[f"suposição {fonte}"], justificativa=f"justificativa {fonte}")
    dados.update(extra)
    return Leitura(**dados)
