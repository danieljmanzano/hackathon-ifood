"""Busca na web: produto industrializado -> tabela oficial (InfoOnline); prato -> estimativa pesquisada (Leitura)."""
import asyncio
import json
from unittest.mock import AsyncMock, patch

from app.services.nutrition.etapas import web
from app.services.nutrition.etapas.web import buscar_na_web, dominio
from app.services.nutrition.modelos import InfoOnline, Leitura
from tests.nutricao_comum import candidato, settings

FOTO = (b"\x89PNG-foto", "image/png")


def resposta_json(**campos):
    dados = {"tipo_item": "industrializado", "encontrado": True, "produto_na_fonte": "Pizza Margherita 35cm",
             "calorias": 1800, "faixa_min": 1700, "faixa_max": 1900, "proteina_g": 70, "carbo_g": 220,
             "gordura_g": 60, "porcao_g": 700, "porcao_base": "pizza inteira", "confianca": "alta",
             "fonte_nome": "Pizza Express", "fonte_url": "https://www.pizzaexpress.com.br/nutri",
             "trecho_fonte": "Margherita: 1800 kcal", "ingredientes": [], "suposicoes": [],
             "justificativa": "Tabela do site."}
    dados.update(campos)
    return dados


def _resposta(**campos):
    return "```json\n" + json.dumps(resposta_json(**campos)) + "\n```"


def _buscar(tmp_path, texto, consultados, juiz=True, imagem=None):
    with patch.object(web, "search_web", AsyncMock(return_value=(texto, consultados))) as busca, \
         patch.object(web, "perguntar_json", AsyncMock(return_value={"corresponde": juiz, "motivo": "m"})) as j:
        achado = asyncio.run(buscar_na_web(settings(tmp_path), candidato(), None, imagem))
    return achado, j, busca


def test_dominio():
    assert dominio("https://www.Site.com.br/a/b") == "site.com.br"
    assert dominio("site.com.br") == "site.com.br"


# ---------- industrializado: tabela oficial ----------

def test_industrializado_aceita_tabela_consultada_com_juiz(tmp_path):
    info, _, _ = _buscar(tmp_path, _resposta(), ["pizzaexpress.com.br"])
    assert isinstance(info, InfoOnline) and info.method == "web" and info.macros.kcal == 1800
    assert info.faixa == (1700, 1900) and info.porcao_g == 700 and info.fonte_url.endswith("/nutri")


def test_industrializado_descarta_fonte_nao_consultada_sem_chamar_o_juiz(tmp_path):
    info, juiz, _ = _buscar(tmp_path, _resposta(), ["outrosite.com"])
    assert info is None
    juiz.assert_not_called()


def test_industrializado_descarta_quando_juiz_diz_que_e_outro_produto(tmp_path):
    assert _buscar(tmp_path, _resposta(), ["pizzaexpress.com.br"], juiz=False)[0] is None


def test_descartes_por_falta_de_base(tmp_path):
    consultados = ["pizzaexpress.com.br"]
    assert _buscar(tmp_path, _resposta(encontrado=False), consultados)[0] is None
    assert _buscar(tmp_path, _resposta(trecho_fonte=" "), consultados)[0] is None
    assert _buscar(tmp_path, _resposta(calorias=None), consultados)[0] is None


def test_faixa_incoerente_da_tabela_e_ignorada(tmp_path):
    info, _, _ = _buscar(tmp_path, _resposta(faixa_min=1900, faixa_max=2000), ["pizzaexpress.com.br"])
    assert info.faixa is None


# ---------- prato: estimativa pesquisada ----------

PRATO = dict(tipo_item="prato", produto_na_fonte="Hambúrguer artesanal com queijo e bacon", calorias=950,
             faixa_min=800, faixa_max=1100, proteina_g=50, carbo_g=55, gordura_g=55, porcao_g=330,
             porcao_base="hambúrguer artesanal ~330 g", confianca="media", fonte_nome="TabelaNutri",
             fonte_url="https://tabelanutri.com.br/hamburguer", trecho_fonte="Hambúrguer artesanal: 280 kcal/100 g",
             ingredientes=[{"nome": "pão", "gramas": 90}, {"nome": "carne", "gramas": 150}],
             suposicoes=["porção de ~330 g pela foto"], justificativa="Valores de pratos equivalentes, ajustados.")


def test_prato_vira_estimativa_que_vai_para_o_consenso_nao_fonte_oficial(tmp_path):
    achado, juiz, _ = _buscar(tmp_path, _resposta(**PRATO), ["tabelanutri.com.br"])
    assert isinstance(achado, Leitura) and achado.fonte == "web"
    assert achado.macros.kcal == 950 and (achado.faixa_min, achado.faixa_max) == (800, 1100)
    assert achado.peso_g == 330 and [i.nome for i in achado.ingredientes] == ["pão", "carne"]
    assert achado.confianca == 0.5  # media, e nunca passa de 0,65 por ser estimativa
    assert any("Estimativa pesquisada na web com base em" in x and "tabelanutri.com.br" in x for x in achado.suposicoes)
    juiz.assert_not_called()  # prato similar é aceito: não exige "mesmo produto"


def test_prato_aceita_pratos_parecidos_mas_exige_fonte_realmente_consultada(tmp_path):
    assert _buscar(tmp_path, _resposta(**PRATO), ["outrosite.com"])[0] is None
    assert _buscar(tmp_path, _resposta(**{**PRATO, "fonte_url": ""}), ["tabelanutri.com.br"])[0] is None
    assert _buscar(tmp_path, _resposta(**{**PRATO, "encontrado": False}), ["tabelanutri.com.br"])[0] is None
    assert _buscar(tmp_path, _resposta(**{**PRATO, "calorias": 0}), ["tabelanutri.com.br"])[0] is None


def test_prato_sem_faixa_valida_ganha_faixa_de_25_por_cento(tmp_path):
    achado, _, _ = _buscar(tmp_path, _resposta(**{**PRATO, "faixa_min": None, "faixa_max": None}),
                           ["tabelanutri.com.br"])
    assert (round(achado.faixa_min), round(achado.faixa_max)) == (712, 1188)


# ---------- foto ----------

def test_foto_vai_para_a_pesquisa_e_o_prompt_avisa(tmp_path):
    _, _, busca = _buscar(tmp_path, _resposta(**PRATO), ["tabelanutri.com.br"], imagem=FOTO)
    assert busca.call_args.kwargs["imagem"] == FOTO
    assert "a foto dele está anexada" in busca.call_args.args[0]
    _, _, busca = _buscar(tmp_path, _resposta(**PRATO), ["tabelanutri.com.br"])
    assert busca.call_args.kwargs["imagem"] is None and "(sem foto)" in busca.call_args.args[0]


def test_instrucoes_nao_mandam_achar_tabela_de_restaurante():
    from app.services.nutrition.prompts import INSTRUCOES_WEB
    assert "NÃO procure uma tabela do restaurante" in INSTRUCOES_WEB and "ESTIMATIVA" in INSTRUCOES_WEB
