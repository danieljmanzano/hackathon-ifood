from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

from fastapi import APIRouter, Depends, Request, Response

from app.core.config import Settings, get_settings
from app.core.exceptions import MacroError
from app.domain import rank, select
from app.schemas.macro import (
    Address,
    AddressCreated,
    AddressInput,
    CheckoutInput,
    CheckoutSummary,
    ConfirmationInput,
    CreateAddressInput,
    GeocodeInput,
    GeocodeResult,
    MealCandidate,
    MealRequest,
    MerchantSummary,
    Message,
    OrderRecord,
    SelectionInput,
    Session,
    UserProfile,
)
if TYPE_CHECKING:
    from app.services.ifood_live import MCPIFood
from app.services.mock_ifood import MockIFood
from app.services.nutrition import enrich_recommendations, estimate_selected, refresh_recommendations
from app.schemas.reviews import Review, ReviewInput, UserTastes
from app.schemas.macro import now
from app.services.review_recommendations import review_context
from app.services.llm_meal_intent import interpret_intent

router = APIRouter()
_mock_provider = MockIFood()
_live_provider: MCPIFood | None = None


def get_provider(settings: Settings = Depends(get_settings)):
    """Modo live usa o MCP real do iFood; mock usa o catálogo fictício."""
    global _live_provider
    if settings.ifood_mode != "live":
        return _mock_provider
    if _live_provider is None:
        from app.services.ifood_live import MCPIFood

        _live_provider = MCPIFood(settings)
    return _live_provider


def live_only(provider, feature: str):
    """Restaurantes próximos, cardápio e cadastro de endereço só existem no iFood real."""
    if not hasattr(provider, feature):
        raise MacroError("Disponível somente no modo live (IFOOD_MODE=live).", 409)


def offered(session: Session, merchant_id: str, item_id: str) -> bool:
    """Item veio da busca atual ou do cardápio aberto."""
    return any(
        (r.candidate.merchant_id, r.candidate.item_id) == (merchant_id, item_id)
        for r in session.recommendations
    ) or (session.menu_merchant_id == merchant_id and item_id in session.menu_item_ids)


def current_session(request: Request, settings: Settings = Depends(get_settings)) -> Session:
    db = request.app.state.db
    session = db.get(request.cookies.get("macro_session", ""))
    if session is None or session.mode != settings.ifood_mode:
        raise MacroError("Sua sessão expirou ou o modo mudou. Recarregue a página.", 401)
    return session


def editable(session: Session) -> None:
    if session.order:
        raise MacroError("Este pedido já foi confirmado. Inicie uma nova sessão para outro pedido.")


def mutate_session(request: Request, snapshot: Session, operation) -> Session:
    db = request.app.state.db
    with db.transaction() as connection:
        session = db.get(snapshot.id, connection)
        if session != snapshot:
            raise MacroError("A sessão mudou em outra aba. Atualize antes de continuar.")
        operation(session)
        db.save(session, connection)
        return session


@router.get("/health")
def health(settings: Settings = Depends(get_settings)):
    return {"status": "ok", **settings.public_status()}


@router.get("/session", response_model=Session)
def session(request: Request, response: Response, settings: Settings = Depends(get_settings)):
    db = request.app.state.db
    existing = db.get(request.cookies.get("macro_session", ""))
    if existing and existing.mode == settings.ifood_mode:
        return existing
    identity = str(uuid4())
    created = Session(id=identity, mode=settings.ifood_mode, profile=UserProfile(id=identity))
    db.save(created)
    review_context(db, created.profile.id, created.mode == "mock", created.profile)
    response.set_cookie(
        "macro_session",
        identity,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 7,
    )
    return created


@router.get("/integration/diagnostic")
async def diagnostic(
    session: Session = Depends(current_session),
    provider: MockIFood = Depends(get_provider),
):
    return await provider.diagnostic()


@router.get("/addresses")
async def addresses(
    session: Session = Depends(current_session),
    provider: MockIFood = Depends(get_provider),
):
    return await provider.addresses()


