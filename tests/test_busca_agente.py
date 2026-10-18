"""Laço de agente da busca: sem resultado, o modelo replaneja ou explica, dentro de guardas."""
import asyncio
import json
import time
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.core.exceptions import AppError
from app.schemas.macro import MealIntent, MealRequest, UserProfile
from app.services import busca_agente, horario
from app.services.busca_agente import buscar
from app.skills import busca_intencao, busca_replanejar
from tests.nutricao_comum import candidato, settings

ENDERECO = SimpleNamespace(latitude=-22.9, longitude=-47.0)


class Provedor:
    """Devolve, por rodada, a lista que o teste combinou (e guarda o que foi pedido)."""
    simulated = False

    def __init__(self, *rodadas):
        self.rodadas, self.pedidos = list(rodadas), []

    async def search_many(self, queries, address, budget, cuisine=None):
        self.pedidos.append({"queries": list(queries), "budget": budget, "cuisine": cuisine})
        return self.rodadas[min(len(self.pedidos) - 1, len(self.rodadas) - 1)]


def plano(**campos):
    base = {"diagnostico": "tarde da noite", "acao": "buscar_de_novo", "search_queries": ["lanche", "pizza"],
            "cuisine": "lanchonete", "relaxar_orcamento_padrao": False,
            "aviso_adaptacao": "Já é tarde e não achei japonês aberto; mostrei lanches e pizzas.",
            "mensagem_se_nada_for_encontrado": "São 23h40 e nada está aberto para esse pedido. Peça outra coisa amanhã."}
    base.update(campos)
    return base


class LLM:
    """Substitui o modelo: devolve as respostas combinadas (JSON ou exceção) e guarda os pedidos."""

    def __init__(self, *respostas):
        self.respostas, self.pedidos = list(respostas), []

    async def __call__(self, messages, **kw):
        self.pedidos.append(messages)
        r = self.respostas[min(len(self.pedidos) - 1, len(self.respostas) - 1)]
        if isinstance(r, BaseException):
            raise r
        return r if isinstance(r, str) else json.dumps(r, ensure_ascii=False)


def rodar(monkeypatch, tmp_path, provedor, llm, *, intent=None, perfil=None, inicio=None, **cfg):
    monkeypatch.setattr(busca_agente, "chat_completion", llm)
    s = settings(tmp_path, **cfg)
    intent = intent or MealIntent(provider_query="sushi", food_query="japonês", search_queries=["sushi", "temaki"],
                                  cuisine="japonesa")
    sessao = SimpleNamespace(profile=perfil or UserProfile(id="u"), address=ENDERECO, mode="live",
                             recent_recommendations=[])
    return asyncio.run(buscar(MealRequest(text="quero comer japonês, tô com fome"), sessao, provedor, s, intent, None,
                              inicio if inicio is not None else time.monotonic()))


ABERTO = lambda i="a", **k: candidato(item_id=i, name=f"Prato {i}", **k)
FECHADO = lambda i="f": candidato(item_id=i, name=f"Fechado {i}", available=False)


# ---------- caminhos ----------

def test_achou_de_primeira_nao_chama_o_modelo(monkeypatch, tmp_path):
    llm = LLM(plano())
    r = rodar(monkeypatch, tmp_path, Provedor([ABERTO()]), llm)
    assert r.recommendations and r.aviso_vazio is None and r.aviso_adaptacao is None
    assert llm.pedidos == []


def test_sem_resultado_o_modelo_replaneja_e_a_segunda_rodada_acha(monkeypatch, tmp_path):
    provedor = Provedor([FECHADO()], [ABERTO("lanche1")])
    llm = LLM(plano())
    r = rodar(monkeypatch, tmp_path, provedor, llm)
    assert [x.candidate.item_id for x in r.recommendations] == ["lanche1"]
    assert provedor.pedidos[1]["queries"] == ["lanche", "pizza"] and provedor.pedidos[1]["cuisine"] == "lanchonete"
    assert r.aviso_adaptacao.startswith("Já é tarde") and r.aviso_vazio is None
    assert len(r.tentativas) == 2 and len(llm.pedidos) == 1


