"""Pediu "diferente/outro/variado": não repetir o que já foi mostrado e variar os tipos (caso dos bolos de cenoura)."""
import json

import pytest
from fastapi.testclient import TestClient

from app.api.endpoints.macro import get_provider
from app.core.config import get_settings
from app.domain import rank, tipo_do_prato
from app.main import app
from app.schemas.macro import MealIntent, MealRequest, Message, Recommendation, UserProfile
from app.services import conversa as mod_conversa, llm_meal_intent as intent_mod
from app.services.llm_meal_intent import LLMIntent, merge_intent
from app.services.meal_intent import parse_intent
from app.services.mensagens_busca import sem_resultado
from app.skills import busca_intencao
from tests.nutricao_comum import candidato, settings
from tests.test_mensagens_busca import ProvedorFalso

BOLOS = [
    ("c1", "Bolo de Cenoura com Ganache de Chocolate Belga", "padaria-a"),
    ("c2", "Bolo de cenoura", "cafe-b"),
    ("c3", "Bolo de Cenoura com Cobertura", "padaria-c"),
    ("ch", "Bolo de Chocolate", "confeitaria-d"),
    ("fu", "Bolo de Fubá", "padaria-e"),
    ("la", "Bolo de Laranja", "cafe-f"),
]


def bolos(ids=None):
    return [candidato(item_id=i, name=nome, merchant_id=m, description="") for i, nome, m in BOLOS
            if ids is None or i in ids]


def ids(recomendacoes):
    return [r.candidate.item_id for r in recomendacoes]


# ---------- detecção do pedido ----------

@pytest.mark.parametrize("texto", ["ah, queria um bolo diferente, me mostre opções variadas", "quero outra opção",
                                   "me mostra outros", "algo novo por favor", "mais opções de pizza",
                                   "nenhum desses, quero variedade", "não quero esses"])
def test_regras_detectam_pedido_de_variedade(texto):
    assert parse_intent(MealRequest(text=texto)).avoid_repeats is True


@pytest.mark.parametrize("texto", ["quero comer bolo agora", "quero uma pizza de calabresa", "frango grelhado até 30"])
def test_pedido_comum_nao_ativa(texto):
    assert parse_intent(MealRequest(text=texto)).avoid_repeats is False


def test_palavras_de_variedade_nao_viram_comida_na_busca():
    q = parse_intent(MealRequest(text="queria um bolo diferente, me mostre opções variadas")).food_query
    assert "diferente" not in q and "variadas" not in q and "mostre" not in q and "bolo" in q


def test_merge_do_llm_soma_a_deteccao_das_regras():
    base = parse_intent(MealRequest(text="quero um bolo"))
    llm = LLMIntent(goals=[], context_summary="x", food_query="bolo", avoid_repeats=True)
    assert merge_intent(base, llm, "quero um bolo").avoid_repeats is True
    regras = parse_intent(MealRequest(text="quero outro bolo"))
    assert merge_intent(regras, LLMIntent(goals=[], context_summary="x", food_query="bolo"), "quero outro bolo").avoid_repeats


# ---------- tipo do prato ----------

@pytest.mark.parametrize("nome,tipo", [
    ("Bolo de Cenoura com Ganache de Chocolate Belga", "cenoura"), ("Bolo de cenoura", "cenoura"),
    ("Bolos Caseiros Inteiros", ""), ("Bolo de Chocolate", "chocolate"), ("Fatia de Bolo de Fubá", "fubá".replace("á", "a")),
])
def test_tipo_do_prato_ignora_a_comida_pedida_e_palavras_de_formato(nome, tipo):
    assert tipo_do_prato(nome, "bolo") == tipo


# ---------- ranking ----------

def test_com_variedade_os_ja_mostrados_saem_e_os_tipos_se_espalham():
    ja = [("padaria-a", "c1"), ("cafe-b", "c2"), ("padaria-c", "c3")]  # os 3 bolos de cenoura que ele viu
    intent = MealIntent(food_query="bolo", provider_query="bolo", avoid_repeats=True)
    r = rank(bolos(), MealRequest(text="bolo diferente"), UserProfile(id="u"), None, recently_shown=ja, intent=intent)
    assert set(ids(r)) == {"ch", "fu", "la"}  # nenhum de cenoura, três sabores diferentes


def test_sem_pedir_variedade_o_comportamento_antigo_continua():
    ja = [("padaria-a", "c1")]
    intent = MealIntent(food_query="bolo", provider_query="bolo")
    d: dict = {}
    r = rank(bolos(), MealRequest(text="bolo"), UserProfile(id="u"), None, recently_shown=ja, intent=intent,
             diagnostico=d)
    assert len(r) == 3 and "já mostrado antes nesta conversa" not in d  # o já mostrado só leva penalidade


