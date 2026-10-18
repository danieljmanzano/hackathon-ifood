import asyncio
from unittest.mock import AsyncMock, patch

from app.services.nutrition.etapas import bases
from app.services.nutrition.etapas.bases import candidatos, carregar_taco, consultar_bases, normalizar_texto
from tests.nutricao_comum import DADOS, candidato, settings


def test_normalizar_texto():
    assert normalizar_texto("Feijão, Carioca – cozido!") == "feijao carioca cozido"


def test_taco_carrega_com_valores_por_100g():
    alimentos = carregar_taco(str(DADOS))
    assert len(alimentos) > 500
    arroz = next(a for a in alimentos if a.nome == "Arroz, tipo 1, cozido")
    assert arroz.macros.kcal == 128 and arroz.macros.proteina_g == 2.5


def test_taco_ausente_devolve_vazio(tmp_path):
    assert carregar_taco(str(tmp_path)) == ()


def test_candidatos_por_titulo():
    alimentos = carregar_taco(str(DADOS))
    nomes = [a.nome for a in candidatos(alimentos, "arroz branco cozido")]
    assert "Arroz, tipo 1, cozido" in nomes
    assert candidatos(alimentos, "xyzzy quux") == []
    assert candidatos(alimentos, "") == []


def test_juiz_escolhe_ou_se_abstem(tmp_path):
    s = settings(tmp_path)
    c = candidato(name="Arroz branco cozido")
    with patch.object(bases, "perguntar_json", AsyncMock(return_value={"escolha": 0, "motivo": "ok"})):
        info = asyncio.run(consultar_bases(s, c, "descricao"))
    assert info.method == "database" and info.base == "100g" and info.fonte_nome == "TACO"
    assert "kcal por 100 g" in info.evidencia

    with patch.object(bases, "perguntar_json", AsyncMock(return_value={"escolha": None, "motivo": "nenhum"})):
        assert asyncio.run(consultar_bases(s, c, "descricao")) is None
    with patch.object(bases, "perguntar_json", AsyncMock(return_value={"escolha": 99, "motivo": "indice ruim"})):
        assert asyncio.run(consultar_bases(s, c, "descricao")) is None


def test_prato_composto_sem_candidato_nao_chama_o_juiz(tmp_path):
    s = settings(tmp_path)
    fake = AsyncMock()
    with patch.object(bases, "perguntar_json", fake):
        assert asyncio.run(consultar_bases(s, candidato(name="Combo Smash Duplo Premium XPTO"), "d")) is None
    fake.assert_not_called()
