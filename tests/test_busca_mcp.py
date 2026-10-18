"""O agente de busca usando o MCP do iFood (só leitura): validação, resumo, laço e travas."""
import asyncio
import json
import logging
import time
from types import SimpleNamespace

import pytest

from app.core.exceptions import MacroError
from app.schemas.macro import MealIntent, MealRequest, UserProfile
from app.services import busca_agente, busca_mcp
from app.services.ifood_live import MCPIFood
from app.skills import busca_mcp as skill_mcp, busca_replanejar
from tests.nutricao_comum import candidato, settings
from tests.test_busca_agente import ENDERECO, FECHADO, LLM, Provedor, plano
from tests.test_busca_multiplas_consultas import IFoodFalso, item_json
from tests.test_llm_texto import _capturar, _linhas

LAT, LON = ENDERECO.latitude, ENDERECO.longitude


# ---------- preparar: o que o código deixa passar ----------

def prep(chamada, vistos=()):
    return busca_mcp.preparar(chamada, LAT, LON, set(vistos))


def test_so_as_quatro_tools_de_leitura_passam():
    for nome in ("createCart", "addItemToCart", "submitOrder", "getUser", "listAddresses", "trackOrder", "getItem"):
        pronta, recusa = prep({"ferramenta": nome, "argumentos": {}})
        assert pronta is None and "não permitida" in recusa, nome
    assert prep({"ferramenta": "listItemTaxonomy"})[0] is not None


def test_localizacao_vem_do_usuario_e_userid_do_modelo_e_ignorado():
    (nome, args), recusa = prep({"ferramenta": "browseOffers", "argumentos": {
        "userLocation": {"latitude": 0, "longitude": 0}, "userId": "outro-usuario", "resultKind": "ITEM"}})
    assert recusa is None and args["userLocation"] == {"latitude": LAT, "longitude": LON}
    assert "userId" not in args
    (_, taxonomia), _ = prep({"ferramenta": "listItemTaxonomy", "argumentos": {"userLocation": {"latitude": 1}}})
    assert "userLocation" not in taxonomia  # a tool é pública: sem geo


def test_tipo_de_loja_e_sempre_restaurante_e_pagina_e_limitada():
    (_, args), _ = prep({"ferramenta": "searchOffers", "argumentos": {"query": "sushi", "merchantType": "DRUGSTORE",
                                                                      "pageSize": 999}})
    assert args["merchantType"] == "RESTAURANT" and args["pageSize"] == busca_mcp.MAX_PAGINA
    assert args["resultKind"] == "ITEM"


def test_regras_de_argumentos():
    assert "exige 'query'" in prep({"ferramenta": "searchOffers", "argumentos": {"query": "  "}})[1]
    assert "resultKind" in prep({"ferramenta": "browseOffers", "argumentos": {"resultKind": "TUDO"}})[1]
    assert "refinements deve ser" in prep({"ferramenta": "browseOffers", "argumentos": {"refinements": "x"}})[1]
    assert "exige merchantId" in prep({"ferramenta": "getMerchant", "argumentos": {}})[1]


def test_ids_inventados_sao_recusados_e_ids_vistos_passam():
    inventado = {"ferramenta": "getMerchant", "argumentos": {"merchantId": "ffffffff-0000"}}
    assert "não apareceu em nenhum resultado" in prep(inventado)[1]
    assert prep(inventado, vistos={"ffffffff-0000"})[1] is None
    cardapio = {"ferramenta": "browseOffers", "argumentos": {"refinements": {"merchantId": "r1"}}}
    assert prep(cardapio)[1] is not None and prep(cardapio, vistos={"r1"})[1] is None


# ---------- refinamentos para a próxima busca ----------

