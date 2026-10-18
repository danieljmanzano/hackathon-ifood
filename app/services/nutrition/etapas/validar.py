"""Validação e confiança: regras (Atwater, limites) + dispersão e divergência entre fontes."""

from dataclasses import dataclass, field

from ..modelos import Fundido

KCAL_MIN, KCAL_MAX = 20, 3500
BASE_POR_METODO = {"web": 0.85, "database": 0.7, "consensus": 0.7, "estimated": 0.55}
ALTA, MEDIA = 0.75, 0.5


@dataclass
class Validacao:
    score: float
    confianca: str  # low | medium | high
    motivos: list[str] = field(default_factory=list)
    revisar: bool = False


def validar(fundido: Fundido, gramas: float | None, limiar: float) -> Validacao:
    """Confiança 0..1 a partir do método e dos sinais de incerteza. `revisar` = abaixo do limiar."""
    score = BASE_POR_METODO[fundido.method]
    motivos: list[str] = []
    macros = fundido.macros

    if not KCAL_MIN <= macros.kcal <= KCAL_MAX:
        score -= 0.4
        motivos.append(f"Calorias fora do plausível ({macros.kcal:.0f} kcal).")

    if fundido.dispersao is not None:
        if fundido.dispersao > 0.5:
            score -= 0.25
            motivos.append(
                f"Estimativas muito diferentes entre si (dispersão {fundido.dispersao:.0%})."
            )
        elif fundido.dispersao > 0.25:
            score -= 0.12
            motivos.append(f"Estimativas divergem entre si (dispersão {fundido.dispersao:.0%}).")
    elif fundido.estimativa is not None and len(fundido.fontes) == 1:
        score -= 0.05
        motivos.append("Apenas uma fonte de estimativa.")

    if fundido.divergencia is not None:
        if fundido.divergencia > 0.5:
            score -= 0.25
            motivos.append(f"Fonte e estimativa divergem {fundido.divergencia:.0%}.")
        elif fundido.divergencia > 0.25:
            score -= 0.12
            motivos.append(f"Fonte e estimativa divergem {fundido.divergencia:.0%}.")

    if macros.completo():
        esperado = 4 * macros.proteina_g + 4 * macros.carbo_g + 9 * macros.gordura_g
        diferenca = abs(esperado - macros.kcal) / macros.kcal if macros.kcal else 1
        if diferenca > 0.25:
            score -= 0.2
            motivos.append(
                f"Macros não fecham com as calorias (Atwater: {esperado:.0f} vs {macros.kcal:.0f} kcal)."
            )
        elif diferenca > 0.15:
            score -= 0.1
            motivos.append(
                f"Macros fecham mal com as calorias (Atwater: {esperado:.0f} vs {macros.kcal:.0f} kcal)."
            )
        if gramas and macros.proteina_g + macros.carbo_g + macros.gordura_g > gramas * 1.05:
            score -= 0.2
            motivos.append("Soma dos macros excede o peso do prato.")

    if gramas is None:
        score -= 0.05
        motivos.append("Peso do prato desconhecido.")

    score = max(0.0, min(1.0, score))
    confianca = "high" if score >= ALTA else "medium" if score >= MEDIA else "low"
    return Validacao(score, confianca, motivos, revisar=score < limiar)
