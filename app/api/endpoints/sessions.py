"""Sessões, perfil e início de novos pedidos."""

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, Request, Response

from app.api.deps import current_session, mutate_session
from app.core.config import Settings, get_settings
from app.core.exceptions import MacroError
from app.schemas.macro import (
    Message,
    Session,
    UserProfile,
)
from app.services.review_recommendations import review_context

router = APIRouter()


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


@router.put("/profile", response_model=Session)
def update_profile(
    payload: UserProfile,
    request: Request,
    session: Session = Depends(current_session),
):
    if payload.id != session.id:
        raise MacroError("Perfil não pertence à sessão.", 403)

    def update(s: Session):
        s.nutrition_search = None
        s.profile = payload
        s.pending_preference_update = None

    updated = mutate_session(request, session, update)
    review_context(
        request.app.state.db, updated.profile.id, updated.mode == "mock", updated.profile
    )
    return updated


@router.post("/session/new-order", response_model=Session)
def new_order(request: Request, session: Session = Depends(current_session)):
    if (
        session.order
        and session.order.review
        and session.order.review.interpretation_state == "pending"
    ):
        raise MacroError("Aguarde a interpretação da avaliação antes de iniciar outro pedido.", 409)

    def reset(s: Session):
        s.selected = s.summary = s.order = s.request_intent = None
        s.assembly = None
        s.nutrition_search = None
        s.last_chat_action = None
        s.recommendations = []
        s.menu_merchant_id = None
        s.menu_item_ids = []
        s.messages = (
            s.messages
            + [
                Message(
                    role="assistant",
                    text="Vamos encontrar sua próxima refeição. Seu objetivo e suas preferências continuam salvos.",
                )
            ]
        )[-40:]

    return mutate_session(request, session, reset)
