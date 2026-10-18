from uuid import uuid4

from fastapi import APIRouter, Depends, Request, Response

from app.core.config import Settings, get_settings
from app.core.exceptions import MacroError
from app.domain import rank, search_terms, select
from app.schemas.macro import (
    Address,
    AddressInput,
    CheckoutInput,
    CheckoutSummary,
    ConfirmationInput,
    MealCandidate,
    MealRequest,
    Message,
    OrderRecord,
    SelectionInput,
    Session,
    UserProfile,
)
from app.services.mock_ifood import MockIFood

router = APIRouter()
_mock_provider = MockIFood()


def get_provider(settings: Settings = Depends(get_settings)):
    return _mock_provider


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

    return mutate_session(request, session, update)


@router.post("/search", response_model=Session)
async def search(
    payload: MealRequest,
    request: Request,
    session: Session = Depends(current_session),
    provider: MockIFood = Depends(get_provider),
):
    editable(session)
    if session.address is None:
        raise MacroError("Selecione o endereço antes de buscar.", 422)
    query, budget = search_terms(payload)
    if budget is None:
        budget = session.profile.default_budget_cents
    candidates = await provider.search(query, session.address, budget)
    recommendations = rank(candidates, payload, session.profile, budget)

    def update(s: Session):
        s.budget_cents = budget
        s.recommendations = recommendations
        s.selected = None
        s.summary = None
        message = (
            "Encontrei estas opções. Escolha um prato para ver os complementos."
            if recommendations
            else "Não encontrei opções com esses filtros. Ajuste o orçamento ou suas preferências e busque novamente."
        )
        s.messages = (
            s.messages
            + [
                Message(role="user", text=payload.text),
                Message(role="assistant", text=message),
            ]
        )[-40:]

    return mutate_session(request, session, update)


@router.get("/items/{merchant_id}/{item_id}")
async def item(
    merchant_id: str,
    item_id: str,
    session: Session = Depends(current_session),
    provider: MockIFood = Depends(get_provider),
):
    if not session.address or not any(
        (r.candidate.merchant_id, r.candidate.item_id) == (merchant_id, item_id)
        for r in session.recommendations
    ):
        raise MacroError("Escolha um item da busca atual.", 422)
    return await provider.item(merchant_id, item_id, session.address)


@router.put("/selection", response_model=Session)
async def selection(
    payload: SelectionInput,
    request: Request,
    session: Session = Depends(current_session),
    provider: MockIFood = Depends(get_provider),
):
    editable(session)
    if not session.address or not any(
        (r.candidate.merchant_id, r.candidate.item_id) == (payload.merchant_id, payload.item_id)
        for r in session.recommendations
    ):
        raise MacroError("Escolha um item da busca atual.", 422)
    candidate = await provider.item(payload.merchant_id, payload.item_id, session.address)
    selected_item = select(candidate, payload)

    def update(s: Session):
        s.selected = selected_item
        s.summary = None

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
