"""Logs de busca/recomendação com correlação por chamada, sem identidade ou texto do usuário."""
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
import json
import logging
import time
from uuid import uuid4

from app.core.logs import NIVEIS

log = logging.getLogger('app.busca')
_search_id: ContextVar[str | None] = ContextVar('search_id', default=None)


def configurar_busca_logs(nivel: str = 'resumo') -> None:
    # Nível próprio: desligar logs de calorias não deve esconder os de busca.
    log.setLevel(NIVEIS[nivel])


def event(name: str, *, level: int = logging.INFO, **fields) -> None:
    if not log.isEnabledFor(level):
        return
    search_id = _search_id.get()
    log.log(level, '%s %s', name, json.dumps(fields, ensure_ascii=False, sort_keys=True), extra={
        'event': name, 'search_id': search_id, 'fields': fields,
        'etapa': name.split('.')[0], 'item': f'busca {search_id}' if search_id else 'busca',
    })


def elapsed_ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000, 2)


@dataclass
class SearchTrace:
    id: str
    result_count: int = 0
    stage: str = 'validation'


@contextmanager
def trace_search(mode: str):
    trace = SearchTrace(uuid4().hex[:12])
    token = _search_id.set(trace.id)
    start = time.perf_counter()
    event('search.started', mode=mode)
    try:
        yield trace
    except BaseException as exc:
        status = getattr(exc, 'status', getattr(exc, 'status_code', None))
        event('search.failed', level=logging.WARNING, error_type=type(exc).__name__,
              status_code=status, stage=trace.stage, duration_ms=elapsed_ms(start))
        raise
    else:
        event('search.completed', result_count=trace.result_count, duration_ms=elapsed_ms(start))
    finally:
        _search_id.reset(token)
