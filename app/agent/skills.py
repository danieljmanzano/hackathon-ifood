"""Skills: arquivos .md (frontmatter name/description + corpo) injetados no system prompt."""
from dataclasses import dataclass
from pathlib import Path

SKILLS_DIR = Path(__file__).parent / "skills_md"


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    content: str


def _parse(path: Path) -> Skill:
    text = path.read_text(encoding="utf-8")
    meta: dict[str, str] = {}
    body = text
    if text.startswith("---\n"):
        header, _, body = text[4:].partition("\n---\n")
        for line in header.splitlines():
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip()
    return Skill(name=meta.get("name", path.stem), description=meta.get("description", ""), content=body.strip())


def load_skill(name: str) -> Skill:
    path = SKILLS_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Skill '{name}' não encontrada em {SKILLS_DIR}")
    return _parse(path)


def list_skills() -> list[str]:
    return sorted(p.stem for p in SKILLS_DIR.glob("*.md"))


def render_skills(skills: list[Skill]) -> str:
    return "\n\n".join(f"## Skill: {s.name}\n{s.description}\n\n{s.content}" for s in skills)
