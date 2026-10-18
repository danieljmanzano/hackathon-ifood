"""Consulta, cadastro e seleção de endereços."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.api.deps import current_session, editable, get_provider, live_only, mutate_session
from app.core.exceptions import MacroError
from app.schemas.macro import (
    Address,
    AddressCreated,
    AddressInput,
    CreateAddressInput,
    GeocodeInput,
    GeocodeResult,
    Session,
)
from app.services.mock_ifood import MockIFood

router = APIRouter()


@router.get("/integration/diagnostic")
async def diagnostic(
    session: Session = Depends(current_session),
    provider: MockIFood = Depends(get_provider),
):
    return await provider.diagnostic()


async def available_addresses(request: Request, session: Session, provider) -> list[Address]:
    """Endereços do iFood; no mock, o fixo de demonstração mais os cadastrados localmente."""
    found = await provider.addresses()
    if provider.simulated:
        found += request.app.state.db.mock_addresses(session.profile.id)
    return found


@router.get("/addresses", response_model=list[Address])
async def addresses(
    request: Request,
    session: Session = Depends(current_session),
    provider: MockIFood = Depends(get_provider),
):
    return await available_addresses(request, session, provider)


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
    """Etapa 2: salva o candidato confirmado (na conta do iFood ou, no mock, localmente) e já o seleciona."""
    editable(session)
    if provider.simulated:
        created = provider.new_address(payload)
        request.app.state.db.save_mock_address(session.profile.id, created)
        found = await available_addresses(request, session, provider)
    else:
        live_only(provider, "create_address")
        before = {a.id for a in await provider.addresses()}
        new_id = await provider.create_address(payload)
        found = await provider.addresses()
        created = next((a for a in found if a.id == new_id), None) or next(
            (a for a in found if a.id not in before), None
        )
        if created is None:
            raise MacroError(
                "Endereço salvo no iFood, mas ainda não apareceu na lista. Recarregue os endereços.",
                502,
            )

    def update(s: Session):
        s.nutrition_search = None
        s.address = created
        s.selected = None
        s.summary = None
        s.recommendations = []

    return AddressCreated(session=mutate_session(request, session, update), addresses=found)


@router.put("/session/address", response_model=Session)
async def set_address(
    payload: AddressInput,
    request: Request,
    session: Session = Depends(current_session),
    provider: MockIFood = Depends(get_provider),
):
    editable(session)
    address = next(
        (
            a
            for a in await available_addresses(request, session, provider)
            if a.id == payload.address_id
        ),
        None,
    )
    if address is None:
        raise MacroError("Selecione um endereço da lista atual.", 422)

    def update(s: Session):
        s.nutrition_search = None
        s.address = address
        s.selected = None
        s.summary = None
        s.recommendations = []

    return mutate_session(request, session, update)