@router.post("/addresses/geocode", response_model=GeocodeResult)
async def geocode(
    payload: GeocodeInput,
    session: Session = Depends(current_session),
    provider: MockIFood = Depends(get_provider),
):
    """Etapa 1 do cadastro: localiza o endereço digitado. Nada é salvo ainda."""
    editable(session)
    live_only(provider, "geocode")
    return await provider.geocode(payload.address)


@router.post("/addresses", response_model=AddressCreated)
async def create_address(
    payload: CreateAddressInput,
    request: Request,
    session: Session = Depends(current_session),
    provider: MockIFood = Depends(get_provider),
):
    """Etapa 2: salva o candidato confirmado na conta do iFood e já o seleciona para a entrega."""
    editable(session)
    live_only(provider, "create_address")
    before = {a.id for a in await provider.addresses()}
    new_id = await provider.create_address(payload)
    available_addresses = await provider.addresses()
    created = next((a for a in available_addresses if a.id == new_id), None) or next(
        (a for a in available_addresses if a.id not in before), None
    )
    if created is None:
        raise MacroError("Endereço salvo no iFood, mas ainda não apareceu na lista. Recarregue os endereços.", 502)

    def update(s: Session):
        s.address = created
        s.selected = None
        s.summary = None
        s.recommendations = []

    return AddressCreated(session=mutate_session(request, session, update), addresses=available_addresses)


@router.put("/session/address", response_model=Session)
async def set_address(
    payload: AddressInput,
    request: Request,
    session: Session = Depends(current_session),
    provider: MockIFood = Depends(get_provider),
):
    editable(session)
    available_addresses = await provider.addresses()
    address = next((a for a in available_addresses if a.id == payload.address_id), None)
    if address is None:
        raise MacroError("Selecione um endereço da lista atual.", 422)

    def update(s: Session):
        s.address = address
        s.selected = None
        s.summary = None
        s.recommendations = []

    return mutate_session(request, session, update)


@router.put("/profile", response_model=Session)
def update_profile(
    payload: UserProfile,
    request: Request,
    session: Session = Depends(current_session),
):
    if payload.id != session.id:
        raise MacroError("Perfil não pertence à sessão.", 403)

    def update(s: Session):
        s.profile = payload

    updated = mutate_session(request, session, update)
    review_context(request.app.state.db, updated.profile.id, updated.mode == "mock", updated.profile)
    return updated


@router.post("/search", response_model=Session)
async def search(
    payload: MealRequest,
    request: Request,
    session: Session = Depends(current_session),
    provider: MockIFood = Depends(get_provider),
    settings: Settings = Depends(get_settings),
):
    editable(session)
    if session.address is None:
        raise MacroError("Selecione o endereço antes de buscar.", 422)
    intent = await interpret_intent(payload, settings)
    query, budget = intent.provider_query, intent.budget_cents
    if budget is None:
        budget = session.profile.default_budget_cents
    candidates = await provider.search(query, session.address, budget)
    context = review_context(request.app.state.db, session.profile.id, session.mode == "mock", session.profile)
    recommendations = rank(candidates, payload, session.profile, budget, context, session.recent_recommendations, intent=intent)
    recommendations = await enrich_recommendations(
        recommendations, settings, prazo=settings.nutrition_search_budget_seconds
    )

    def update(s: Session):
        s.budget_cents = budget
        s.request_intent = intent
        s.recommendations = recommendations
        s.recent_recommendations = (
            s.recent_recommendations
            + [(r.candidate.merchant_id, r.candidate.item_id) for r in recommendations]
        )[-18:]
        s.selected = None
        s.summary = None
        message = (
            ("Busquei opções considerando: " + ", ".join(intent.labels) + ". Confira os detalhes de cada sugestão."
             if intent.labels else "Encontrei estas opções. Escolha um prato para ver os complementos.")
            if recommendations
            else "Não encontrei opções com esses filtros. Ajuste o orçamento ou suas preferências e busque novamente."
        )
        if recommendations and intent.context_summary:
            message = intent.context_summary + " " + message
        s.messages = (
            s.messages
            + [
                Message(role="user", text=payload.text),
                Message(role="assistant", text=message),
            ]
        )[-40:]

    return mutate_session(request, session, update)


