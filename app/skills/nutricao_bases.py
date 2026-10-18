"""Skill: juiz que decide se um alimento da tabela TACO representa o item pedido (com direito a abstenção).

Quem usa: etapas/bases.py -> escolher_alimento. Roda depois da busca por título (rapidfuzz), com até 8 candidatos.
Modelo:   LLM de texto (OpenRouter ou OpenAI, com a reserva do outro).
Saída:    {"escolha": índice do candidato | null, "motivo": ...}. null é o esperado para pratos compostos.
"""
from . import item_pedido
from .comum import pedir_json

INSTRUCOES = """Você decide se um alimento de uma tabela nutricional representa o item pedido.
Escolha um candidato SOMENTE se ele for o mesmo tipo de alimento ou prato, no mesmo preparo (cozido, cru, frito...).
Nunca escolha um alimento parecido de outra categoria. Para pratos compostos (pizza, hambúrguer, lasanha, combos)
que a tabela não traz como um único item, responda escolha=null: isso é correto e esperado.
Responda com o índice do candidato escolhido ou null se nenhum serve."""

SCHEMA = {
    "type": "object",
    "properties": {"escolha": {"type": ["integer", "null"]}, "motivo": {"type": "string"}},
    "required": ["escolha", "motivo"],
}

ITEM_PEDIDO = "Item pedido:\n"
CANDIDATOS = "Candidatos:\n"


def pedido(item: str, candidatos: list[tuple[str, str]]) -> str:
    """`candidatos`: (nome, categoria) na ordem em que o índice da resposta será lido."""
    lista = "\n".join(f"{i}: {nome} ({categoria})" for i, (nome, categoria) in enumerate(candidatos))
    return f"{ITEM_PEDIDO}{item}\n\n{CANDIDATOS}{lista}"


def exemplo() -> list[tuple[str, str]]:
    item = item_pedido.exemplo()[0][1]
    candidatos = [("Queijo, mozarela", "Leite e derivados"), ("Pizza, de mussarela", "Alimentos preparados")]
    return [("sistema", INSTRUCOES), ("usuário", pedir_json(pedido(item, candidatos), SCHEMA))]
