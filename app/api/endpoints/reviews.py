"""Histórico de avaliações e preferências aprendidas."""

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, Request

from app.api.deps import current_session, get_provider, offered
from app.core.exceptions import MacroError
from app.schemas.macro import (
    Session,
    now,
)
from app.schemas.reviews import Review, ReviewInput, UserTastes
from app.services.mock_ifood import MockIFood
from app.services.review_recommendations import review_context

router = APIRouter()


@router.get("/reviews/me", response_model=list[Review])
def my_reviews(request: Request, session: Session = Depends(current_session)):
    return review_context(
        request.app.state.db, session.profile.id, session.mode == "mock", session.profile
    ).history


@router.get("/profile/tastes", response_model=UserTastes)
def my_tastes(request: Request, session: Session = Depends(current_session)):
    return review_context(
        request.app.state.db, session.profile.id, session.mode == "mock", session.profile
    ).tastes


@router.put("/reviews", response_model=Review)
async def save_review(
    payload: ReviewInput,
    request: Request,
    session: Session = Depends(current_session),
    provider: MockIFood = Depends(get_provider),
):
    # Apenas itens conhecidos pela sessão podem receber avaliações. Não implica compra verificada.
    selected = session.selected
    history = review_context(
        request.app.state.db, session.profile.id, session.mode == "mock"
    ).history
    previously_reviewed = any(
        (r.merchant_id, r.item_id) == (payload.merchant_id, payload.item_id) for r in history
    )
    if (
        not previously_reviewed
        and not offered(session, payload.merchant_id, payload.item_id)
        and not (
            selected
            and (selected.candidate.merchant_id, selected.candidate.item_id)
            == (payload.merchant_id, payload.item_id)
        )
    ):
        raise MacroError("Escolha um item da busca ou do cardápio para avaliar.", 422)
    if session.address is None:
        raise MacroError("Selecione um endereço antes de avaliar.", 422)
    candidate = await provider.item(payload.merchant_id, payload.item_id, session.address)
    review = Review(
        **payload.model_dump(),
        id=str(uuid4()),
        user_id=session.profile.id,
        created_at=now(),
        simulated=session.mode == "mock",
        merchant_name=candidate.merchant_name,
        item_name=candidate.name,
    )
    request.app.state.db.save_review(review)
    review_context(
        request.app.state.db, session.profile.id, session.mode == "mock", session.profile
    )
    return review