def test_refinamentos_so_com_categorias_vistas_e_valores_razoaveis():
    vistas = {"japanese_food", "pizza"}
    ok = busca_mcp.sanear_refinamentos({"itemTaxonomy": ["japanese_food", "inventada"], "maxDistanceKm": 5,
                                        "maxDeliveryTimeMinutes": 40, "onlyOpen": False, "maxItemPrice": 1,
                                        "merchantId": "x"}, vistas)
    assert ok == {"itemTaxonomy": ["japanese_food"], "maxDistanceKm": 5.0, "maxDeliveryTimeMinutes": 40}
    assert busca_mcp.sanear_refinamentos({"maxDistanceKm": 500, "maxDeliveryTimeMinutes": True}, vistas) == {}
    assert busca_mcp.sanear_refinamentos("lixo", vistas) == {} and busca_mcp.sanear_refinamentos(None, vistas) == {}


# ---------- resumos ----------

def test_resumos_curtos_para_o_modelo():
    taxonomia = {"taxonomy": [{"id": "japanese_food", "name": "Japonesa", "availability": "PLENTIFUL"}]}
    assert busca_mcp.resumir("listItemTaxonomy", {}, taxonomia) == {
        "categorias": [{"id": "japanese_food", "nome": "Japonesa", "disponibilidade": "PLENTIFUL"}]}
    restaurantes = {"results": [{"merchantId": "r1", "merchantName": "Sushi Norte", "isOpen": False,
                                 "nextOpenAt": "18:00", "reviewRating": 4.8, "straightLineDistanceKm": 2.1}],
                    "facets": {"itemTaxonomy": [{"id": "sashimi", "name": "Sashimi"}]}}
    r = busca_mcp.resumir("searchOffers", {"resultKind": "MERCHANT"}, restaurantes)
    assert r["restaurantes"][0] == {"merchantId": "r1", "nome": "Sushi Norte", "aberto": False, "nota": 4.8,
                                    "distancia_km": 2.1, "proxima_abertura": "18:00"}
    assert r["categorias_relacionadas"] == [{"id": "sashimi", "nome": "Sashimi"}]
    itens = busca_mcp.resumir("browseOffers", {"resultKind": "ITEM"}, {"results": [item_json("i1", "Combinado")]})
    assert itens["itens"][0]["nome"] == "Combinado" and itens["itens"][0]["merchantId"] == "m1"
    loja = busca_mcp.resumir("getMerchant", {}, {"merchantName": "X", "isOpen": True,
                                                 "operatingHours": {"today": {"openLocal": "11:00", "closeLocal": "23:00"}},
                                                 "featuredItems": [{"itemName": "Pizza", "unitPrice": 30.0}]})
    assert loja["aberto"] is True and loja["hoje_abre_fecha"] == ["11:00", "23:00"] and loja["itens_em_destaque"]
    erro = busca_mcp.resumir("searchOffers", {}, {"errors": {"code": "INVALID_QUERY", "message": "x" * 500, "retryable": True}})
    assert erro["erro"]["codigo"] == "INVALID_QUERY" and len(erro["erro"]["mensagem"]) == 160


def test_resumo_nao_despeja_a_lista_inteira():
    muitos = {"results": [item_json(f"i{n}", f"Prato {n}") for n in range(40)]}
    assert len(busca_mcp.resumir("browseOffers", {"resultKind": "ITEM"}, muitos)["itens"]) == 10


def test_so_pratos_abertos_de_buscas_de_item_viram_candidatos():
    dados = {"results": [item_json("a", "Aberto"), item_json("b", "Fechado", aberto=False)]}
    achados = busca_mcp.candidatos_abertos({"resultKind": "ITEM"}, dados, MCPIFood.itens_de_resposta)
    assert [c.item_id for c in achados] == ["a"]
    assert busca_mcp.candidatos_abertos({"resultKind": "MERCHANT"}, dados, MCPIFood.itens_de_resposta) == []
    assert busca_mcp.candidatos_abertos({"resultKind": "ITEM"}, {"errors": {"code": "X"}}, MCPIFood.itens_de_resposta) == []
    assert busca_mcp.candidatos_abertos({"resultKind": "ITEM"}, {"results": [{"lixo": 1}]}, MCPIFood.itens_de_resposta) == []


