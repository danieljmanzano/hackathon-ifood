import asyncio
import json
from unittest.mock import AsyncMock, patch

from app.services.nutrition.etapas import web
from app.services.nutrition.etapas.web import buscar_na_web, dominio
from tests.nutricao_comum import candidato, settings


def _resposta(**campos):
    dados = {"encontrado": True, "produto_na_fonte": "Pizza Margherita 35cm", "calorias": 1800, "faixa_min": 1700,
             "faixa_max": 1900, "proteina_g": 70, "carbo_g": 220, "gordura_g": 60, "porcao_g": 700,
             "porcao_base": "pizza inteira", "fonte_nome": "Pizza Express", "fonte_url": "https://www.pizzaexpress.com.br/nutri",
             "trecho_fonte": "Margherita: 1800 kcal", "justificativa": "Tabela do site."}
    dados.update(campos)
    return "```json\n" + json.dumps(dados) + "\n```"


def _buscar(tmp_path, texto, consultados, juiz=True):
    with patch.object(web, "search_web", AsyncMock(return_value=(texto, consultados))), \
         patch.object(web, "perguntar_json", AsyncMock(return_value={"corresponde": juiz, "motivo": "m"})) as j:
        return asyncio.run(buscar_na_web(settings(tmp_path), candidato(), None)), j


def test_dominio():
    assert dominio("https://www.Site.com.br/a/b") == "site.com.br"
    assert dominio("site.com.br") == "site.com.br"


def test_web_aceita_fonte_consultada_e_juiz_aprova(tmp_path):
    info, _ = _buscar(tmp_path, _resposta(), ["pizzaexpress.com.br"])
    assert info.method == "web" and info.macros.kcal == 1800 and info.faixa == (1700, 1900)
    assert info.porcao_g == 700 and info.fonte_url.endswith("/nutri")


def test_web_descarta_fonte_nao_consultada_sem_chamar_o_juiz(tmp_path):
    info, juiz = _buscar(tmp_path, _resposta(), ["outrosite.com"])
    assert info is None
    juiz.assert_not_called()


def test_web_descarta_quando_juiz_diz_que_e_outro_produto(tmp_path):
    info, _ = _buscar(tmp_path, _resposta(), ["pizzaexpress.com.br"], juiz=False)
    assert info is None


def test_web_nao_encontrado_sem_trecho_ou_numero_invalido(tmp_path):
    assert _buscar(tmp_path, _resposta(encontrado=False), ["pizzaexpress.com.br"])[0] is None
    assert _buscar(tmp_path, _resposta(trecho_fonte=" "), ["pizzaexpress.com.br"])[0] is None
    assert _buscar(tmp_path, _resposta(calorias=None), ["pizzaexpress.com.br"])[0] is None


def test_web_faixa_incoerente_e_ignorada(tmp_path):
    info, _ = _buscar(tmp_path, _resposta(faixa_min=1900, faixa_max=2000), ["pizzaexpress.com.br"])
    assert info.faixa is None