@router.get("/reviews/me", response_model=list[Review])
def my_reviews(request: Request, session: Session = Depends(current_session)):
    return review_context(request.app.state.db, session.profile.id, session.mode == "mock", session.profile).history


@router.get("/profile/tastes", response_model=UserTastes)
def my_tastes(request: Request, session: Session = Depends(current_session)):
    return review_context(request.app.state.db, session.profile.id, session.mode == "mock", session.profile).tastes


@router.put("/reviews", response_model=Review)
async def save_review(
    payload: ReviewInput,
    request: Request,
    session: Session = Depends(current_session),
    provider: MockIFood = Depends(get_provider),
):
    # Apenas itens conhecidos pela sessão podem receber avaliações. Não implica compra verificada.
    selected = session.selected
    history = review_context(request.app.state.db, session.profile.id, session.mode == "mock").history
    previously_reviewed = any(
        (r.merchant_id, r.item_id) == (payload.merchant_id, payload.item_id) for r in history
    )
    if not previously_reviewed and not offered(session, payload.merchant_id, payload.item_id) and not (
        selected and (selected.candidate.merchant_id, selected.candidate.item_id)
        == (payload.merchant_id, payload.item_id)
    ):
        raise MacroError("Escolha um item da busca ou do cardápio para avaliar.", 422)
    if session.address is None:
        raise MacroError("Selecione um endereço antes de avaliar.", 422)
    candidate = await provider.item(payload.merchant_id, payload.item_id, session.address)
    review = Review(
        **payload.model_dump(), id=str(uuid4()), user_id=session.profile.id,
        created_at=now(), simulated=session.mode == "mock",
        merchant_name=candidate.merchant_name, item_name=candidate.name,
    )
    request.app.state.db.save_review(review)
    review_context(request.app.state.db, session.profile.id, session.mode == "mock", session.profile)
    return review


@router.get("/merchants", response_model=list[MerchantSummary])
async def merchants(
    session: Session = Depends(current_session),
    provider: MockIFood = Depends(get_provider),
):
    if session.address is None:
        raise MacroError("Selecione o endereço antes de ver os restaurantes.", 422)
    live_only(provider, "merchants")
    return await provider.merchants(session.address)


@router.get("/merchants/{merchant_id}/menu", response_model=list[MealCandidate])
async def menu(
    merchant_id: str,
    request: Request,
    session: Session = Depends(current_session),
    provider: MockIFood = Depends(get_provider),
):
    if session.address is None:
        raise MacroError("Selecione o endereço antes de ver o cardápio.", 422)
    live_only(provider, "menu")
    items = await provider.menu(merchant_id, session.address)

    def update(s: Session):
        s.menu_merchant_id = merchant_id
        s.menu_item_ids = [i.item_id for i in items]

    mutate_session(request, session, update)
    return items


@router.get("/recommendations/nutrition", response_model=Session)
def recommendations_nutrition(
    request: Request,
    session: Session = Depends(current_session),
    settings: Settings = Depends(get_settings),
):
    """Entrega as calorias das recomendações que estavam "pending" quando a busca respondeu."""
    if not any(r.nutrition.state == "pending" for r in session.recommendations):
        return session
    updated = refresh_recommendations(session.recommendations, settings)
    if [r.nutrition for r in updated] == [r.nutrition for r in session.recommendations]:
        return session
    ids = [(r.candidate.merchant_id, r.candidate.item_id) for r in session.recommendations]

    def update(s: Session):
        # Só aplica se a busca não mudou enquanto isso.
        if [(r.candidate.merchant_id, r.candidate.item_id) for r in s.recommendations] == ids:
            s.recommendations = updated

    return mutate_session(request, session, update)


@router.get("/items/{merchant_id}/{item_id}")
async def item(
    merchant_id: str,
    item_id: str,
    session: Session = Depends(current_session),
    provider: MockIFood = Depends(get_provider),
):
    if not session.address or not offered(session, merchant_id, item_id):
        raise MacroError("Escolha um item da busca atual ou do cardápio aberto.", 422)
    return await provider.item(merchant_id, item_id, session.address)


