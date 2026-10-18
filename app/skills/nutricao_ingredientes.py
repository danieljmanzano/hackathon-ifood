"""Skills: decompor o prato em ingredientes e casá-los com os alimentos da tabela TACO.

Quem usa: etapas/estimar.py -> decompor_ingredientes (só se nenhuma estimativa trouxe a lista)
          etapas/ingredientes.py -> casar_ingredientes (uma chamada em lote para todos os ingredientes).
Modelo:   LLM de texto (OpenRouter ou OpenAI, com a reserva do outro).
Saída:    DECOMPOR -> lista de ingredientes com gramas; CASAR -> para cada ingrediente, o índice do candidato ou null.
"""

from . import item_pedido
from .comum import SCHEMA_INGREDIENTES, pedir_json

INSTRUCOES_DECOMPOR = """Você decompõe um prato de delivery em ingredientes com a massa de cada um em gramas, na forma
como seriam consumidos (cozidos, grelhados etc.). Use nomes genéricos de alimentos em português, como numa tabela de
composição de alimentos (ex.: "arroz branco cozido", "peito de frango grelhado"). Inclua as opções escolhidas.
Se o peso total do prato for informado, as massas devem somar aproximadamente esse peso."""

SCHEMA_DECOMPOR = {
    "type": "object",
    "properties": {
        "ingredientes": SCHEMA_INGREDIENTES,
    },
    "required": ["ingredientes"],
}

INSTRUCOES_CASAR = """Você casa ingredientes com alimentos de uma tabela de composição (TACO). Para cada ingrediente
há uma lista de candidatos numerados. Escolha o candidato que representa o mesmo alimento no mesmo preparo, ou null se
nenhum serve. Nunca escolha um alimento de outra categoria só por parecer."""

SCHEMA_CASAR = {
    "type": "object",
    "properties": {
        "escolhas": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "ingrediente": {"type": "string"},
                    "escolha": {"type": ["integer", "null"]},
                },
                "required": ["ingrediente", "escolha"],
            },
        }
    },
    "required": ["escolhas"],
}

PEDIDO_DECOMPOR = "Decomponha este item.\n\n"
INGREDIENTE = "Ingrediente: "


def pedido_decompor(item: str) -> str:
    """O formato JSON é acrescentado por `perguntar_json` (veja `comum.pedir_json`)."""
    return f"{PEDIDO_DECOMPOR}{item}"


def pedido_casar(candidatos_por_ingrediente: dict[str, list[tuple[str, str]]]) -> str:
    """Um bloco por ingrediente com seus candidatos numerados (nome, categoria da TACO)."""
    blocos = []
    for nome, lista in candidatos_por_ingrediente.items():
        linhas = "\n".join(
            f"  {i}: {alimento} ({categoria})" for i, (alimento, categoria) in enumerate(lista)
        )
        blocos.append(f"{INGREDIENTE}{nome}\n{linhas}")
    return "\n\n".join(blocos)


def exemplo() -> list[tuple[str, str]]:
    item = item_pedido.exemplo()[1][1]
    candidatos = {
        "arroz": [
            ("Arroz, tipo 1, cozido", "Cereais e derivados"),
            ("Arroz, integral, cozido", "Cereais e derivados"),
        ],
        "feijão": [("Feijão, carioca, cozido", "Leguminosas e derivados")],
    }
    return [
        ("decompor - sistema", INSTRUCOES_DECOMPOR),
        ("decompor - usuário", pedir_json(pedido_decompor(item), SCHEMA_DECOMPOR)),
        ("casar - sistema", INSTRUCOES_CASAR),
        ("casar - usuário", pedir_json(pedido_casar(candidatos), SCHEMA_CASAR)),
    ]
