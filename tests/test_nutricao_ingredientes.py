import asyncio
from unittest.mock import AsyncMock, patch

from app.services.nutrition.etapas import ingredientes as mod
from app.services.nutrition.etapas.bases import carregar_taco
from app.services.nutrition.etapas.ingredientes import casar_ingredientes, somar_ingredientes
from app.services.nutrition.modelos import Ingrediente
from tests.nutricao_comum import DADOS, settings

ALIMENTOS = carregar_taco(str(DADOS))


def _taco(nome):
    return next(a for a in ALIMENTOS if a.nome == nome)


def test_somar_ingredientes_taco_por_gramas():
    ings = [Ingrediente("arroz", 200), Ingrediente("feijão", 100)]
    casados = {"arroz": _taco("Arroz, tipo 1, cozido"), "feijão": _taco("Feijão, carioca, cozido")}
    leitura = somar_ingredientes(ings, casados)
    esperado = 128 * 2 + casados["feijão"].macros.kcal
    assert abs(leitura.macros.kcal - esperado) < 0.01
    assert leitura.fonte == "taco" and leitura.peso_g == 300
    assert leitura.faixa_min < leitura.macros.kcal < leitura.faixa_max


def test_cobertura_insuficiente_nao_vira_fonte():
    ings = [Ingrediente("arroz", 100), Ingrediente("molho secreto", 300)]
    assert somar_ingredientes(ings, {"arroz": _taco("Arroz, tipo 1, cozido"), "molho secreto": None}) is None
    assert somar_ingredientes([], {}) is None


def test_casar_em_lote_com_abstencao(tmp_path):
    ings = [Ingrediente("arroz branco cozido", 200), Ingrediente("ingrediente xyzzy", 50)]
    resposta = {"escolhas": [{"ingrediente": "arroz branco cozido", "escolha": 0}]}
    with patch.object(mod, "perguntar_json", AsyncMock(return_value=resposta)) as fake:
        casados = asyncio.run(casar_ingredientes(settings(tmp_path), ings, ALIMENTOS))
    assert casados["arroz branco cozido"] is not None and casados["ingrediente xyzzy"] is None
    fake.assert_awaited_once()  # uma chamada para todos os ingredientes
