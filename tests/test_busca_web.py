"""Pesquisa na web para entender o termo pedido (marca/produto desconhecido) antes ou depois da busca no iFood."""
import asyncio
import json

from app.schemas.macro import MealIntent
from app.services import busca_web
from tests.nutricao_comum import settings
from tests.test_busca_agente import ABERTO, FECHADO, LLM, Provedor, plano, rodar

ENTENDI = {"entendi": True, "o_que_e": "bolinho industrializado Ana Maria",
           "consultas": ["bolinho Ana Maria baunilha", "bolinho Ana Maria", "bolo Ana Maria"]}


class Web:
    def __init__(self, resposta):
        self.resposta, self.termos = resposta, []

    async def __call__(self, cfg, prompt):
        self.termos.append(prompt)
        return json.dumps(self.resposta) if isinstance(self.resposta, dict) else self.resposta


def _intent(**campos):
    base = dict(provider_query="bolo", food_query="bolo dona maria", search_queries=["bolo dona maria"])
    base.update(campos)
    return MealIntent(**base)


def test_identificar_devolve_consultas_validas(monkeypatch, tmp_path):
    monkeypatch.setattr(busca_web, "_pesquisar", Web(ENTENDI))
    r = asyncio.run(busca_web.identificar(settings(tmp_path), "bolo dona maria", None, 10))
    assert r == ["bolinho Ana Maria baunilha", "bolinho Ana Maria", "bolo Ana Maria"]


def test_identificar_sem_certeza_ainda_aproveita_as_variacoes(monkeypatch, tmp_path):
    monkeypatch.setattr(busca_web, "_pesquisar", Web({"entendi": False, "o_que_e": "ambíguo", "consultas": ["bolo caseiro"]}))
    assert asyncio.run(busca_web.identificar(settings(tmp_path), "xyz", None, 10)) == ["bolo caseiro"]


def test_identificar_resposta_ruim_ou_vazia_devolve_none(monkeypatch, tmp_path):
    for resposta in ({"entendi": False, "o_que_e": "", "consultas": []}, "não é json"):
        monkeypatch.setattr(busca_web, "_pesquisar", Web(resposta))
        assert asyncio.run(busca_web.identificar(settings(tmp_path), "xyz", None, 10)) is None


def test_consultas_com_simbolos_sao_descartadas(monkeypatch, tmp_path):
    monkeypatch.setattr(busca_web, "_pesquisar",
                        Web({"entendi": True, "o_que_e": "x", "consultas": ["bolo; DROP", "bolo Ana Maria"]}))
    assert asyncio.run(busca_web.identificar(settings(tmp_path), "bolo", None, 10)) == ["bolo Ana Maria"]


def test_modelo_marcou_incerteza_pesquisa_antes_de_consultar_o_ifood(monkeypatch, tmp_path):
    web = Web(ENTENDI)
    monkeypatch.setattr(busca_web, "_pesquisar", web)
    provedor = Provedor([ABERTO()])
    r = rodar(monkeypatch, tmp_path, provedor, LLM(plano()), intent=_intent(pesquisar_na_web="bolo dona maria"),
              busca_web_identificar=True)
    assert len(web.termos) == 1 and "bolo dona maria" in web.termos[0]
    assert provedor.pedidos[0]["queries"][0] == "bolo dona maria"  # a consulta do usuário continua primeiro
    assert "bolinho Ana Maria baunilha" in provedor.pedidos[0]["queries"] and r.recommendations


def test_sem_incerteza_e_com_resultado_nao_pesquisa(monkeypatch, tmp_path):
    web = Web(ENTENDI)
    monkeypatch.setattr(busca_web, "_pesquisar", web)
    rodar(monkeypatch, tmp_path, Provedor([ABERTO()]), LLM(plano()), intent=_intent(), busca_web_identificar=True)
    assert web.termos == []


def test_busca_vazia_pesquisa_o_termo_antes_de_chamar_o_planejador(monkeypatch, tmp_path):
    web = Web(ENTENDI)
    monkeypatch.setattr(busca_web, "_pesquisar", web)
    provedor, llm = Provedor([FECHADO()], [ABERTO("ana")]), LLM(plano())
    r = rodar(monkeypatch, tmp_path, provedor, llm, intent=_intent(), busca_web_identificar=True)
    assert len(web.termos) == 1 and llm.pedidos == []  # o planejador nem precisou rodar
    assert provedor.pedidos[1]["queries"] == ["bolinho Ana Maria baunilha", "bolinho Ana Maria", "bolo Ana Maria"]
    assert [x.candidate.item_id for x in r.recommendations] == ["ana"]


def test_termo_so_e_pesquisado_uma_vez(monkeypatch, tmp_path):
    web = Web(ENTENDI)
    monkeypatch.setattr(busca_web, "_pesquisar", web)
    rodar(monkeypatch, tmp_path, Provedor([FECHADO()]), LLM(plano(search_queries=["lanche"])),
          intent=_intent(pesquisar_na_web="bolo dona maria"), busca_web_identificar=True)
    assert len(web.termos) == 1


def test_desligado_ou_sem_chave_nao_pesquisa(monkeypatch, tmp_path):
    web = Web(ENTENDI)
    monkeypatch.setattr(busca_web, "_pesquisar", web)
    rodar(monkeypatch, tmp_path, Provedor([ABERTO()]), LLM(plano()), intent=_intent(pesquisar_na_web="x1"),
          busca_web_identificar=False)
    rodar(monkeypatch, tmp_path, Provedor([ABERTO()]), LLM(plano()), intent=_intent(pesquisar_na_web="x1"),
          busca_web_identificar=True, gemini_api_key="")
    assert web.termos == []
