import asyncio
import json
from types import SimpleNamespace as NS

import pytest
from fastapi.testclient import TestClient

from backend.app.config import Settings
from backend.app.ifood.mock import catalog
from backend.app.main import create_app
from backend.app.nutrition import service
from backend.app.nutrition.service import enrich_recommendations, estimate_nutrition
from backend.app.schemas import MealCandidate, Recommendation

ESTIMATIVA = {"suficiente": True, "calorias": 600, "faixa_min": 450, "faixa_max": 750, "confianca": "media",
              "porcao_base": "prato de ~450 g", "justificativa": "estimado", "suposicoes": ["arroz ~150 g"]}
BUSCA = {"encontrado": True, "calorias": 2200, "faixa_min": 2100, "faixa_max": 2300, "confianca": "alta",
         "porcao_base": "pizza grande inteira (8 fatias)", "fonte_nome": "Tabela Domino's",
         "fonte_url": "https://www.dominos.com.br/nutricional?x=1", "trecho_fonte": "275 kcal por fatia",
         "justificativa": "8 fatias x 275 kcal"}


class FakeResponses:
    def __init__(self, busca=None, estimativa=None, fontes=("https://dominos.com.br/a",), atraso=0.0, erro=None):
        self.busca, self.estimativa, self.fontes = busca or BUSCA, estimativa or ESTIMATIVA, fontes
        self.atraso, self.erro, self.chamadas = atraso, erro, []

    async def create(self, **kw):
        tipo = "busca" if kw.get("tools") else "estimativa"
        self.chamadas.append(tipo)
        await asyncio.sleep(self.atraso)
        if self.erro:
            raise self.erro
        if tipo == "busca":
            saida = [NS(type="web_search_call", action=NS(sources=[NS(url=u) for u in self.fontes]))]
            return NS(output=saida, output_text=json.dumps(self.busca))
        return NS(output=[], output_text=json.dumps(self.estimativa))


def fake(**kw):
    return NS(responses=FakeResponses(**kw))


def pizza(**kw) -> MealCandidate:
    dados = dict(merchant_id="m1", merchant_name="Domino's Pizza", item_id="i1", name="Pizza Grande",
                 description="Pizza Grande (35 cm) com 8 fatias.", image_url=None, price_cents=10490)
    return MealCandidate(**{**dados, **kw})


@pytest.fixture(autouse=True)
def limpa_cache():
    service._cache.clear()
    service._em_andamento.clear()


def settings(**kw) -> Settings:
    return Settings(OPENAI_API_KEY="sk-teste", **kw)


def rodar(coro):
    return asyncio.run(coro)


def test_usa_tabela_publicada_quando_encontrada():
    cliente = fake()
    r = rodar(estimate_nutrition(pizza(), settings(), cliente))
    assert (r.state, r.method, r.calories, r.minimum, r.maximum) == ("ready", "published", 2200, 2100, 2300)
    assert r.confidence == "high" and "275 kcal" in r.evidence
    assert cliente.responses.chamadas == ["busca"]


def test_fonte_fora_dos_sites_consultados_cai_na_estimativa():
    cliente = fake(fontes=("https://outro-site.com/x",))
    r = rodar(estimate_nutrition(pizza(), settings(), cliente))
    assert (r.state, r.method, r.calories) == ("ready", "estimated", 600)
    assert cliente.responses.chamadas == ["busca", "estimativa"]


def test_sem_restaurante_ou_simulado_nao_busca_na_web():
    for item in (pizza(merchant_name="não informado"), pizza(simulated=True)):
        cliente = fake()
        rodar(estimate_nutrition(item, settings(), cliente))
        assert cliente.responses.chamadas == ["estimativa"]


def test_faixa_inconsistente_vira_erro_sem_reordenar():
    cliente = fake(estimativa={**ESTIMATIVA, "calorias": 900})
    r = rodar(estimate_nutrition(pizza(simulated=True), settings(), cliente))
    assert r.state == "error" and r.calories is None


def test_modelo_pode_se_abster():
    cliente = fake(estimativa={**ESTIMATIVA, "suficiente": False, "calorias": None, "faixa_min": None, "faixa_max": None})
    r = rodar(estimate_nutrition(pizza(simulated=True), settings(), cliente))
    assert r.state == "unavailable" and r.calories is None


def test_falha_da_api_vira_erro():
    cliente = fake(erro=service.OpenAIError("fora do ar"))
    r = rodar(estimate_nutrition(pizza(), settings(), cliente))
    assert r.state == "error"


def test_sem_chave_fica_indisponivel():
    r = rodar(estimate_nutrition(pizza(), Settings(OPENAI_API_KEY="")))
    assert r.state == "unavailable"


def test_foto_ilustrativa_nao_e_enviada():
    cliente = fake()
    item = pizza(simulated=True, description="Bolo de pote. *Foto ilustrativa*", image_url="https://exemplo.com/a.jpg")
    r = rodar(estimate_nutrition(item, settings(), cliente))
    assert any("ilustrativa" in s for s in r.assumptions)


def test_cache_evita_segunda_chamada():
    cliente = fake()
    rodar(estimate_nutrition(pizza(), settings(), cliente))
    rodar(estimate_nutrition(pizza(), settings(), cliente))
    assert cliente.responses.chamadas == ["busca"]