# ---------- MCPIFood.chamar_ferramentas ----------

def test_ifood_executa_as_chamadas_em_paralelo_e_isola_falhas():
    def resp(nome, args):
        if nome == "getMerchant":
            return MacroError("restaurante sumiu", 404)
        return {"taxonomy": [{"id": "pizza", "name": "Pizza"}]}
    ifood = IFoodFalso(resp)
    r = asyncio.run(ifood.chamar_ferramentas([("listItemTaxonomy", {"merchantType": "RESTAURANT"}),
                                              ("getMerchant", {"merchantId": "r1"})]))
    assert r[0] == {"ok": True, "dados": {"taxonomy": [{"id": "pizza", "name": "Pizza"}]}}
    assert r[1] == {"ok": False, "erro": "restaurante sumiu"}
    assert [n for n, _ in ifood.chamadas] == ["listItemTaxonomy", "getMerchant"]


def test_ifood_aplica_os_refinamentos_da_proxima_busca():
    ifood = IFoodFalso(lambda n, a: {"results": [item_json("i1", "Sushi")]})
    asyncio.run(ifood.search_many(["sushi"], ENDERECO, 3000, None, refinamentos={"itemTaxonomy": ["japanese_food"]}))
    refinamentos = ifood.chamadas[0][1]["refinements"]
    assert refinamentos == {"onlyOpen": True, "maxItemPrice": 30.0, "itemTaxonomy": ["japanese_food"]}


# ---------- o laço do agente ----------

class ProvedorMCP(Provedor):
    """iFood falso com MCP: guarda as buscas (com refinamentos) e as chamadas de ferramenta."""

    def __init__(self, *rodadas, ferramentas=None, falha_nas_ferramentas=None):
        super().__init__(*rodadas)
        self.ferramentas = ferramentas or (lambda nome, args: {"results": []})
        self.falha = falha_nas_ferramentas
        self.chamadas = []

    async def search_many(self, queries, address, budget, cuisine=None, refinamentos=None):
        self.pedidos.append({"queries": list(queries), "budget": budget, "cuisine": cuisine,
                             "refinamentos": refinamentos})
        return self.rodadas[min(len(self.pedidos) - 1, len(self.rodadas) - 1)]

    async def chamar_ferramentas(self, chamadas):
        self.chamadas.append(chamadas)
        if self.falha:
            raise self.falha
        return [{"ok": True, "dados": self.ferramentas(n, a)} for n, a in chamadas]

    itens_de_resposta = staticmethod(MCPIFood.itens_de_resposta)


def tool(nome, **argumentos):
    return {"ferramenta": nome, "argumentos": argumentos}


def laco(monkeypatch, tmp_path, provedor, *respostas, **cfg):
    llm = LLM(*respostas)
    monkeypatch.setattr(busca_agente, "chat_completion", llm)
    s = settings(tmp_path, **cfg)
    intent = MealIntent(provider_query="sushi", search_queries=["sushi"], cuisine="japonesa")
    sessao = SimpleNamespace(profile=UserProfile(id="u"), address=ENDERECO, mode="live", recent_recommendations=[])
    r = asyncio.run(busca_agente.buscar(MealRequest(text="quero comer japonês"), sessao, provedor, s, intent, None,
                                        time.monotonic()))
    return r, llm


TAXONOMIA = {"taxonomy": [{"id": "japanese_food", "name": "Japonesa", "availability": "PLENTIFUL"}]}


