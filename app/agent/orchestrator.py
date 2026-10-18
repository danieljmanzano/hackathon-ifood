from dataclasses import dataclass, field
from typing import Any

from app.agent.skills import Skill, load_skill, render_skills
from app.services.openrouter import Message, chat_completion

BASE_SYSTEM_PROMPT = (
    "Você é o assistente de pedidos do iFood focado em nutrição. "
    "Macros são estimativas, não aconselhamento médico. "
    "Nunca finalize um pedido sem confirmação explícita do usuário."
)


@dataclass
class McpAction:
    tool: str
    arguments: dict[str, Any] = field(default_factory=dict)


def build_system_prompt(skills: list[Skill]) -> str:
    if not skills:
        return BASE_SYSTEM_PROMPT
    return f"{BASE_SYSTEM_PROMPT}\n\n# Skills disponíveis\n\n{render_skills(skills)}"


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
