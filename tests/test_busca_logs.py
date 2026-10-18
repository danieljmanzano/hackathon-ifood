"""Logs da busca: eventos só com contagens (sem texto do usuário); conteúdo só com BUSCA_LOG_CONTEUDO."""
import logging

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.domain import rank
from app.main import app
from app.schemas.macro import MealRequest, UserProfile
from tests.nutricao_comum import candidato
from tests.test_nutricao_logs import Coletor

client = TestClient(app)


@pytest.fixture
def linhas():
    coletor = Coletor()
    logger_busca, logger_calorias = logging.getLogger("app.busca"), logging.getLogger("app.nutricao")
    niveis = (logger_busca.level, logger_calorias.level)
    for logger in (logger_busca, logger_calorias):
        logger.addHandler(coletor); logger.setLevel(logging.DEBUG)
    yield lambda: " ".join("\n".join(coletor.linhas).split())
    for logger, nivel in zip((logger_busca, logger_calorias), niveis):
        logger.removeHandler(coletor); logger.setLevel(nivel)


@pytest.fixture(autouse=True)
def sem_llm_na_interpretacao():
    anterior = dict(app.dependency_overrides)
    app.dependency_overrides[get_settings] = lambda: get_settings().model_copy(update={"intent_llm_enabled": False})
    yield
    app.dependency_overrides.clear()
    app.dependency_overrides.update(anterior)


def _buscar(texto):
    sessao = client.get("/api/session").json()["id"]
    cookie = {"macro_session": sessao}
    endereco = client.get("/api/addresses", cookies=cookie).json()[0]["id"]
    client.put("/api/session/address", json={"address_id": endereco}, cookies=cookie)
    return client.post("/api/search", json={"text": texto}, cookies=cookie)


def test_busca_conta_as_etapas_com_eventos(linhas):
    assert _buscar("Quero um frango grelhado até 35 reais").status_code == 200
    texto = linhas()
    for evento in ("search.started", "intent.ready", "reviews.ready", "catalog.completed", "ranking.completed",
                   "search.completed"):
        assert evento in texto, evento
    assert '"round": 1' in texto and '"candidate_count"' in texto


def test_logs_da_busca_nao_vazam_o_texto_do_usuario(linhas):
    _buscar("Quero xablau com purpurina até 35 reais")  # palavras que não existem no catálogo
    texto = linhas().lower()
    assert "xablau" not in texto and "purpurina" not in texto and "35 reais" not in texto


def test_busca_sem_resultado_explica_na_tela_e_nao_no_log(linhas):
    resposta = _buscar("quero algo até 1 real")
    assert "nenhuma cabe no orçamento de R$ 1,00" in resposta.json()["messages"][-1]["text"]
    assert "orçamento de R$" not in linhas()  # a mensagem é para o usuário, o log só tem contagens


def test_rank_devolve_o_diagnostico_dos_descartes_em_portugues():
    caros = [candidato(item_id=f"i{n}", name=f"Prato {n}", price_cents=9000) for n in range(3)]
    fechado = candidato(item_id="fechado", available=False)
    diagnostico: dict = {}
    r = rank(caros + [fechado], MealRequest(text="quero algo"), UserProfile(id="u"), 3000, diagnostico=diagnostico)
    assert r == []
    assert diagnostico == {"acima do orçamento de R$ 30.00": 3, "restaurante fechado/indisponível": 1}
