"""Junções: consenso entre estimativas e fusão com a fonte online."""
from statistics import median

from ..modelos import Estimativa, Fundido, InfoOnline, Leitura, Macros

FAIXA_WEB = 0.10
FAIXA_BASE = 0.25


def _mediana(valores: list[float | None]) -> float | None:
    validos = [v for v in valores if v is not None]
    return median(validos) if validos else None


def consenso(leituras: list[Leitura]) -> Estimativa | None:
    """Mediana das leituras (kcal e macros) e dispersão entre elas. Aceita qualquer subconjunto de fontes."""
    if not leituras:
        return None
    kcals = [l.macros.kcal for l in leituras]
    mediana_kcal = median(kcals)
    dispersao = (max(kcals) - min(kcals)) / mediana_kcal if len(leituras) > 1 and mediana_kcal else None
    macros = Macros(
        mediana_kcal,
        _mediana([l.macros.proteina_g for l in leituras]),
        _mediana([l.macros.carbo_g for l in leituras]),
        _mediana([l.macros.gordura_g for l in leituras]),
    )
    suposicoes = list(dict.fromkeys(s for l in leituras for s in l.suposicoes))
    principal = next((l for l in leituras if l.porcao_base), leituras[0])
    return Estimativa(
        macros=macros,
        faixa_min=min(min(l.faixa_min for l in leituras), mediana_kcal),
        faixa_max=max(max(l.faixa_max for l in leituras), mediana_kcal),
        dispersao=dispersao,
        fontes=[l.fonte for l in leituras],
        peso_g=_mediana([l.peso_g for l in leituras]),
        porcao_base=principal.porcao_base,
        suposicoes=suposicoes,
        justificativa=principal.justificativa,
        confianca_modelos=sum(l.confianca for l in leituras) / len(leituras),
    )


def fundir(info: InfoOnline | None, info_macros: Macros | None, estimativa: Estimativa | None) -> Fundido | None:
    """info_online vence a estimativa; guarda a divergência entre as duas (diferença relativa de kcal)."""
    if info is not None and info_macros is not None:
        if info.faixa:
            faixa_min, faixa_max = info.faixa
        else:
            folga = FAIXA_WEB if info.method == "web" else FAIXA_BASE
            faixa_min, faixa_max = info_macros.kcal * (1 - folga), info_macros.kcal * (1 + folga)
        divergencia = None
        if estimativa and estimativa.macros.kcal:
            divergencia = abs(info_macros.kcal - estimativa.macros.kcal) / estimativa.macros.kcal
        return Fundido(
            macros=info_macros, faixa_min=min(faixa_min, info_macros.kcal), faixa_max=max(faixa_max, info_macros.kcal),
            method=info.method, porcao_base=info.porcao_base, divergencia=divergencia,
            dispersao=estimativa.dispersao if estimativa else None,
            fontes=[info.fonte_nome, *(estimativa.fontes if estimativa else [])], info=info, estimativa=estimativa,
        )
    if estimativa is not None:
        return Fundido(
            macros=estimativa.macros, faixa_min=estimativa.faixa_min, faixa_max=estimativa.faixa_max,
            method="consensus" if len(estimativa.fontes) > 1 else "estimated", porcao_base=estimativa.porcao_base,
            divergencia=None, dispersao=estimativa.dispersao, fontes=estimativa.fontes, info=None,
            estimativa=estimativa,
        )
    return None
