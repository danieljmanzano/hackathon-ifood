"""Mensagem certa para cada motivo de a busca não mostrar nada, e sempre pedindo outra coisa."""
import asyncio

import pytest
from fastapi.testclient import TestClient

from app.api.endpoints.macro import get_provider
from app.core.config import get_settings
from app.main import app
from app.services.mock_ifood import MockIFood
from app.services.mensagens_busca import PEDIR_OUTRA_COISA, sem_resultado
from tests.nutricao_comum import candidato
from tests.test_busca_multiplas_consultas import ENDERECO, IFoodFalso, item_json

client = TestClient(app)


# ---------- o texto ----------

def test_nada_encontrado_cita_o_que_foi_procurado_e_pede_outra_coisa():
    texto = sem_resultado([], None, ["sushi", "comida japonesa"])
    assert "Não encontrei “sushi” perto de você" in texto and PEDIR_OUTRA_COISA in texto


def test_consulta_generica_nao_vira_aspas_estranhas():
    texto = sem_resultado([], None, ["refeição"])
    assert texto.startswith("Não encontrei opções perto de você")


def test_tudo_fechado_diz_que_nao_ha_abertos():
    fechados = [candidato(item_id=f"i{n}", merchant_id=f"m{n % 2}", available=False) for n in range(3)]
    texto = sem_resultado(fechados, None, ["sushi"])
    assert "Encontrei 3 itens de 2 restaurantes, mas todos estão fechados agora" in texto
    assert "não há opções abertas" in texto and PEDIR_OUTRA_COISA in texto and "tente de novo" in texto


def test_tudo_fechado_singular():
    texto = sem_resultado([candidato(available=False)], None, ["sushi"])
    assert "Encontrei 1 item de 1 restaurante, mas todos estão fechados" in texto


def test_abertos_mas_acima_do_orcamento_diz_o_preco_mais_baixo():
    caros = [candidato(item_id="a", price_cents=5000), candidato(item_id="b", price_cents=4200)]
    texto = sem_resultado(caros, 3000, ["sushi"])
    assert "nenhuma cabe no orçamento de R$ 30,00" in texto and "a mais barata custa R$ 42,00" in texto
    assert "outra coisa" in texto


def test_abertos_dentro_do_orcamento_mas_filtrados_fala_em_restricoes():
    texto = sem_resultado([candidato(price_cents=1000)], 3000, ["sushi"])
    assert "nenhuma passou pelos seus filtros" in texto and "peça outra coisa" in texto


def test_fechados_pesam_mais_que_orcamento():
    # existe item barato, só que fechado: o problema é o horário, não o preço
    misto = [candidato(item_id="a", available=False, price_cents=1000), candidato(item_id="b", price_cents=9000)]
    assert "cabe no orçamento" in sem_resultado(misto, 3000, ["x"])  # há um aberto e ele estoura o orçamento


# ---------- iFood real (falso): existe mas está fechado ----------

def test_ifood_sem_aberto_confere_se_existem_itens_fechados():
    def resp(nome, args):
        if args.get("resultKind") == "MERCHANT":
            return {"results": []}
        if args["refinements"].get("onlyOpen"):
            return {"results": []}
        return {"results": [item_json("i1", "Combinado", merchant="r1", aberto=False)]}
    ifood = IFoodFalso(resp)
    itens = asyncio.run(ifood.search_many(["sushi"], ENDERECO, None, "japonesa"))
    assert [(c.item_id, c.available) for c in itens] == [("i1", False)]
    ultimas = [a["refinements"] for n, a in ifood.chamadas if a.get("resultKind") == "ITEM"][-1]
    assert "onlyOpen" not in ultimas  # a checagem extra não filtra por abertos


def test_ifood_com_aberto_nao_faz_a_checagem_extra():
    ifood = IFoodFalso(lambda n, a: {"results": [item_json("i1", "Combinado")]})
    asyncio.run(ifood.search_many(["sushi"], ENDERECO, None))
    assert all(a["refinements"].get("onlyOpen") for n, a in ifood.chamadas)  # só a busca normal, 1 chamada
    assert len(ifood.chamadas) == 1


