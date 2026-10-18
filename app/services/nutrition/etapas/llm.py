import json

from jsonschema import validate

from app.core.config import Settings
from app.services.openrouter import chat_completion
from ..entrada import extrair_json


async def perguntar_json(settings: Settings, system: str, prompt: str, schema: dict, *,
                         temperature: float = 0.2) -> dict:
    """Pergunta ao LLM do OpenRouter e devolve o JSON validado contra o schema."""
    mensagens = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"{prompt}\n\nResponda SOMENTE com um objeto JSON que siga este JSON Schema:\n"
                                    f"{json.dumps(schema, ensure_ascii=False)}"},
    ]
    texto = await chat_completion(mensagens, json_mode=True, temperature=temperature, settings=settings)
    dados = extrair_json(texto)
    validate(dados, schema)
    return dados
