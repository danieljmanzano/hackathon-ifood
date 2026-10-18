from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

NonNegative = Annotated[float, Field(ge=0, allow_inf_nan=False)]
Cents = Annotated[int, Field(ge=0, strict=True)]
Quantity = Annotated[int, Field(ge=1, le=20, strict=True)]
Text = Annotated[str, Field(min_length=1, max_length=2000, strip_whitespace=True)]


def now() -> datetime:
    return datetime.now(timezone.utc)


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class UserProfile(Model):
    id: str
    preferences: list[str] = Field(default_factory=list, max_length=30)
    restrictions: list[str] = Field(default_factory=list, max_length=30)
    dislikes: list[str] = Field(default_factory=list, max_length=30)
    default_budget_cents: Cents | None = None
    daily_calorie_goal: NonNegative | None = None


class MealRequest(Model):
    text: Text
    budget_cents: Cents | None = None
    restrictions: list[str] = Field(default_factory=list, max_length=30)


class Address(Model):
    id: str
    label: str
    formatted: str
    latitude: float = Field(ge=-90, le=90, allow_inf_nan=False)
    longitude: float = Field(ge=-180, le=180, allow_inf_nan=False)


ShortText = Annotated[str, Field(max_length=200, strip_whitespace=True)]


class GeocodeInput(Model):
    address: Annotated[str, Field(min_length=5, max_length=300, strip_whitespace=True)]


class AddressCandidate(Model):
    candidate_id: str
    formatted: str
    neighborhood: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class GeocodeResult(Model):
    match: Literal["SINGLE", "MULTIPLE"]
    candidates: list[AddressCandidate]


class CreateAddressInput(Model):
    address: Annotated[str, Field(min_length=5, max_length=300, strip_whitespace=True)]
    candidate_id: Annotated[str, Field(min_length=1, max_length=200)]
    neighborhood: ShortText = ""
    complement: ShortText = ""
    reference: ShortText = ""
    alias: Literal["", "CASA", "TRABALHO"] = ""


class AddressInput(Model):
    address_id: str


class Option(Model):
    id: str
    name: str
    price_cents: Cents = 0
    max_quantity: Quantity = 1


class OptionGroup(Model):
    id: str
    name: str
    min_selections: int = Field(ge=0)
    max_selections: int = Field(ge=0)
    options: list[Option]

    @model_validator(mode="after")
    def valid_limits(self):
        if self.min_selections > self.max_selections:
            raise ValueError("Limites inconsistentes no grupo de opções.")
        if len({o.id for o in self.options}) != len(self.options):
            raise ValueError("Opções duplicadas.")
        return self


class MealCandidate(Model):
    merchant_id: str
    merchant_name: str
    item_id: str
    name: str
    description: str
    image_url: str | None = None
    price_cents: Cents
    currency: Literal["BRL"] = "BRL"
    option_groups: list[OptionGroup] = Field(default_factory=list)
    available: bool = True
    simulated: bool = False


class SelectedOption(Model):
    group_id: str
    option_id: str
    quantity: Quantity = 1


class SelectionInput(Model):
    item_id: str
    merchant_id: str
    quantity: Quantity = 1
    options: list[SelectedOption] = Field(default_factory=list, max_length=100)


class NutritionResult(Model):
    state: Literal["pending", "ready", "unavailable", "error"] = "unavailable"
    portion_basis: str | None = None
    calories: NonNegative | None = None
    minimum: NonNegative | None = None
    maximum: NonNegative | None = None
    confidence: Literal["low", "medium", "high"] | None = None
    method: Literal["published", "estimated"] | None = None
    source_url: str | None = None
    source_name: str | None = None
    evidence: str | None = None
    assumptions: list[str] = Field(default_factory=list)
    pipeline_version: str = "not-connected"
    obtained_at: datetime | None = None

    @model_validator(mode="after")
    def validate_estimate(self):
        numbers = (self.minimum, self.calories, self.maximum)
        if self.state == "ready":
            if any(n is None for n in numbers) or not self.portion_basis or not self.method:
                raise ValueError("Uma estimativa disponível exige faixa, porção e método.")
            if not self.minimum <= self.calories <= self.maximum:
                raise ValueError("Faixa calórica inconsistente.")
            if self.method == "published" and not all((self.source_url, self.source_name, self.evidence)):
                raise ValueError("Informação publicada exige fonte e evidência.")
        elif any(n is not None for n in numbers):
            raise ValueError("Dados indisponíveis não podem conter calorias.")
        return self


class SelectedItem(Model):
    candidate: MealCandidate
    quantity: Quantity
    options: list[SelectedOption]
    option_labels: list[str]
    unit_total_cents: Cents
    # Calorias de uma unidade com as opções escolhidas (a quantidade é aplicada na exibição).
    nutrition: NutritionResult = Field(default_factory=NutritionResult)


class MerchantSummary(Model):
    merchant_id: str
    name: str
    logo_url: str | None = None
    is_open: bool = True
    distance_km: float | None = None
    rating: float | None = None
    rating_count: int | None = None
    eta_min: int | None = None
    eta_max: int | None = None
    delivery_fee_cents: Cents | None = None
    minimum_order_cents: Cents | None = None
    simulated: bool = False


class Recommendation(Model):
    candidate: MealCandidate
    nutrition: NutritionResult = Field(default_factory=NutritionResult)
    reasons: list[str]
    limitations: list[str]


class DeliveryChoice(Model):
    id: str
    label: str
    fee_cents: Cents


class PaymentChoice(Model):
    id: str
    label: str


class CheckoutInput(Model):
    delivery_id: str
    payment_id: str


class CheckoutSummary(Model):
    cart_id: str
    items: list[SelectedItem]
    address: Address
    delivery: DeliveryChoice
    payment: PaymentChoice
    subtotal_cents: Cents
    total_cents: Cents
    currency: Literal["BRL"] = "BRL"
    version: str
    simulated: bool


class ConfirmationInput(Model):
    version: str
    confirmed: Literal[True]


class OrderRecord(Model):
    id: str
    cart_id: str
    status: Literal["submitted", "uncertain"]
    simulated: bool
    created_at: datetime = Field(default_factory=now)


class ConsumptionEntry(Model):
    id: str
    order_id: str
    item_id: str
    fraction: float = Field(gt=0, le=1, allow_inf_nan=False)
    consumed_at: datetime
    source: Literal["user_confirmation"] = "user_confirmation"
    nutrition_snapshot: NutritionResult


class Message(Model):
    role: Literal["user", "assistant"]
    text: str


class AddressCreated(Model):
    session: "Session"
    addresses: list[Address]


class Session(Model):
    id: str = Field(default_factory=lambda: str(uuid4()))
    mode: Literal["mock", "live"]
    profile: UserProfile
    address: Address | None = None
    messages: list[Message] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)
    selected: SelectedItem | None = None
    summary: CheckoutSummary | None = None
    order: OrderRecord | None = None
    budget_cents: Cents | None = None
    # Cardápio aberto pelo usuário: libera abrir e escolher esses itens, como as recomendações.
    menu_merchant_id: str | None = None
    menu_item_ids: list[str] = Field(default_factory=list)


AddressCreated.model_rebuild()
