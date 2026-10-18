from dataclasses import dataclass, field
from typing import Any

from app.agent.skills import Skill, load_skill
from app.services.llm_texto import chat_completion_fallback as chat_completion
from app.services.openrouter import Message
from app.skills import agente_pedidos

BASE_SYSTEM_PROMPT = agente_pedidos.BASE  # o texto fica em app/skills/agente_pedidos.py


@dataclass
class McpAction:
    tool: str
    arguments: dict[str, Any] = field(default_factory=dict)


def build_system_prompt(skills: list[Skill]) -> str:
    return agente_pedidos.montar_system([(s.name, s.description, s.content) for s in skills])


async def ask_llm(
    user_message: str,
    *,
    skills: list[str | Skill] | None = None,
    history: list[Message] | None = None,
    model: str | None = None,
) -> str:
    """Envia a mensagem ao OpenRouter com as skills (por nome ou objeto) no system prompt."""
    resolved = [s if isinstance(s, Skill) else load_skill(s) for s in (skills or [])]
    messages: list[Message] = [
        {"role": "system", "content": build_system_prompt(resolved)},
        *(history or []),
        {"role": "user", "content": user_message},
    ]
    return await chat_completion(messages, model=model)


def resolve_mcp_action(llm_response: str) -> McpAction | None:
    """FUTURO: lê a resposta da LLM, decide se há chamada ao MCP e devolve a ação (ou None).

    O formato esperado é o bloco ```mcp_call {...}``` descrito na skill `ifood_mcp`.
    Depois a ação deve ser executada via `app.services.ifood_mcp.ifood_session()`
    (`session.call_tool(action.tool, action.arguments)`) e o resultado devolvido à LLM.
    """
    raise NotImplementedError
