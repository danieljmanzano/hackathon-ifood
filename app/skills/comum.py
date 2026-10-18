"""Peças compartilhadas pelas skills: o pedido de JSON e o trecho de ingredientes dos schemas."""

import json

# Valor numérico que o modelo pode deixar em branco (null) quando não sabe.
NUM = {"type": ["number", "null"]}

# Lista de ingredientes com a massa de cada um; aparece nos schemas da estimativa, da decomposição e da web.
SCHEMA_INGREDIENTES = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {"nome": {"type": "string"}, "gramas": {"type": "number"}},
        "required": ["nome", "gramas"],
    },
}

# Frase colada ao final de (quase) todo pedido para o modelo responder em JSON; o schema vem logo depois.
FORMATO_JSON = "Responda SOMENTE com um objeto JSON que siga este JSON Schema:\n"


def schema_json(schema: dict) -> str:
    return json.dumps(schema, ensure_ascii=False)


def pedir_json(pedido: str, schema: dict) -> str:
    """O pedido seguido da exigência de JSON e do schema (o que o LLM de texto realmente lê)."""
    return f"{pedido}\n\n{FORMATO_JSON}{schema_json(schema)}"
