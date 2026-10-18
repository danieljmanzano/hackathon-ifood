"""Skill: papel do agente que conversa com o usuário e usa o MCP do iFood.

Quem usa: agent/orchestrator.py -> ask_llm / build_system_prompt (LLM de texto, com a reserva do outro provedor).
Montagem: mensagem de sistema = BASE + as skills do agente (arquivos agente_*.py) listadas uma abaixo da outra.
"""
BASE = """Você é o assistente de pedidos do iFood focado em nutrição. Macros são estimativas, não aconselhamento médico. Nunca finalize um pedido sem confirmação explícita do usuário."""

TITULO_SKILLS = "\n\n# Skills disponíveis\n\n"


def renderizar(nome: str, descricao: str, conteudo: str) -> str:
    return f"## Skill: {nome}\n{descricao}\n\n{conteudo}"


def montar_system(skills: list[tuple[str, str, str]]) -> str:
    """`skills`: (nome, descrição, conteúdo) de cada skill do agente a ativar."""
    if not skills:
        return BASE
    return f"{BASE}{TITULO_SKILLS}" + "\n\n".join(renderizar(*s) for s in skills)


def exemplo() -> list[tuple[str, str]]:
    return [("sistema sem skills", montar_system([]))]
