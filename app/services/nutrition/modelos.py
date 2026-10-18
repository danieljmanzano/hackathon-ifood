"""Tipos internos da pipeline de calorias (o contrato público é NutritionResult)."""
from dataclasses import dataclass, field, replace
from typing import Literal


@dataclass(frozen=True)
class Macros:
    kcal: float
    proteina_g: float | None = None
    carbo_g: float | None = None
    gordura_g: float | None = None

    def escalar(self, fator: float) -> "Macros":
        def f(v):
            return None if v is None else v * fator
        return Macros(self.kcal * fator, f(self.proteina_g), f(self.carbo_g), f(self.gordura_g))

    def completo(self) -> bool:
        return None not in (self.proteina_g, self.carbo_g, self.gordura_g)


@dataclass(frozen=True)
class Ingrediente:
    nome: str
    gramas: float


@dataclass
class Leitura:
    """Estimativa de uma fonte (modelo ou soma de ingredientes), para UMA unidade do item."""
    fonte: str
    macros: Macros
    faixa_min: float
    faixa_max: float
    confianca: float  # 0..1
    porcao_base: str = ""
    peso_g: float | None = None
    ingredientes: list[Ingrediente] = field(default_factory=list)
    suposicoes: list[str] = field(default_factory=list)
    justificativa: str = ""


@dataclass
class InfoOnline:
    """Dado vindo de base de dados ou da web. `base` diz a que os valores se referem."""
    macros: Macros
    base: Literal["item", "100g"]
    porcao_base: str
    fonte_nome: str
    fonte_url: str | None
    evidencia: str
    method: Literal["database", "web"]
    porcao_g: float | None = None
    faixa: tuple[float, float] | None = None  # kcal (mín, máx) informadas pela fonte


@dataclass
class Porcao:
    """O que o texto do item declara sobre tamanho."""
    gramas: float | None = None
    pessoas_min: int | None = None
    pessoas_max: int | None = None
    tamanho_cm: float | None = None
    trecho: str | None = None


@dataclass
class Estimativa:
    """Consenso entre as leituras disponíveis."""
    macros: Macros
    faixa_min: float
    faixa_max: float
    dispersao: float | None
    fontes: list[str]
    peso_g: float | None
    porcao_base: str
    suposicoes: list[str]
    justificativa: str
    confianca_modelos: float


@dataclass
class Fundido:
    macros: Macros
    faixa_min: float
    faixa_max: float
    method: Literal["database", "web", "consensus", "estimated"]
    porcao_base: str
    divergencia: float | None
    dispersao: float | None
    fontes: list[str]
    info: InfoOnline | None
    estimativa: Estimativa | None


def com(obj, **campos):
    return replace(obj, **campos)
