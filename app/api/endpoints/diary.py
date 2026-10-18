"""Consumo registrado e contexto alimentar diário."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import Field

from app.api.deps import current_session
from app.core.config import Settings, get_settings
from app.core.exceptions import MacroError
from app.schemas.macro import (
    ConsumptionRecord,
    DailyFoodDiary,
    FoodDiaryEntry,
    Session,
    now,
)
from app.services.diet_context import build_diet_context, local_date

router = APIRouter()


@router.get("/consumption", response_model=list[ConsumptionRecord])
def consumption(request: Request, session: Session = Depends(current_session)):
    return request.app.state.db.consumption(session.profile.id)


@router.put("/consumption", response_model=list[ConsumptionRecord])
def save_consumption(
    payload: Annotated[list[ConsumptionRecord], Field(max_length=500)],
    request: Request,
    session: Session = Depends(current_session),
):
    keys = {(e.order_id, e.item_id) for e in payload}
    if len(keys) != len(payload):
        raise MacroError("Há registros duplicados para o mesmo prato e pedido.", 422)
    if any(e.consumed_at > now() + timedelta(minutes=5) for e in payload):
        raise MacroError("O consumo precisa ter ocorrido antes de agora.", 422)
    request.app.state.db.replace_consumption(session.profile.id, payload)
    return payload


@router.get("/daily-context", response_model=DailyFoodDiary)
def daily_context(
    request: Request,
    on_date: date | None = None,
    session: Session = Depends(current_session),
    settings: Settings = Depends(get_settings),
):
    entries = request.app.state.db.food_entries(session.profile.id)
    context, _ = build_diet_context(
        session.profile,
        entries,
        request.app.state.db.consumption(session.profile.id),
        settings.timezone,
        on_date=on_date,
    )
    return DailyFoodDiary(
        entries=sorted(
            [e for e in entries if local_date(e.consumed_at, settings.timezone) == context.date],
            key=lambda e: e.consumed_at,
        ),
        context=context,
    )


@router.post("/food-diary", response_model=FoodDiaryEntry)
def add_food(
    payload: FoodDiaryEntry, request: Request, session: Session = Depends(current_session)
):
    if payload.consumed_at > now() + timedelta(minutes=5):
        raise MacroError("Registre apenas alimentos já consumidos.", 422)
    entries = request.app.state.db.food_entries(session.profile.id)
    if len(entries) >= 500 and not any(e.id == payload.id for e in entries):
        raise MacroError(
            "O diário chegou ao limite de 500 registros. Remova registros antigos para continuar.",
            422,
        )
    request.app.state.db.save_food_entry(session.profile.id, payload)
    return payload


@router.delete("/food-diary/{entry_id}", status_code=204)
def remove_food(entry_id: str, request: Request, session: Session = Depends(current_session)):
    request.app.state.db.delete_food_entry(session.profile.id, entry_id)
