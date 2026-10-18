"""Teste manual: chama o OpenRouter com a skill ifood_mcp.

Uso: .venv/bin/python -m scripts.try_openrouter ["sua pergunta"]
"""

import asyncio
import sys

from app.agent.orchestrator import ask_llm, build_system_prompt
from app.agent.skills import list_skills, load_skill


async def main() -> None:
    question = (
        " ".join(sys.argv[1:])
        or "Quero um almoço com bastante proteína, perto de casa. Pode buscar opções?"
    )
    print(f"Skills: {list_skills()}")
    print(f"System prompt: {len(build_system_prompt([load_skill('ifood_mcp')]))} caracteres\n")
    print(f"> {question}\n")
    answer = await ask_llm(question, skills=["ifood_mcp"])
    print(answer)
    print("\nbloco mcp_call presente:", "```mcp_call" in answer)


if __name__ == "__main__":
    asyncio.run(main())