@router.put("/selection", response_model=Session)
async def selection(
    payload: SelectionInput,
    request: Request,
    session: Session = Depends(current_session),
    provider: MockIFood = Depends(get_provider),
    settings: Settings = Depends(get_settings),
):
    editable(session)
    if not session.address or not offered(session, payload.merchant_id, payload.item_id):
        raise MacroError("Escolha um item da busca atual ou do cardápio aberto.", 422)
    candidate = await provider.item(payload.merchant_id, payload.item_id, session.address)
    selected_item = select(candidate, payload)
    # Prato montado: calcula as calorias com a descrição completa e as opções escolhidas.
    selected_item = selected_item.model_copy(
        update={"nutrition": await estimate_selected(selected_item, settings)}
    )

    def update(s: Session):
        s.selected = selected_item
        s.summary = None

    return mutate_session(request, session, update)


@router.get("/selection/nutrition", response_model=Session)
async def selection_nutrition(
    request: Request,
    session: Session = Depends(current_session),
    settings: Settings = Depends(get_settings),
):
    """Atualiza a estimativa do prato escolhido quando ela ainda estava "pending"."""
    if not session.selected or session.selected.nutrition.state != "pending":
        return session
    nutrition = await estimate_selected(session.selected, settings, aguardar=False)
    if nutrition.state == "pending":
        return session

    def update(s: Session):
        if s.selected and s.selected.nutrition.state == "pending":
            s.selected = s.selected.model_copy(update={"nutrition": nutrition})

    return mutate_session(request, session, update)


@router.get("/checkout/choices")
def choices(
    session: Session = Depends(current_session),
    provider: MockIFood = Depends(get_provider),
    settings: Settings = Depends(get_settings),
):
    if not provider.simulated or settings.ifood_mode != "mock":
        raise MacroError("Checkout real bloqueado até validar ferramentas e ambiente de teste.", 403)
    return provider.checkout_choices()


@router.post("/checkout/review", response_model=Session)
def review(
    payload: CheckoutInput,
    request: Request,
    session: Session = Depends(current_session),
    provider: MockIFood = Depends(get_provider),
    settings: Settings = Depends(get_settings),
):
    if not provider.simulated or settings.ifood_mode != "mock":
        raise MacroError("Checkout real bloqueado até validar ferramentas e ambiente de teste.", 403)
    editable(session)
    if not session.selected or not session.address:
        raise MacroError("Selecione prato, complementos e endereço antes de revisar.", 422)
    available_choices = provider.checkout_choices()
    delivery = next((d for d in available_choices["delivery"] if d.id == payload.delivery_id), None)
    payment = next((p for p in available_choices["payment"] if p.id == payload.payment_id), None)
    if not delivery or not payment:
        raise MacroError("Entrega ou pagamento não pertence às opções disponíveis.", 422)

    def update(s: Session):
        subtotal = s.selected.unit_total_cents * s.selected.quantity
        s.summary = CheckoutSummary(
            cart_id=s.summary.cart_id if s.summary else f"demo-cart-{uuid4()}",
            items=[s.selected],
            address=s.address,
            delivery=delivery,
            payment=payment,
            subtotal_cents=subtotal,
            total_cents=subtotal + delivery.fee_cents,
            version=str(uuid4()),
            simulated=True,
        )

    return mutate_session(request, session, update)


@router.post("/checkout/confirm", response_model=Session)
def confirm(
    payload: ConfirmationInput,
    request: Request,
    settings: Settings = Depends(get_settings),
):
    if settings.ifood_mode != "mock":
        raise MacroError("Checkout real bloqueado até validar ferramentas e ambiente de teste.", 403)
    db = request.app.state.db
    with db.transaction() as connection:
        s = db.get(request.cookies.get("macro_session", ""), connection)
        if not s or s.mode != "mock":
            raise MacroError("Sessão inválida. Recarregue a página.", 401)
        if not s.summary or payload.version != s.summary.version:
            raise MacroError("O resumo mudou. Revise o pedido e confirme a nova versão.")
        if not s.order:
            s.order = OrderRecord(
                id=f"demo-order-{uuid4()}",
                cart_id=s.summary.cart_id,
                status="submitted",
                simulated=True,
            )
            db.save(s, connection)
        return s