def test_recomendacoes_lentas_voltam_pending():
    recs = [Recommendation(candidate=c, reasons=["x"], limitations=["Informação nutricional indisponível. Calorias e macros não foram calculados."])
            for c in catalog()]

    async def cenario():
        rapido = await enrich_recommendations(recs, settings(), fake())
        lento = await enrich_recommendations(
            [r.model_copy(update={"candidate": r.candidate.model_copy(update={"item_id": r.candidate.item_id + "-2"})}) for r in recs],
            settings(nutrition_response_budget_seconds=0.05), fake(atraso=1))
        return rapido, lento

    rapido, lento = rodar(cenario())
    assert all(r.nutrition.state == "ready" and r.limitations == [] for r in rapido)
    assert all(r.nutrition.state == "pending" for r in lento)


def test_busca_da_api_preenche_nutricao(tmp_path, monkeypatch):
    cliente = fake()
    monkeypatch.setattr(service, "criar_cliente", lambda s: cliente)
    app = create_app(settings(database_path=tmp_path / "db.sqlite3", ifood_mode="mock"))
    with TestClient(app) as http:
        http.get("/api/session")
        http.put("/api/session/address", json={"address_id": "demo-address"})
        resposta = http.post("/api/search", json={"text": "frango"})
    assert resposta.status_code == 200, resposta.text
    recs = resposta.json()["recommendations"]
    assert recs and all(r["nutrition"]["state"] == "ready" and r["nutrition"]["calories"] == 600 for r in recs)
    assert cliente.responses.chamadas == ["estimativa"] * len(recs)  # catálogo simulado: sem busca na web


def _app(tmp_path, monkeypatch, cliente, **kw):
    monkeypatch.setattr(service, "criar_cliente", lambda s: cliente)
    return create_app(settings(database_path=tmp_path / "db.sqlite3", ifood_mode="mock", **kw))


def _escolher(http, item_id="demo-frango"):
    return http.put("/api/selection", json={"merchant_id": "demo-cozinha", "item_id": item_id, "quantity": 2,
                                            "options": [{"group_id": "demo-base", "option_id": "demo-arroz"}]})


def test_restaurantes_cardapio_e_calorias_do_prato_montado(tmp_path, monkeypatch):
    cliente = fake()
    with TestClient(_app(tmp_path, monkeypatch, cliente)) as http:
        http.get("/api/session")
        assert http.get("/api/merchants").status_code == 422  # sem endereço
        http.put("/api/session/address", json={"address_id": "demo-address"})
        restaurantes = http.get("/api/merchants").json()
        assert restaurantes[0]["merchant_id"] == "demo-cozinha"
        assert _escolher(http).status_code == 422  # item fora da busca e de cardápio aberto
        cardapio = http.get("/api/merchants/demo-cozinha/menu").json()
        assert {i["item_id"] for i in cardapio} == {"demo-frango", "demo-vegetal", "demo-carne"}
        assert http.get("/api/items/demo-cozinha/demo-frango").status_code == 200
        sessao = _escolher(http).json()
    escolhido = sessao["selected"]
    assert escolhido["quantity"] == 2 and escolhido["option_labels"] == ["1 × Arroz integral"]
    assert escolhido["nutrition"]["state"] == "ready" and escolhido["nutrition"]["calories"] == 600
    assert cliente.responses.chamadas == ["estimativa"]


def test_prato_lento_fica_pending_e_atualiza_depois(tmp_path, monkeypatch):
    cliente = fake(atraso=0.5)
    with TestClient(_app(tmp_path, monkeypatch, cliente, nutrition_response_budget_seconds=0.05)) as http:
        http.get("/api/session")
        http.put("/api/session/address", json={"address_id": "demo-address"})
        http.get("/api/merchants/demo-cozinha/menu")
        assert _escolher(http, "demo-carne").json()["selected"]["nutrition"]["state"] == "pending"
        import time
        time.sleep(0.8)
        assert http.get("/api/selection/nutrition").json()["selected"]["nutrition"]["state"] == "ready"


def test_cadastra_endereco_em_duas_etapas_e_seleciona(tmp_path, monkeypatch):
    with TestClient(_app(tmp_path, monkeypatch, fake())) as http:
        http.get("/api/session")
        assert http.post("/api/addresses/geocode", json={"address": "Rua inexistente 1"}).status_code == 422
        achado = http.post("/api/addresses/geocode", json={"address": "Rua Nova, 10, Campinas"}).json()
        assert achado["match"] == "SINGLE" and achado["candidates"][0]["neighborhood"] == "Centro"
        resposta = http.post("/api/addresses", json={"address": "Rua Nova, 10, Campinas",
                                                     "candidate_id": achado["candidates"][0]["candidate_id"],
                                                     "complement": "apto 3", "alias": "CASA"})
        assert resposta.status_code == 200, resposta.text
        corpo = resposta.json()
        assert len(corpo["addresses"]) == 2
        assert corpo["session"]["address"]["label"] == "Casa" and "apto 3" in corpo["session"]["address"]["formatted"]
        assert http.post("/api/addresses", json={"address": "Rua Nova, 10", "candidate_id": "x",
                                                 "alias": "PRAIA"}).status_code == 422  # apelido fora do permitido