def test_modelo_desiste_e_a_mensagem_dele_vai_ao_usuario(monkeypatch, tmp_path):
    provedor = Provedor([FECHADO()])
    r = rodar(monkeypatch, tmp_path, provedor, LLM(plano(acao="desistir", search_queries=[])))
    assert r.recommendations == [] and r.aviso_vazio.startswith("São 23h40")
    assert len(provedor.pedidos) == 1  # não buscou de novo


def test_replanejou_mas_continua_vazio_usa_a_mensagem_do_modelo(monkeypatch, tmp_path):
    provedor = Provedor([FECHADO()], [FECHADO("g")])
    r = rodar(monkeypatch, tmp_path, provedor, LLM(plano()))
    assert r.recommendations == [] and len(provedor.pedidos) == 2 and r.aviso_vazio.startswith("São 23h40")
    assert r.aviso_adaptacao is None


def test_o_modelo_recebe_o_diagnostico_com_hora_e_origem_do_orcamento(monkeypatch, tmp_path):
    llm = LLM(plano(acao="desistir", search_queries=[]))
    rodar(monkeypatch, tmp_path, Provedor([FECHADO(), FECHADO("g")]), llm, perfil=UserProfile(id="u", default_budget_cents=3000))
    sistema, usuario = [m["content"] for m in llm.pedidos[0]]
    assert sistema == busca_replanejar.INSTRUCOES
    assert usuario.startswith(busca_replanejar.CABECALHO)
    dados = json.loads(usuario.split("\n", 1)[1].split("\n\nResponda SOMENTE")[0])
    assert dados["pedido"] == "quero comer japonês, tô com fome"
    assert set(dados["agora"]) == {"data", "hora", "dia_da_semana", "periodo"}
    assert dados["orcamento"] == {"valor_reais": 30.0, "origem": "padrao_do_perfil"}
    tentativa = dados["tentativas"][0]
    assert tentativa["consultas"] == ["sushi", "temaki"] and tentativa["itens_encontrados"] == 2
    assert tentativa["itens_abertos"] == 0 and tentativa["restaurantes_fechados"] == 1
    assert tentativa["descartes_do_ranking"] == {"restaurante fechado/indisponível": 2}


# ---------- guardas ----------

def test_orcamento_do_usuario_nunca_e_relaxado_mesmo_que_o_modelo_peca(monkeypatch, tmp_path):
    caro = ABERTO(price_cents=9000)
    provedor = Provedor([caro], [caro])
    intent = MealIntent(provider_query="sushi", search_queries=["sushi"], budget_cents=3000)
    rodar(monkeypatch, tmp_path, provedor, LLM(plano(relaxar_orcamento_padrao=True)), intent=intent)
    assert [p["budget"] for p in provedor.pedidos] == [3000, 3000]


def test_orcamento_padrao_do_perfil_pode_ser_relaxado(monkeypatch, tmp_path):
    caro = ABERTO(price_cents=9000)
    provedor = Provedor([caro], [caro])
    r = rodar(monkeypatch, tmp_path, provedor, LLM(plano(relaxar_orcamento_padrao=True)),
              perfil=UserProfile(id="u", default_budget_cents=3000))
    assert [p["budget"] for p in provedor.pedidos] == [3000, None]
    assert len(r.recommendations) == 1 and r.budget is None


def test_restricoes_do_usuario_continuam_valendo_na_nova_rodada(monkeypatch, tmp_path):
    amendoim = ABERTO("pacoca", description="com amendoim")
    perfil = UserProfile(id="u", restrictions=["amendoim"])
    r = rodar(monkeypatch, tmp_path, Provedor([FECHADO()], [amendoim]), LLM(plano()), perfil=perfil)
    assert r.recommendations == []  # o modelo não consegue contornar a restrição


