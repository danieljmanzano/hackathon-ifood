"""Skill: juiz que confirma que a tabela achada na web é do MESMO produto (só para produtos industrializados).

Quem usa: etapas/web.py -> _tabela_oficial. Para pratos de restaurante ele não roda: pratos parecidos são aceitos.
Modelo:   LLM de texto (OpenRouter ou OpenAI, com a reserva do outro).
Saída:    {"corresponde": true|false, "motivo": ...}.
"""
from . import item_pedido
from .comum import pedir_json

INSTRUCOES = """Você verifica se uma informação nutricional encontrada na web se refere ao MESMO produto pedido.
O pedido é um produto industrializado, de marca e embalado, vendido por um restaurante ou mercado do iFood. O lugar onde
ele é vendido NÃO importa: a tabela pode ser do fabricante ou de outro mercado que vende o mesmo produto.
Responda corresponde=true quando marca, linha, sabor/variante e tamanho da embalagem forem os mesmos (diferenças só de
escrita, acento ou ordem das palavras não contam). Responda corresponde=false se mudar a marca, o sabor, o tamanho da
embalagem ou o número de unidades, ou se for um produto apenas parecido."""

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