def test_ifood_nada_em_lugar_nenhum_continua_vazio():
    assert asyncio.run(IFoodFalso(lambda n, a: {"results": []}).search_many(["sushi"], ENDERECO, None)) == []


# ---------- a tela recebe a mensagem ----------

class ProvedorFalso(MockIFood):
    """Catálogo fictício (endereços etc.), mas com a busca devolvendo o que o teste mandar."""

    def __init__(self, candidatos):
        self.candidatos = candidatos

    async def search_many(self, queries, address, budget, cuisine=None):
        return self.candidatos


@pytest.fixture
def com_provedor():
    anterior = dict(app.dependency_overrides)

    def usar(candidatos):
        app.dependency_overrides[get_provider] = lambda: ProvedorFalso(candidatos)
        app.dependency_overrides[get_settings] = lambda: get_settings().model_copy(update={"intent_llm_enabled": False})
    yield usar
    app.dependency_overrides.clear()
    app.dependency_overrides.update(anterior)


def _ultima_resposta(texto):
    sessao = client.get("/api/session").json()["id"]
    cookie = {"macro_session": sessao}
    endereco = client.get("/api/addresses", cookies=cookie).json()[0]["id"]
    client.put("/api/session/address", json={"address_id": endereco}, cookies=cookie)
    r = client.post("/api/search", json={"text": texto}, cookies=cookie)
    assert r.status_code == 200
    return r.json()["messages"][-1]["text"], r.json()["recommendations"]


def test_tela_mostra_que_nao_ha_abertos(com_provedor):
    com_provedor([candidato(item_id="a", available=False), candidato(item_id="b", available=False)])
    mensagem, recs = _ultima_resposta("quero sushi")
    assert recs == [] and "todos estão fechados agora" in mensagem and "Peça outra coisa" in mensagem


def test_tela_mostra_nada_encontrado(com_provedor):
    com_provedor([])
    mensagem, recs = _ultima_resposta("quero sushi")
    assert recs == [] and "Não encontrei" in mensagem and "Peça outra coisa" in mensagem


def test_tela_mostra_a_mensagem_escrita_pelo_modelo_quando_ele_explica(com_provedor, monkeypatch):
    from app.services import busca_agente
    from tests.test_busca_agente import LLM, plano
    com_provedor([candidato(item_id="a", available=False)])
    monkeypatch.setattr(busca_agente, "chat_completion", LLM(plano(
        acao="desistir", search_queries=[],
        mensagem_se_nada_for_encontrado="Já são 23h40 e o japonês perto de você fechou. Peça um lanche ou tente amanhã.")))
    # a chave precisa existir para o planejador ser chamado; o falso não usa rede
    app.dependency_overrides[get_settings] = lambda: get_settings().model_copy(
        update={"intent_llm_enabled": False, "openrouter_api_key": "k"})
    mensagem, recs = _ultima_resposta("quero comer japonês")
    assert recs == [] and mensagem == "Já são 23h40 e o japonês perto de você fechou. Peça um lanche ou tente amanhã."


def test_tela_mostra_o_aviso_de_adaptacao_quando_a_nova_busca_acha(com_provedor, monkeypatch):
    from app.services import busca_agente
    from tests.test_busca_agente import LLM, plano
    chamadas = []

    class DuasRodadas(ProvedorFalso):
        async def search_many(self, queries, address, budget, cuisine=None):
            chamadas.append(list(queries))
            return [candidato(item_id="f", available=False)] if len(chamadas) == 1 else [candidato(item_id="ok", price_cents=1500)]

    anterior = dict(app.dependency_overrides)
    app.dependency_overrides[get_provider] = lambda: DuasRodadas([])
    app.dependency_overrides[get_settings] = lambda: get_settings().model_copy(
        update={"intent_llm_enabled": False, "openrouter_api_key": "k"})
    monkeypatch.setattr(busca_agente, "chat_completion", LLM(plano()))
    try:
        mensagem, recs = _ultima_resposta("quero comer japonês")
    finally:
        app.dependency_overrides.clear(); app.dependency_overrides.update(anterior)
    assert len(recs) == 1 and mensagem.startswith("Já é tarde e não achei japonês aberto")
    assert len(chamadas) == 2 and chamadas[1] == ["lanche", "pizza"]