def test_consulta_repetida_nao_e_tentada_de_novo(monkeypatch, tmp_path):
    provedor = Provedor([FECHADO()])
    r = rodar(monkeypatch, tmp_path, provedor, LLM(plano(search_queries=["Sushi", "temaki"])))
    assert len(provedor.pedidos) == 1 and r.aviso_vazio  # nada novo: encerra


def test_respeita_o_maximo_de_replanejamentos(monkeypatch, tmp_path):
    provedor = Provedor([FECHADO()])
    llm = LLM(plano(search_queries=["a1", "a2"]), plano(search_queries=["b1", "b2"]), plano(search_queries=["c1", "c2"]))
    rodar(monkeypatch, tmp_path, provedor, llm, busca_max_replanejamentos=2)
    assert len(provedor.pedidos) == 3 and len(llm.pedidos) == 2


@pytest.mark.parametrize("cfg", [{"busca_replanejar": False}, {"busca_max_replanejamentos": 0}])
def test_desligado_nao_chama_o_modelo_e_usa_a_mensagem_fixa(monkeypatch, tmp_path, cfg):
    llm = LLM(plano())
    r = rodar(monkeypatch, tmp_path, Provedor([FECHADO()]), llm, **cfg)
    assert llm.pedidos == [] and "todos estão fechados agora" in r.aviso_vazio


def test_sem_tempo_nao_replaneja(monkeypatch, tmp_path):
    llm = LLM(plano())
    r = rodar(monkeypatch, tmp_path, Provedor([FECHADO()]), llm, inicio=time.monotonic() - 25)
    assert llm.pedidos == [] and "todos estão fechados agora" in r.aviso_vazio


# ---------- o modelo falha: cai na mensagem fixa ----------

@pytest.mark.parametrize("resposta", [AppError("sem cota"), asyncio.TimeoutError(), "isto não é json",
                                      {"acao": "buscar_de_novo"}])
def test_modelo_com_problema_cai_na_mensagem_fixa(monkeypatch, tmp_path, resposta):
    r = rodar(monkeypatch, tmp_path, Provedor([FECHADO()]), LLM(resposta))
    assert r.recommendations == [] and "todos estão fechados agora" in r.aviso_vazio


def test_mensagem_do_modelo_curta_demais_e_ignorada(monkeypatch, tmp_path):
    r = rodar(monkeypatch, tmp_path, Provedor([FECHADO()]),
              LLM(plano(acao="desistir", search_queries=[], mensagem_se_nada_for_encontrado="ok")))
    assert "todos estão fechados agora" in r.aviso_vazio


# ---------- horário ----------

def test_periodos_do_dia():
    assert [horario.periodo(h) for h in (2, 8, 12, 16, 20, 23)] == [
        "madrugada", "manhã", "horário de almoço", "tarde", "noite (jantar)", "fim da noite"]


def test_agora_usa_o_fuso_do_usuario(tmp_path):
    h = horario.agora(settings(tmp_path), datetime(2026, 10, 19, 2, 40, tzinfo=timezone.utc))
    assert h == {"data": "2026-10-18", "hora": "23:40", "dia_da_semana": "domingo", "periodo": "fim da noite"}


def test_interpretacao_da_busca_recebe_a_hora_e_a_instrucao_de_usa_la():
    agora = {"data": "2026-10-18", "hora": "23:40", "dia_da_semana": "domingo", "periodo": "fim da noite"}
    corpo = json.loads(busca_intencao.mensagem_usuario("quero sushi", agora))
    assert corpo == {"message": "quero sushi", "agora": agora}
    assert json.loads(busca_intencao.mensagem_usuario("quero sushi")) == {"message": "quero sushi"}
    assert '"agora"' in busca_intencao.TEXTO and "poucos lugares estão abertos" in busca_intencao.TEXTO
