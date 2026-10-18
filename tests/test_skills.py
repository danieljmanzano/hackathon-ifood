"""app/skills/ é o único lugar com texto de prompt: arquivos completos, documentados e sem texto solto no código."""
import pathlib
import re

import pytest

import app.skills as skills
from app.skills import AGENTE, SKILLS, comum, item_pedido

RAIZ = pathlib.Path(__file__).resolve().parents[1]
PASTA = RAIZ / "app/skills"


def test_toda_skill_do_disco_esta_no_registro():
    no_disco = {p.stem for p in PASTA.glob("*.py")} - {"__init__", "comum"}
    assert no_disco == set(SKILLS), "skill nova precisa entrar em SKILLS (app/skills/__init__.py)"


@pytest.mark.parametrize("nome", sorted(SKILLS))
def test_cada_skill_se_explica_e_tem_exemplo(nome):
    modulo = SKILLS[nome]
    doc = modulo.__doc__ or ""
    assert doc.strip().startswith("Skill"), f"{nome}: o cabeçalho deve começar com 'Skill ...'"
    assert "Quem usa" in doc or nome.startswith("agente_") or nome == "item_pedido"
    exemplos = modulo.exemplo()
    assert exemplos and all(isinstance(r, str) and isinstance(t, str) and t.strip() for r, t in exemplos)


@pytest.mark.parametrize("nome", sorted(SKILLS))
def test_exemplos_nao_deixam_marcador_sem_preencher(nome):
    for rotulo, texto in SKILLS[nome].exemplo():
        assert not re.search(r"\{(nome|item|pedido|schema|candidatos|restaurante)\}", texto), (nome, rotulo)
        assert "__DOT__" not in texto and "None" not in texto.replace("null", ""), (nome, rotulo)


def test_pedir_json_acrescenta_formato_e_schema_uma_vez():
    texto = comum.pedir_json("Pedido.", {"type": "object"})
    assert texto == 'Pedido.\n\nResponda SOMENTE com um objeto JSON que siga este JSON Schema:\n{"type": "object"}'
    assert texto.count("Responda SOMENTE") == 1


def test_descrever_item_cobre_os_tres_casos_de_opcoes():
    grupos = [("Borda", False, 1, ["Catupiry", "Cheddar"])]
    assert "Opções escolhidas:\n- Catupiry" in item_pedido.descrever("P", "R", "d", ["Catupiry"], grupos)
    assert "Opções ainda não escolhidas" in item_pedido.descrever("P", "R", "d", None, grupos)
    assert "- Borda (opcional, até 1): Catupiry, Cheddar" in item_pedido.descrever("P", "R", "d", None, grupos)
    assert "Opções escolhidas: nenhuma" in item_pedido.descrever("P", "R", "d", None, [])
    assert "Descrição: (sem descrição)" in item_pedido.descrever("P", "R", "", None, [])
    assert item_pedido.descrever("P", "R", "d", None, [], 400.5).endswith("Peso informado do prato: 400.5 g")


def test_skills_do_agente_sao_carregadas_pelo_nome():
    from app.agent.skills import list_skills, load_skill
    assert list_skills() == sorted(AGENTE) == ["ifood_mcp"]
    skill = load_skill("ifood_mcp")
    assert skill.name == "ifood_mcp" and "mcp_call" in skill.content and skill.content == skill.content.strip()
    with pytest.raises(FileNotFoundError):
        load_skill("nao_existe")


# Frases que identificam texto de prompt. Se aparecerem fora de app/skills, alguém voltou a escondê-las no código.
FRASES_DE_PROMPT = [
    "Responda SOMENTE", "Estime as calorias", "Decomponha este item", "Item pedido:", "Encontrado na web",
    "Pesquise a informação", "Pesquise na web e responda", "Opções ainda não escolhidas", "Peso informado do prato",
    "Você é um nutricionista", "Você decide se um alimento", "Você casa ingredientes", "Você verifica se uma informação",
    "Interprete a intenção", "Você é o assistente de pedidos", "Você é o planejador de busca",
]


def test_nenhum_texto_de_prompt_fora_de_app_skills():
    achados = []
    for arquivo in (RAIZ / "app").rglob("*.py"):
        if PASTA in arquivo.parents or arquivo.name == "llm.py" and arquivo.parent.name == "nutrition":
            continue  # llm.py (da main) é código sem uso, tratado à parte
        texto = arquivo.read_text(encoding="utf-8")
        achados += [(str(arquivo.relative_to(RAIZ)), f) for f in FRASES_DE_PROMPT if f in texto]
    assert not achados, f"texto de prompt fora de app/skills: {achados}"


def test_skills_md_antigas_e_prompts_py_sumiram():
    assert not (RAIZ / "app/agent/skills_md").exists()
    assert not (RAIZ / "app/services/nutrition/prompts.py").exists()