def test_varios_da_mesma_familia_nao_ocupam_todas_as_vagas():
    intent = MealIntent(food_query="bolo", provider_query="bolo", avoid_repeats=True)
    r = rank(bolos({"c1", "c2", "c3", "ch"}), MealRequest(text="outro bolo"), UserProfile(id="u"), None,
             intent=intent, limit=2)
    tipos = sorted(tipo_do_prato(x.candidate.name, "bolo") for x in r)
    assert tipos == ["cenoura", "chocolate"]  # um de cada tipo, não dois de cenoura


def test_se_faltar_variedade_completa_pela_ordem_do_ranking():
    intent = MealIntent(food_query="bolo", provider_query="bolo", avoid_repeats=True)
    r = rank(bolos({"c1", "c2", "c3"}), MealRequest(text="outro bolo"), UserProfile(id="u"), None, intent=intent)
    assert len(r) == 3  # só há cenoura: melhor mostrar do que nada


def test_diagnostico_conta_os_repetidos_para_o_planejador():
    ja = [("padaria-a", "c1"), ("cafe-b", "c2")]
    d: dict = {}
    rank(bolos({"c1", "c2"}), MealRequest(text="outro"), UserProfile(id="u"), None, recently_shown=ja,
         intent=MealIntent(food_query="bolo", provider_query="bolo", avoid_repeats=True), diagnostico=d)
    assert d == {"já mostrado antes nesta conversa": 2}


def test_mensagem_quando_so_sobrou_o_que_ja_foi_mostrado():
    abertos = bolos({"c1", "c2"})
    texto = sem_resultado(abertos, None, ["bolo"], ja_mostrados=2)
    assert "Já mostrei todas as opções abertas" in texto and "Peça outro sabor" in texto
    assert "Já mostrei" not in sem_resultado(abertos, None, ["bolo"], ja_mostrados=1)  # ainda havia um novo


# ---------- o que o agente passa a ver ----------

def _rec(item_id, nome, loja):
    return Recommendation(candidate=candidato(item_id=item_id, name=nome, merchant_name=loja), reasons=[], limitations=[])


def test_agente_ve_os_pratos_que_ja_foram_mostrados(tmp_path):
    from types import SimpleNamespace
    s = SimpleNamespace(messages=[Message(role="user", text="quero bolo")], request_intent=MealIntent(food_query="bolo"),
                        recommendations=[_rec("c1", "Bolo de Cenoura", "Padaria A"), _rec("c1", "duplicado", "x"),
                                         _rec("c2", "Bolo de cenoura", "Café B")])
    c = mod_conversa.montar(s, settings(tmp_path))
    assert c["busca_anterior"]["ja_recomendados"] == [{"prato": "Bolo de Cenoura", "restaurante": "Padaria A"},
                                                      {"prato": "Bolo de cenoura", "restaurante": "Café B"}]


def test_prompt_explica_variedade_e_como_usar_os_ja_recomendados():
    t = busca_intencao.TEXTO
    assert "avoid_repeats=true" in t and "ja_recomendados" in t and "TIPOS, sabores ou estilos DIFERENTES" in t
    assert "bolo de chocolate" in t


# ---------- ponta a ponta: o caso dos bolos de cenoura ----------

client = TestClient(app)


@pytest.fixture
def com_bolos():
    anterior = dict(app.dependency_overrides)
    app.dependency_overrides[get_provider] = lambda: ProvedorFalso(bolos())
    app.dependency_overrides[get_settings] = lambda: get_settings().model_copy(update={"intent_llm_enabled": False})
    yield
    app.dependency_overrides.clear()
    app.dependency_overrides.update(anterior)


def _buscar(cookie, texto):
    r = client.post("/api/search", json={"text": texto}, cookies=cookie)
    assert r.status_code == 200
    return [x["candidate"]["item_id"] for x in r.json()["recommendations"]], r.json()["messages"][-1]["text"]


def test_pediu_bolo_diferente_nao_volta_a_cenoura(com_bolos):
    client.cookies.clear()
    sid = client.get("/api/session").json()["id"]
    cookie = {"macro_session": sid}
    endereco = client.get("/api/addresses", cookies=cookie).json()[0]["id"]
    client.put("/api/session/address", json={"address_id": endereco}, cookies=cookie)

    primeira, _ = _buscar(cookie, "quero comer bolo agora")
    segunda, mensagem = _buscar(cookie, "ah, queria um bolo diferente, me mostre opções variadas")
    assert len(primeira) == 3 and len(segunda) == 3
    assert not set(primeira) & set(segunda)  # nada repetido
    nomes = {i: n for i, n, _ in BOLOS}
    assert len({tipo_do_prato(nomes[i], "bolo") for i in segunda}) >= 2  # não são três do mesmo sabor
    terceira, aviso = _buscar(cookie, "mais uma opção diferente")  # o catálogo de teste acabou
    assert terceira == [] and "Já mostrei todas as opções abertas" in aviso
