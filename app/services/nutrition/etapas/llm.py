from jsonschema import validate

from app.core.config import Settings
from app.core.nutrition_budget import current_budget
from app.skills import agente_nutricao
from app.services.llm_texto import chat_completion_fallback
from app.skills.comum import pedir_json
from ..entrada import extrair_json


async def perguntar_json(settings: Settings, system: str, prompt: str, schema: dict, *,
                         temperature: float = 0.2) -> dict:
    """Pergunta ao LLM de texto (provedor escolhido, com a reserva do outro) e devolve o JSON validado."""
    if current_budget.get():
        system += "\n\n" + agente_nutricao.CONTEUDO
    pedido = pedir_json(prompt, schema)
    mensagens = [{"role": "system", "content": system}, {"role": "user", "content": pedido}]
    texto = await chat_completion_fallback(mensagens, json_mode=True, temperature=temperature,
                                           preferido=settings.nutrition_provider, settings=settings)
    dados = extrair_json(texto)
    validate(dados, schema)
    return dados
