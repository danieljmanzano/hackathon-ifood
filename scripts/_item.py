"""Carrega um item no formato do getItem do MCP (JSON) como MealCandidate, para os scripts de teste."""
import json
from pathlib import Path

from app.schemas.macro import MealCandidate

PADRAO = Path(__file__).resolve().parents[1] / "tests/fixtures/getItem_pizza.json"


def carregar_item(caminho: str | None = None) -> MealCandidate:
    item = json.loads(Path(caminho or PADRAO).read_text(encoding="utf-8"))
    return MealCandidate(
        merchant_id=item["merchantId"], merchant_name=item["merchantName"], item_id=item["itemId"],
        name=item["itemName"], description=item.get("itemDescription", ""), image_url=item.get("itemImageUrl"),
        price_cents=round(item["unitPrice"] * 100), currency="BRL", option_groups=[], available=True, simulated=False,
    )
