"""Ingredientes do prato casados com a TACO e somados (casar_tbca + somar_ingredientes)."""
from app.core.config import Settings
from ..modelos import Ingrediente, Leitura, Macros
from ..prompts import INSTRUCOES_CASAR, SCHEMA_CASAR
from .bases import Alimento, candidatos
from .llm import perguntar_json

COBERTURA_MINIMA = 0.7


async def casar_ingredientes(settings: Settings, ingredientes: list[Ingrediente],
                             alimentos: tuple[Alimento, ...]) -> dict[str, Alimento | None]:
    """Uma chamada em lote: o LLM escolhe, por ingrediente, o alimento da TACO (ou nenhum)."""
    opcoes = {i.nome: candidatos(alimentos, i.nome, n=5) for i in ingredientes}
    com_candidatos = {nome: lista for nome, lista in opcoes.items() if lista}
    casados: dict[str, Alimento | None] = {i.nome: None for i in ingredientes}
    if not com_candidatos:
        return casados
    blocos = []
    for nome, lista in com_candidatos.items():
        linhas = "\n".join(f"  {i}: {a.nome} ({a.categoria})" for i, a in enumerate(lista))
        blocos.append(f"Ingrediente: {nome}\n{linhas}")
    dados = await perguntar_json(settings, INSTRUCOES_CASAR, "\n\n".join(blocos), SCHEMA_CASAR)
    for item in dados["escolhas"]:
        lista = com_candidatos.get(item["ingrediente"])
        indice = item["escolha"]
        if lista and indice is not None and 0 <= indice < len(lista):
            casados[item["ingrediente"]] = lista[indice]
    return casados


def somar_ingredientes(ingredientes: list[Ingrediente], casados: dict[str, Alimento | None]) -> Leitura | None:
    """TACO × gramas de cada ingrediente. Exige cobertura mínima (por massa) para valer como fonte."""
    total_g = sum(i.gramas for i in ingredientes)
    achados = [(i, casados.get(i.nome)) for i in ingredientes if casados.get(i.nome) is not None]
    gramas_casadas = sum(i.gramas for i, _ in achados)
    if total_g <= 0 or gramas_casadas / total_g < COBERTURA_MINIMA:
        return None
    cobertura = gramas_casadas / total_g

    def soma(campo: str) -> float | None:
        valores = [getattr(a.macros, campo) for _, a in achados]
        if any(v is None for v in valores):
            return None
        return sum(v * i.gramas / 100 for (i, _), v in zip(achados, valores)) / cobertura

    kcal = sum(a.macros.kcal * i.gramas / 100 for i, a in achados) / cobertura
    folga = 0.2 + 0.3 * (1 - cobertura)
    nomes = ", ".join(f"{i.nome}→{a.nome}" for i, a in achados)
    return Leitura(
        fonte="taco", macros=Macros(kcal, soma("proteina_g"), soma("carbo_g"), soma("gordura_g")),
        faixa_min=kcal * (1 - folga), faixa_max=kcal * (1 + folga), confianca=0.4 + 0.3 * cobertura,
        porcao_base="soma dos ingredientes", peso_g=total_g,
        suposicoes=[f"Soma pela TACO cobrindo {cobertura:.0%} da massa: {nomes}."],
        justificativa="Ingredientes estimados e somados com a Tabela TACO.",
    )
