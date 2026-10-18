"""Skill: juiz que confirma que a tabela achada na web é do MESMO produto (só para produtos industrializados).

Quem usa: etapas/web.py -> _tabela_oficial. Para pratos de restaurante ele não roda: pratos parecidos são aceitos.
Modelo:   LLM de texto (OpenRouter ou OpenAI, com a reserva do outro).
Saída:    {"corresponde": true|false, "motivo": ...}.
"""
from . import item_pedido
from .comum import pedir_json

INSTRUCOES = """Você verifica se uma informação nutricional encontrada na web se refere ao MESMO produto pedido.
Responda corresponde=true somente se for o mesmo prato, do mesmo restaurante ou rede, com tamanho e adicionais
compatíveis com o pedido. Produtos parecidos, de outro restaurante ou de outro tamanho: corresponde=false."""

SCHEMA = {
    "type": "object",
    "properties": {"corresponde": {"type": "boolean"}, "motivo": {"type": "string"}},
    "required": ["corresponde", "motivo"],
}


def pedido(item: str, produto: str, fonte_nome: str, fonte_url: str, trecho: str, porcao_base: str) -> str:
    return (f"Pedido:\n{item}\n\nEncontrado na web:\nProduto: {produto}\n"
            f"Fonte: {fonte_nome} ({fonte_url})\nTrecho: {trecho}\n"
            f"Base dos valores: {porcao_base}")


def exemplo() -> list[tuple[str, str]]:
    item = item_pedido.exemplo()[0][1]
    achado = pedido(item, "Pizza Margherita 35cm", "Pizza Express", "https://pizzaexpress.com.br/nutri",
                    "Margherita: 1800 kcal", "pizza inteira")
    return [("sistema", INSTRUCOES), ("usuário", pedir_json(achado, SCHEMA))]