def test_explora_categorias_e_aplica_o_que_aprendeu_na_proxima_busca(monkeypatch, tmp_path):
    provedor = ProvedorMCP([FECHADO()], [candidato(item_id="ok", name="Combinado")], ferramentas=lambda n, a: TAXONOMIA)
    r, llm = laco(monkeypatch, tmp_path, provedor,
                  plano(acao="usar_ferramentas", search_queries=[], chamadas=[tool("listItemTaxonomy")]),
                  plano(search_queries=["temaki"], refinamentos={"itemTaxonomy": ["japanese_food", "inventada"]}))
    assert [x.candidate.item_id for x in r.recommendations] == ["ok"]
    assert provedor.pedidos[1]["queries"] == ["temaki"]
    assert provedor.pedidos[1]["refinamentos"] == {"itemTaxonomy": ["japanese_food"]}  # a inventada caiu
    # o 2º pedido ao modelo traz o resumo do que a tool devolveu, e o 1º já listava as ferramentas
    sistema1, _ = [m["content"] for m in llm.pedidos[0]]
    _, usuario2 = [m["content"] for m in llm.pedidos[1]]
    assert skill_mcp.FERRAMENTAS in sistema1
    assert '"observacoes_mcp"' in usuario2 and "japanese_food" in usuario2 and '"mcp_disponivel": true' in usuario2
    assert provedor.chamadas == [[("listItemTaxonomy", {"merchantType": "RESTAURANT"})]]


def test_pratos_abertos_achados_pelas_tools_viram_opcoes_sem_nova_busca_no_catalogo(monkeypatch, tmp_path):
    def ferramentas(nome, args):
        return {"results": [item_json("lanche1", "X-Burger", merchant="r9")]}
    provedor = ProvedorMCP([FECHADO()], ferramentas=ferramentas)
    r, _ = laco(monkeypatch, tmp_path, provedor,
                plano(acao="usar_ferramentas", search_queries=[], chamadas=[tool("browseOffers", resultKind="ITEM")]),
                plano(search_queries=[], aviso_adaptacao="Achei lanches abertos agora, perto de você."))
    assert [x.candidate.item_id for x in r.recommendations] == ["lanche1"]
    assert len(provedor.pedidos) == 1  # a rodada 2 usou só o que as tools acharam
    assert r.aviso_adaptacao.startswith("Achei lanches abertos")


def test_chamadas_perigosas_ou_inventadas_nunca_chegam_ao_ifood(monkeypatch, tmp_path):
    provedor = ProvedorMCP([FECHADO()])
    r, llm = laco(monkeypatch, tmp_path, provedor,
                  plano(acao="usar_ferramentas", search_queries=[], chamadas=[
                      tool("createCart", merchantId="m1"), tool("submitOrder"),
                      tool("getMerchant", merchantId="inventado-123")]),
                  plano(acao="desistir", search_queries=[]))
    assert provedor.chamadas == []  # nenhuma passou
    _, usuario2 = [m["content"] for m in llm.pedidos[1]]
    assert usuario2.count("recusada") == 3 and "não permitida" in usuario2 and "não invente ids" in usuario2


def test_restaurante_visto_na_busca_pode_ser_consultado(monkeypatch, tmp_path):
    provedor = ProvedorMCP([FECHADO()], ferramentas=lambda n, a: {"merchantName": "Fechado Ltda", "isOpen": False})
    laco(monkeypatch, tmp_path, provedor,
         plano(acao="usar_ferramentas", search_queries=[], chamadas=[tool("getMerchant", merchantId="m1")]),
         plano(acao="desistir", search_queries=[]))
    assert provedor.chamadas and provedor.chamadas[0][0][0] == "getMerchant"  # m1 veio do resultado da busca


def test_localizacao_e_injetada_pelo_codigo(monkeypatch, tmp_path):
    provedor = ProvedorMCP([FECHADO()])
    laco(monkeypatch, tmp_path, provedor,
         plano(acao="usar_ferramentas", search_queries=[], chamadas=[
             tool("searchOffers", query="pizza", userLocation={"latitude": 1, "longitude": 2})]),
         plano(acao="desistir", search_queries=[]))
    _, args = provedor.chamadas[0][0]
    assert args["userLocation"] == {"latitude": LAT, "longitude": LON}


