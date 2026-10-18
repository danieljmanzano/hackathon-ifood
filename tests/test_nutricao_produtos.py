from datetime import datetime, timezone

from app.schemas.macro import NutritionResult, SelectedItem, SelectedOption
from app.services.nutrition.produtos import RepositorioProdutos, chave_produto
from tests.nutricao_comum import candidato


def _resultado(versao="v1", kcal=600):
    return NutritionResult(state="ready", method="estimated", portion_basis="prato", calories=kcal,
                           minimum=kcal - 100, maximum=kcal + 100, pipeline_version=versao, obtained_at=datetime.now(timezone.utc))


def _selecionado(opcoes):
    return SelectedItem(candidate=candidato(), quantity=1,
                        options=[SelectedOption(group_id="g", option_id=o, quantity=1) for o in opcoes],
                        option_labels=opcoes, unit_total_cents=3290)


def test_chave_ignora_ordem_das_opcoes_e_diferencia_opcoes():
    assert chave_produto(_selecionado(["a", "b"])) == chave_produto(_selecionado(["b", "a"]))
    assert chave_produto(_selecionado(["a"])) != chave_produto(_selecionado(["a", "b"]))
    assert chave_produto(_selecionado([])) != chave_produto(candidato())


def test_grava_e_le(tmp_path):
    repo = RepositorioProdutos(tmp_path / "p.json")
    c = candidato()
    assert repo.get("k", "v1") is None
    repo.put("k", _resultado(), c)
    assert repo.get("k", "v1").calories == 600


def test_versao_antiga_do_pipeline_recalcula(tmp_path):
    repo = RepositorioProdutos(tmp_path / "p.json")
    repo.put("k", _resultado("v1"), candidato())
    assert repo.get("k", "v2") is None


def test_so_grava_resultado_pronto(tmp_path):
    repo = RepositorioProdutos(tmp_path / "p.json")
    repo.put("k", NutritionResult(state="error"), candidato())
    assert not (tmp_path / "p.json").exists()


def test_manual_nunca_e_sobrescrito_e_vale_em_qualquer_versao(tmp_path):
    import json
    caminho = tmp_path / "p.json"
    repo = RepositorioProdutos(caminho)
    repo.put("k", _resultado("v1", kcal=600), candidato())
    dados = json.loads(caminho.read_text())
    dados["produtos"]["k"]["origem"] = "manual"
    caminho.write_text(json.dumps(dados))

    repo.put("k", _resultado("v2", kcal=999), candidato())
    assert repo.get("k", "v2").calories == 600


def test_json_corrompido_vira_base_vazia_e_guarda_backup(tmp_path):
    caminho = tmp_path / "p.json"
    caminho.write_text("{ não é json")
    repo = RepositorioProdutos(caminho)
    assert repo.get("k", "v1") is None
    assert (tmp_path / "p.bak").exists()
    repo.put("k", _resultado(), candidato())
    assert repo.get("k", "v1").calories == 600
