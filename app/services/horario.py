"""Hora local do usuário, dita ao modelo para ele raciocinar sobre o que costuma estar aberto."""

from datetime import datetime
from zoneinfo import ZoneInfo

from app.core.config import Settings

DIAS = [
    "segunda-feira",
    "terça-feira",
    "quarta-feira",
    "quinta-feira",
    "sexta-feira",
    "sábado",
    "domingo",
]


def periodo(hora: int) -> str:
    """Faixa do dia, pensando em delivery: o que muda é o que costuma estar aberto."""
    if hora < 5:
        return "madrugada"
    if hora < 11:
        return "manhã"
    if hora < 15:
        return "horário de almoço"
    if hora < 18:
        return "tarde"
    if hora < 23:
        return "noite (jantar)"
    return "fim da noite"


def agora(settings: Settings, momento: datetime | None = None) -> dict:
    """{"data": "2026-10-18", "hora": "23:40", "dia_da_semana": "domingo", "periodo": "fim da noite"}"""
    local = (momento or datetime.now(ZoneInfo(settings.timezone))).astimezone(
        ZoneInfo(settings.timezone)
    )
    return {
        "data": local.strftime("%Y-%m-%d"),
        "hora": local.strftime("%H:%M"),
        "dia_da_semana": DIAS[local.weekday()],
        "periodo": periodo(local.hour),
    }
