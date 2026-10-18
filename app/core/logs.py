"""Logs legíveis do pipeline de calorias: uma linha por etapa, com o item no começo.

    14:02:11 · Pizza Margherita   │ bases        │ 8 candidatos na TACO → juiz: nenhum serve
    14:02:19 ! Pizza Margherita   │ web          │ OpenAI 400: Web Search cannot be used...

Nível (CALORIAS_LOG ou python -m app.run --log): off = só problemas · resumo = uma linha por etapa ·
detalhe = também candidatos, respostas dos modelos e cada chamada de API.
"""

import contextvars
import logging
import sys
import time

NIVEIS = {"off": logging.WARNING, "resumo": logging.INFO, "detalhe": logging.DEBUG}
SIMBOLO = {
    logging.DEBUG: ".",
    logging.INFO: "·",
    logging.WARNING: "!",
    logging.ERROR: "x",
    logging.CRITICAL: "x",
}

log = logging.getLogger("app.nutricao")
_item: contextvars.ContextVar[str] = contextvars.ContextVar("nutricao_item", default="")


class Legivel(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        hora = time.strftime("%H:%M:%S", time.localtime(record.created))
        simbolo = SIMBOLO.get(record.levelno, "·")
        etapa = getattr(record, "etapa", None)
        if etapa:
            return f"{hora} {simbolo} {getattr(record, 'item', ''):<{LARGURA_ITEM}.{LARGURA_ITEM}} │ {etapa:<12.12} │ {record.getMessage()}"
        nome = record.name.removeprefix("app.").removeprefix("services.")
        return f"{hora} {simbolo} {record.levelname:<7} {nome}: {record.getMessage()}"


def configurar_logs(nivel: str = "resumo") -> None:
    """Instala o formato legível nos loggers do app (idempotente). Chamado na criação do app."""
    raiz = logging.getLogger("app")
    if not any(isinstance(h.formatter, Legivel) for h in raiz.handlers):
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(Legivel())
        raiz.addHandler(handler)
        raiz.propagate = False
    raiz.setLevel(NIVEIS.get(nivel, logging.INFO))


LARGURA_ITEM = 28


def rotulo(nome: str, largura: int = LARGURA_ITEM) -> str:
    """Nome curto que preserva começo e fim ("Marmita Parm…de frango" x "Marmita Parm…de carne")."""
    if len(nome) <= largura:
        return nome
    fim = largura // 2 - 1
    return nome[: largura - fim - 1] + "…" + nome[-fim:]


def iniciar_item(nome: str) -> contextvars.Token:
    """Marca o item atual: todas as linhas seguintes (inclusive de tasks filhas) levam o nome dele."""
    return _item.set(rotulo(nome))


def curto(valor, limite: int = 180) -> str:
    """Erro ou texto em uma linha só, truncado."""
    texto = " ".join(str(valor if not isinstance(valor, BaseException) else repr(valor)).split())
    return texto if len(texto) <= limite else texto[: limite - 1] + "…"


def _emitir(nivel: int, etapa: str, msg: str) -> None:
    if log.isEnabledFor(nivel):
        log.log(nivel, msg, extra={"etapa": etapa, "item": _item.get()})


def info(etapa: str, msg: str) -> None:
    _emitir(logging.INFO, etapa, msg)


def detalhe(etapa: str, msg: str) -> None:
    _emitir(logging.DEBUG, etapa, msg)


def aviso(etapa: str, msg: str) -> None:
    _emitir(logging.WARNING, etapa, msg)


class Cronometro:
    """with Cronometro() as t: ...; t.segundos"""

    def __enter__(self):
        self._inicio = time.perf_counter()
        return self

    def __exit__(self, *_):
        self.segundos = time.perf_counter() - self._inicio

    @property
    def texto(self) -> str:
        return f"{getattr(self, 'segundos', time.perf_counter() - self._inicio):.1f} s"
