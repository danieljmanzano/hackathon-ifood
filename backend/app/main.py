from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .config import Settings
from .domain import rank, search_terms, select
from .errors import MacroError
from .ifood.mcp import MCPIFood
from .ifood.mock import MockIFood
from .schemas import (CheckoutInput, CheckoutSummary, ConfirmationInput, MealRequest,
                      Message, OrderRecord, SelectionInput, Session, UserProfile)
from .storage.database import Database


class AddressInput(BaseModel):
    address_id: str


def create_app(settings: Settings | None = None, provider=None) -> FastAPI:
    settings = settings or Settings()
    provider = provider or (MockIFood() if settings.ifood_mode == "mock" else MCPIFood(settings))

    @asynccontextmanager
    async def lifespan(app):
        app.state.db = Database(settings.database_path)
        yield

    app = FastAPI(title="Macro", version="0.1.0", lifespan=lifespan)

    @app.exception_handler(MacroError)
    async def domain_error(request, exc):
        return JSONResponse({"detail": exc.message}, status_code=exc.status)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        return JSONResponse({"detail": "Dados inválidos. Revise os campos e as quantidades."}, status_code=422)

    def current(request: Request) -> Session:
        session = app.state.db.get(request.cookies.get("macro_session", ""))
        if session is None or session.mode != settings.ifood_mode:
            raise MacroError("Sua sessão expirou ou o modo mudou. Recarregue a página.", 401)
        return session

    def editable(session):
        if session.order:
            raise MacroError("Este pedido já foi confirmado. Inicie uma nova sessão para outro pedido.")

    def mutate(snapshot, operation):
        with app.state.db.transaction() as connection:
            session = app.state.db.get(snapshot.id, connection)
            if session != snapshot:
                raise MacroError("A sessão mudou em outra aba. Atualize antes de continuar.")
            operation(session)
            app.state.db.save(session, connection)
            return session

    def mock_only():
        if not provider.simulated or settings.ifood_mode != "mock":
            raise MacroError("Checkout real bloqueado até validar ferramentas e ambiente de teste.", 403)

    @app.get("/api/health")
    def health():
        return {"status": "ok", **settings.public_status()}

    @app.get("/api/session", response_model=Session)
    def session(request: Request, response: Response):
        existing = app.state.db.get(request.cookies.get("macro_session", ""))
        if existing and existing.mode == settings.ifood_mode:
            return existing
        identity = str(uuid4())
        created = Session(id=identity, mode=settings.ifood_mode, profile=UserProfile(id=identity))
        app.state.db.save(created)
        response.set_cookie("macro_session", identity, httponly=True, samesite="strict", max_age=60 * 60 * 24 * 7)
        return created

    @app.get("/api/integration/diagnostic")
    async def diagnostic(request: Request):
        current(request)
        return await provider.diagnostic()

    @app.get("/api/addresses")
    async def addresses(request: Request):
        current(request)
        return await provider.addresses()

    @app.put("/api/session/address", response_model=Session)
    async def set_address(payload: AddressInput, request: Request):
        snapshot = current(request)
        editable(snapshot)
        address = next((a for a in await provider.addresses() if a.id == payload.address_id), None)
        if address is None:
            raise MacroError("Selecione um endereço da lista atual.", 422)
        def update(s):
            s.address, s.selected, s.summary, s.recommendations = address, None, None, []
        return mutate(snapshot, update)

    @app.put("/api/profile", response_model=Session)
    def profile(payload: UserProfile, request: Request):
        snapshot = current(request)
        if payload.id != snapshot.id:
            raise MacroError("Perfil não pertence à sessão.", 403)
        def update(s):
            s.profile = payload
        return mutate(snapshot, update)

    @app.post("/api/search", response_model=Session)
    async def search(payload: MealRequest, request: Request):
        snapshot = current(request)
        editable(snapshot)
        if snapshot.address is None:
            raise MacroError("Selecione o endereço antes de buscar.", 422)
        query, budget = search_terms(payload)
        if budget is None:
            budget = snapshot.profile.default_budget_cents
        candidates = await provider.search(query, snapshot.address, budget)
        recommendations = rank(candidates, payload, snapshot.profile, budget)
        def update(s):
            s.budget_cents = budget
            s.recommendations, s.selected, s.summary = recommendations, None, None
            message = ("Encontrei estas opções. Escolha um prato para ver os complementos." if recommendations else
                       "Não encontrei opções com esses filtros. Ajuste o orçamento ou suas preferências e busque novamente.")
            s.messages = (s.messages + [Message(role="user", text=payload.text), Message(role="assistant", text=message)])[-40:]
        return mutate(snapshot, update)

    @app.get("/api/items/{merchant_id}/{item_id}")
    async def item(merchant_id: str, item_id: str, request: Request):
        snapshot = current(request)
        if not snapshot.address or not any((r.candidate.merchant_id, r.candidate.item_id) == (merchant_id, item_id)
                                           for r in snapshot.recommendations):
            raise MacroError("Escolha um item da busca atual.", 422)
        return await provider.item(merchant_id, item_id, snapshot.address)

    @app.put("/api/selection", response_model=Session)
    async def selection(payload: SelectionInput, request: Request):
        snapshot = current(request)
        editable(snapshot)
        if not snapshot.address or not any((r.candidate.merchant_id, r.candidate.item_id) == (payload.merchant_id, payload.item_id)
                                           for r in snapshot.recommendations):
            raise MacroError("Escolha um item da busca atual.", 422)
        candidate = await provider.item(payload.merchant_id, payload.item_id, snapshot.address)
        selected = select(candidate, payload)
        def update(s):
            s.selected, s.summary = selected, None
        return mutate(snapshot, update)

    @app.get("/api/checkout/choices")
    def choices(request: Request):
        current(request)
        mock_only()
        return provider.checkout_choices()

    @app.post("/api/checkout/review", response_model=Session)
    def review(payload: CheckoutInput, request: Request):
        mock_only()
        snapshot = current(request)
        editable(snapshot)
        if not snapshot.selected or not snapshot.address:
            raise MacroError("Selecione prato, complementos e endereço antes de revisar.", 422)
        choices = provider.checkout_choices()
        delivery = next((d for d in choices["delivery"] if d.id == payload.delivery_id), None)
        payment = next((p for p in choices["payment"] if p.id == payload.payment_id), None)
        if not delivery or not payment:
            raise MacroError("Entrega ou pagamento não pertence às opções disponíveis.", 422)
        def update(s):
            subtotal = s.selected.unit_total_cents * s.selected.quantity
            s.summary = CheckoutSummary(cart_id=s.summary.cart_id if s.summary else f"demo-cart-{uuid4()}",
                                        items=[s.selected], address=s.address, delivery=delivery, payment=payment,
                                        subtotal_cents=subtotal, total_cents=subtotal + delivery.fee_cents,
                                        version=str(uuid4()), simulated=True)
        return mutate(snapshot, update)

    @app.post("/api/checkout/confirm", response_model=Session)
    def confirm(payload: ConfirmationInput, request: Request):
        mock_only()
        # No external calls here: this is an atomic simulation, never a real submission.
        with app.state.db.transaction() as connection:
            s = app.state.db.get(request.cookies.get("macro_session", ""), connection)
            if not s or s.mode != "mock":
                raise MacroError("Sessão inválida. Recarregue a página.", 401)
            if not s.summary or payload.version != s.summary.version:
                raise MacroError("O resumo mudou. Revise o pedido e confirme a nova versão.")
            if not s.order:
                s.order = OrderRecord(id=f"demo-order-{uuid4()}", cart_id=s.summary.cart_id, status="submitted", simulated=True)
                app.state.db.save(s, connection)
            return s

    return app


app = create_app()
