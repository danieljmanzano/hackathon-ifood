"""Revisão, confirmação e avaliação de pedidos."""

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, Request

from app.api.deps import current_session, editable, get_provider, mutate_session
from app.core.config import Settings, get_settings
from app.core.exceptions import MacroError
from app.schemas.macro import (
    CheckoutInput,
    CheckoutSummary,
    ConfirmationInput,
    Message,
    OrderRecord,
    OrderReview,
    OrderReviewEdit,
    OrderReviewInput,
    Session,
)
from app.services.mock_ifood import MockIFood
from app.services.review_interpretation import (
    llm_available,
    schedule_interpretation,
    sync_taste_review,
)

router = APIRouter()


@router.get("/checkout/choices")
def choices(
    session: Session = Depends(current_session),
    provider: MockIFood = Depends(get_provider),
    settings: Settings = Depends(get_settings),
):
    if not provider.simulated or settings.ifood_mode != "mock":
        raise MacroError(
            "Checkout real bloqueado até validar ferramentas e ambiente de teste.", 403
        )
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
        raise MacroError(
            "Checkout real bloqueado até validar ferramentas e ambiente de teste.", 403
        )
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
        total = f"R$ {s.summary.total_cents / 100:.2f}".replace(".", ",")
        s.messages = (
            s.messages
            + [
                Message(
                    role="user", text=f"Entrega: {delivery.label}. Pagamento: {payment.label}."
                ),
                Message(
                    role="assistant",
                    text=f"Confira os itens e o total de {total}. O pedido ainda não foi confirmado.",
                ),
            ]
        )[-40:]

    return mutate_session(request, session, update)


@router.post("/checkout/confirm", response_model=Session)
async def confirm(
    payload: ConfirmationInput,
    request: Request,
    settings: Settings = Depends(get_settings),
):
    if settings.ifood_mode != "mock":
        raise MacroError(
            "Checkout real bloqueado até validar ferramentas e ambiente de teste.", 403
        )
    db = request.app.state.db
    with db.transaction() as connection:
        s = db.get(request.cookies.get("macro_session", ""), connection)
        if not s or s.mode != "mock":
            raise MacroError("Sessão inválida. Recarregue a página.", 401)
        if not s.summary or payload.version != s.summary.version:
            raise MacroError("O resumo mudou. Revise o pedido e confirme a nova versão.")
        created = not s.order
        if created:
            given = payload.review if payload.review and not payload.review.empty else None
            s.order = OrderRecord(
                id=f"demo-order-{uuid4()}",
                cart_id=s.summary.cart_id,
                status="submitted",
                simulated=True,
                review=given
                and OrderReview(
                    rating=given.rating,
                    comment=given.comment,
                    # Só há o que interpretar quando o usuário escreveu algo.
                    interpretation_state="pending"
                    if given.comment and llm_available(settings)
                    else "none",
                ),
            )
            s.messages = (
                s.messages
                + [
                    Message(role="user", text="Confirmar pedido."),
                    Message(
                        role="assistant",
                        text="Pedido de demonstração confirmado. Nenhuma cobrança foi realizada. Você pode avaliar sua experiência aqui na conversa.",
                    ),
                ]
            )[-40:]
            db.save(s, connection)
    # Fora da transação: save_review abre a sua. Só a primeira confirmação grava a avaliação.
    if created and s.order.review:
        # A nota escolhida já vale; a interpretação completa aspectos (e a nota, se faltou) depois.
        sync_taste_review(db, s)
        if s.order.review.interpretation_state == "pending":
            schedule_interpretation(db, s.id, settings)
    return s


@router.get("/checkout/order", response_model=Session)
def order_status(session: Session = Depends(current_session)):
    """Consulta leve para acompanhar a interpretação em segundo plano."""
    return session


@router.put("/checkout/order/review", response_model=Session)
def edit_order_review(
    payload: OrderReviewEdit,
    request: Request,
    session: Session = Depends(current_session),
):
    if not session.order or not session.order.review:
        raise MacroError("Não há avaliação neste pedido para ajustar.", 422)
    if session.order.review.interpretation_state == "pending":
        raise MacroError(
            "Ainda estamos interpretando sua avaliação. Tente de novo em instantes.", 409
        )

    def update(s: Session):
        s.order.review = s.order.review.model_copy(
            update={"rating": payload.rating, "aspects": payload.aspects}
        )

    updated = mutate_session(request, session, update)
    sync_taste_review(request.app.state.db, updated)
    return updated


@router.post("/checkout/order/review", response_model=Session)
async def add_order_review(
    payload: OrderReviewInput,
    request: Request,
    session: Session = Depends(current_session),
    settings: Settings = Depends(get_settings),
):
    if not session.order or session.order.status != "submitted":
        raise MacroError("Confirme o pedido antes de avaliá-lo.", 422)
    if payload.empty:
        raise MacroError("Informe uma nota ou um comentário para avaliar.", 422)
    if session.order.review and session.order.review.interpretation_state == "pending":
        raise MacroError("Sua avaliação ainda está sendo interpretada.", 409)

    def update(s: Session):
        s.order.review = OrderReview(
            rating=payload.rating,
            comment=payload.comment,
            interpretation_state="pending"
            if payload.comment and llm_available(settings)
            else "none",
        )
        text = payload.comment or f"Nota do pedido: {payload.rating}/5."
        s.messages = (
            s.messages
            + [
                Message(role="user", text=text),
                Message(
                    role="assistant",
                    text="Avaliação salva. Ela será considerada nas próximas sugestões.",
                ),
            ]
        )[-40:]

    updated = mutate_session(request, session, update)
    sync_taste_review(request.app.state.db, updated)
    if updated.order.review.interpretation_state == "pending":
        schedule_interpretation(request.app.state.db, updated.id, settings)
    return updated
