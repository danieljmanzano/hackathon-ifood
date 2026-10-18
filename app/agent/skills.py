"""Skills do agente: os textos ficam em app/skills/agente_*.py; aqui só se carrega pelo nome."""
from dataclasses import dataclass

from app.skills import AGENTE
from app.skills.agente_pedidos import renderizar


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    content: str


def load_skill(name: str) -> Skill:
    modulo = AGENTE.get(name)
    if modulo is None:
        raise FileNotFoundError(f"Skill '{name}' não encontrada. Disponíveis: {sorted(AGENTE)}")
    return Skill(name=modulo.NOME, description=modulo.DESCRICAO, content=modulo.CONTEUDO.strip())


def list_skills() -> list[str]:
    return sorted(AGENTE)


def render_skills(skills: list[Skill]) -> str:
    return "\n\n".join(renderizar(s.name, s.description, s.content) for s in skills)
