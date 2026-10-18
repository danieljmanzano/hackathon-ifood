import json

from jsonschema import validate

from app.core.config import Settings
from app.services.openai_client import responder
from app.services.openrouter import chat_completion
from ..entrada import extrair_json


async def perguntar_json(settings: Settings, system: str, prompt: str, schema: dict, *,
                         temperature: float = 0.2) -> dict:
    """Pergunta ao LLM do provedor escolhido (OpenRouter ou OpenAI) e devolve o JSON validado contra o schema."""
    pedido = (f"{prompt}\n\nResponda SOMENTE com um objeto JSON que siga este JSON Schema:\n"
              f"{json.dumps(schema, ensure_ascii=False)}")
    if settings.nutrition_provider == "openai":
        texto, _ = await responder(pedido, instrucoes=system, settings=settings)
    else:
        mensagens = [{"role": "system", "content": system}, {"role": "user", "content": pedido}]
        texto = await chat_completion(mensagens, json_mode=True, temperature=temperature, settings=settings)
    dados = extrair_json(texto)
    validate(dados, schema)
    return dados
