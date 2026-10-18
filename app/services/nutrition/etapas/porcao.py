"""Trilha das gramas: extrair_porcao, converter_em_gramas e calcular_porcao."""

import re

from app.schemas.macro import MealCandidate

from ..modelos import InfoOnline, Macros, Porcao

_MASSA = re.compile(
    r"(?<![\w.,])(\d+(?:[.,]\d+)?)\s*(kg|quilos?|gramas?|gr|g|litros?|ml|l)(?![a-zà-ú])", re.I
)
_SERVE = re.compile(
    r"serv(?:e|es|em|ir)\s+(?:até\s+|ate\s+)?(\d+)(?:\s*(?:-|–|a|ou|to)\s*(\d+))?", re.I
)
_CM = re.compile(r"(?<![\w.,])(\d+(?:[.,]\d+)?)\s*cm(?![a-zà-ú])", re.I)

_FATOR_G = {"kg": 1000, "quilo": 1000, "quilos": 1000, "l": 1000, "litro": 1000, "litros": 1000}


def _num(texto: str) -> float:
    return float(texto.replace(",", "."))


def extrair_porcao(candidate: MealCandidate, opcoes: list[str] | None = None) -> Porcao:
    """Peso (g/kg/ml/l), tamanho (cm) e "serve N" declarados no nome e na descrição do item.

    Usa a primeira gramatura encontrada. Os adicionais (opções) não entram: eles mudam os macros, não a porção base.
    Líquidos contam 1 ml = 1 g.
    """
    texto = f"{candidate.name}. {candidate.description}"
    porcao = Porcao()

    massa = _MASSA.search(texto)
    if massa:
        valor = _num(massa.group(1)) * _FATOR_G.get(massa.group(2).lower(), 1)
        if 0 < valor <= 10_000:
            porcao.gramas = valor
            porcao.trecho = massa.group(0)

    serve = _SERVE.search(texto)
    if serve:
        porcao.pessoas_min = int(serve.group(1))
        porcao.pessoas_max = int(serve.group(2)) if serve.group(2) else porcao.pessoas_min

    cm = _CM.search(texto)
    if cm:
        porcao.tamanho_cm = _num(cm.group(1))
    return porcao


def converter_em_gramas(
    declarada: Porcao, estimado_g: float | None
) -> tuple[float | None, str, list[str]]:
    """Gramas do item e sua origem: "declarada" > "estimada" (pela imagem/modelo) > "ausente"."""
    avisos: list[str] = []
    if declarada.gramas:
        if estimado_g and abs(estimado_g - declarada.gramas) / declarada.gramas > 0.5:
            avisos.append(
                f"Peso estimado ({estimado_g:.0f} g) difere do declarado ({declarada.gramas:.0f} g); "
                "usado o declarado."
            )
        return declarada.gramas, "declarada", avisos
    if estimado_g and estimado_g > 0:
        return estimado_g, "estimada", avisos
    return None, "ausente", avisos


def calcular_porcao(info: InfoOnline, gramas: float | None) -> Macros | None:
    """Valores da fonte para o item inteiro. Fontes por 100 g exigem as gramas; sem elas devolve None."""
    if info.base == "item":
        return info.macros
    if not gramas:
        return None
    return info.macros.escalar(gramas / 100)
