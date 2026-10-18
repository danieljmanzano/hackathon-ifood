"""Pesquisa na web para entender o que o usuário pediu (marca, produto de mercado, nome regional).

Devolve consultas para o buscador do iFood; nunca decide nada sozinho: quem usa é busca_agente.buscar.
Falha, demora ou resposta fora do formato viram None e a busca segue com o que já tinha.
"""

import asyncio
import logging
import re
import time

from jsonschema import ValidationError as SchemaError
from jsonschema import validate

from app.core import logs
from app.core.config import Settings
from app.core.exceptions import AppError
from app.core.search_logs import elapsed_ms, event
from app.services.gemini import search_web
from app.services.nutrition.entrada import extrair_json
from app.services.openai_client import responder
from app.services.review_processing import normalized
from app.skills import busca_identificar

CONSULTA_VALIDA = re.compile(r"^[\w\s\-]{2,60}$")
MAX_CONSULTAS = 3


def possivel(settings: Settings) -> bool:
    return settings.busca_web_identificar and bool(settings.web_api_key)


async def _pesquisar(settings: Settings, prompt: str) -> str:
    if settings.nutrition_provider == "openai":
        texto, _ = await responder(
            prompt,
            instrucoes=busca_identificar.INSTRUCAO_CURTA_OPENAI,
            web=True,
            schema=busca_identificar.SCHEMA,
            settings=settings,
            log_content=settings.busca_log_conteudo,
        )
    else:
        texto, _ = await search_web(prompt, settings=settings)
    return texto


async def identificar(
    settings: Settings, termo: str, agora: dict | None, prazo: float
) -> list[str] | None:
    """Consultas novas para o iFood a partir do que a web diz sobre `termo`; None se não sugeriu nenhuma ou falhou."""
    termo = termo.strip()
    if not termo or prazo < 3:
        return None
    started = time.perf_counter()
    try:
        texto = await asyncio.wait_for(
            _pesquisar(settings, busca_identificar.pedido(termo, agora)), prazo
        )
        dados = extrair_json(texto)
        validate(dados, busca_identificar.SCHEMA)
    except (asyncio.TimeoutError, AppError, ValueError, SchemaError) as e:
        event(
            "search.web_lookup_failed",
            level=logging.WARNING,
            error_type=type(e).__name__,
            duration_ms=elapsed_ms(started),
        )
        return None
    consultas = list(
        dict.fromkeys(q.strip() for q in dados["consultas"] if CONSULTA_VALIDA.match(q.strip()))
    )
    consultas = consultas[:MAX_CONSULTAS]
    event(
        "search.web_lookup",
        understood=dados["entendi"],
        query_count=len(consultas),
        duration_ms=elapsed_ms(started),
    )
    if settings.busca_log_conteudo:
        logs.info(
            "busca web",
            f"“{termo}” → {'entendi' if dados['entendi'] else 'não entendi'}: "
            f"{logs.curto(dados['o_que_e'], 120)} · consultas {consultas}",
        )
    return (
        consultas or None
    )  # mesmo sem certeza, as variações de grafia/sabor ampliam a busca sem custo


def sem_repetir(novas: list[str], ja_tentadas: set[str]) -> list[str]:
    return [q for q in novas if normalized(q) not in ja_tentadas]
