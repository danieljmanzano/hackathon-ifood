"""Dependências compartilhadas e atualização atômica das sessões da API."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Annotated

from fastapi import Depends, Request

from app.core.config import Settings, get_settings
from app.core.exceptions import MacroError
from app.schemas.macro import Session
from app.services.mock_ifood import MockIFood

if TYPE_CHECKING:
    from app.services.ifood_live import MCPIFood

SettingsDep = Annotated[Settings, Depends(get_settings)]
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


def mutate_session(
    request: Request, snapshot: Session, operation: Callable[[Session], None]
) -> Session:
    db = request.app.state.db
    with db.transaction() as connection:
        session = db.get(snapshot.id, connection)
        if session != snapshot:
            raise MacroError("A sessão mudou em outra aba. Atualize antes de continuar.")
        operation(session)
        db.save(session, connection)
        return session