def test_falha_do_ifood_nas_ferramentas_nao_derruba_e_o_modelo_decide_assim_mesmo(monkeypatch, tmp_path):
    provedor = ProvedorMCP([FECHADO()], falha_nas_ferramentas=MacroError("sem login", 503))
    r, llm = laco(monkeypatch, tmp_path, provedor,
                  plano(acao="usar_ferramentas", search_queries=[], chamadas=[tool("listItemTaxonomy")]),
                  plano(acao="desistir", search_queries=[]))
    assert r.recommendations == [] and r.aviso_vazio.startswith("São 23h40")
    assert "o iFood não respondeu a tempo" in llm.pedidos[1][1]["content"]


def test_so_um_passo_de_exploracao_depois_o_modelo_precisa_decidir(monkeypatch, tmp_path):
    provedor = ProvedorMCP([FECHADO()])
    pede = plano(acao="usar_ferramentas", search_queries=[], chamadas=[tool("listItemTaxonomy")])
    r, llm = laco(monkeypatch, tmp_path, provedor, pede, pede, pede)
    assert len(provedor.chamadas) == 1 and len(llm.pedidos) == 2  # explora uma vez; na 2ª ainda pede: encerra
    assert r.recommendations == [] and r.aviso_vazio  # mensagem padrão/do modelo, sem laço infinito


def test_sem_mcp_no_mock_o_modelo_nem_ve_as_ferramentas(monkeypatch, tmp_path):
    provedor = Provedor([FECHADO()])  # catálogo fictício: sem chamar_ferramentas
    r, llm = laco(monkeypatch, tmp_path, provedor, plano(acao="usar_ferramentas", search_queries=[],
                                                          chamadas=[tool("listItemTaxonomy")]))
    sistema, usuario = [m["content"] for m in llm.pedidos[0]]
    assert sistema == busca_replanejar.INSTRUCOES and skill_mcp.FERRAMENTAS not in sistema
    assert '"mcp_disponivel": false' in usuario
    assert r.recommendations == [] and len(llm.pedidos) == 1  # pediu ferramenta que não existe: segue o padrão


def test_chave_desliga_as_ferramentas_mesmo_no_modo_live(monkeypatch, tmp_path):
    provedor = ProvedorMCP([FECHADO()])
    _, llm = laco(monkeypatch, tmp_path, provedor, plano(acao="desistir", search_queries=[]),
                  busca_mcp_ferramentas=False)
    assert skill_mcp.FERRAMENTAS not in llm.pedidos[0][0]["content"] and provedor.chamadas == []


def test_logs_das_ferramentas_sao_so_contagens(monkeypatch, tmp_path):
    coletor, restaurar = _capturar()
    logging.getLogger("app.busca").addHandler(coletor); logging.getLogger("app.busca").setLevel(logging.INFO)
    try:
        provedor = ProvedorMCP([FECHADO()], ferramentas=lambda n, a: TAXONOMIA)
        laco(monkeypatch, tmp_path, provedor,
             plano(acao="usar_ferramentas", search_queries=[], chamadas=[tool("listItemTaxonomy")]),
             plano(acao="desistir", search_queries=[], diagnostico="XABLAU-PRIVADO"))
    finally:
        logging.getLogger("app.busca").removeHandler(coletor); restaurar()
    texto = _linhas(coletor)
    assert "search.mcp_call" in texto and '"tool": "listItemTaxonomy"' in texto and '"ok": true' in texto
    assert "japanese_food" not in texto and "XABLAU" not in texto


# ---------- skills ----------

def test_planejador_so_ganha_a_lista_de_ferramentas_com_mcp():
    assert skill_mcp.FERRAMENTAS in busca_replanejar.instrucoes(True)
    assert busca_replanejar.instrucoes(False) == busca_replanejar.INSTRUCOES
    assert "usar_ferramentas" in busca_replanejar.SCHEMA["properties"]["acao"]["enum"]
    for proibida in ("createCart", "addItemToCart", "submitOrder"):
        assert proibida not in skill_mcp.FERRAMENTAS
