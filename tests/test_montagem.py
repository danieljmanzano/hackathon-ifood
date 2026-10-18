"""Montagem do pedido pelo assistente: base, teto impossível, ajustes com o que o cálculo mostrou e 3 tentativas."""
import asyncio

import pytest

from app.api.endpoints.macro import _alvo_da_montagem, _limites_da_montagem
from app.schemas.macro import (Assembly, AssemblyLimits, MealIntent, NutritionPreferences, NutritionResult, Option,
                               OptionGroup, Recommendation, Session, UserProfile)
from app.services import montagem
from tests.nutricao_comum import candidato, settings

PROTEINA = OptionGroup(id="g1", name="Proteína", min_selections=1, max_selections=1, options=[
    Option(id="frango", name="Frango grelhado", price_cents=0), Option(id="bife", name="Bife", price_cents=400),
    Option(id="camarao", name="Camarão", price_cents=300)])
EXTRAS = OptionGroup(id="g2", name="Extras", min_selections=0, max_selections=3, options=[
    Option(id="ovo", name="Ovo", price_cents=200), Option(id="bacon", name="Bacon", price_cents=300)])


def prato(preco=2800, grupos=(PROTEINA, EXTRAS)):
    return candidato(name="Marmita Fit", price_cents=preco, option_groups=list(grupos), description="Marmita")


def nutricao(kcal, prot=30.0, carb=40.0, gord=10.0):
    return NutritionResult(state="ready", calories=kcal, minimum=kcal * .9, maximum=kcal * 1.1, portion_basis="400 g",
                           method="estimated", protein_g=prot, carbs_g=carb, fat_g=gord, portion_grams=400,
                           assumptions=["porção de 400 g"], pipeline_version="t")


class Calculo:
    """Nutrição por combinação de complementos (os ids ordenados) e registro do que foi calculado."""
    def __init__(self, tabela, padrao=None):
        self.tabela, self.padrao, self.chamadas = tabela, padrao, []

    async def __call__(self, selecionado):
        chave = tuple(sorted(o.option_id for o in selecionado.options))
        self.chamadas.append(chave)
        return self.tabela.get(chave, self.padrao or nutricao(500))


class Modelo:
    def __init__(self, *respostas):
        self.respostas, self.dados = list(respostas), []

    async def __call__(self, cfg, dados, erro=None):
        self.dados.append((dados, erro))
        r = self.respostas[min(len(self.dados) - 1, len(self.respostas) - 1)]
        if isinstance(r, BaseException):
            raise r
        return r


def proposta(*ids, quantidade=1, motivo="escolhi"):
    grupos = {"frango": "g1", "bife": "g1", "camarao": "g1", "ovo": "g2", "bacon": "g2"}
    return {"opcoes": [{"group_id": grupos[i], "option_id": i, "quantity": 1} for i in ids],
            "quantidade": quantidade, "motivo": motivo}


def rodar(tmp_path, calculo, modelo, limites, candidate=None, perfil=None, **cfg):
    eventos = []
    r = asyncio.run(montagem.montar(settings(tmp_path, **cfg), candidate or prato(), limites, perfil or UserProfile(id="u"),
                                    [], eventos.append, calculo, propor_fn=modelo))
    return r, eventos


def limites(preco=None, **nutri):
    return AssemblyLimits(max_price_cents=preco, nutrition=NutritionPreferences(**nutri))


def test_base_mais_barato_ja_passa_do_preco_e_impossivel_sem_calcular(tmp_path):
    calculo = Calculo({})
    r, _ = rodar(tmp_path, calculo, Modelo(proposta("frango")), limites(preco=2000))
    assert r.state == "impossible" and "R$ 28,00" in r.message and calculo.chamadas == []


def test_base_ja_passa_do_teto_de_calorias_e_impossivel(tmp_path):
    calculo = Calculo({("frango",): nutricao(900)})
    modelo = Modelo(proposta("frango"))
    r, _ = rodar(tmp_path, calculo, modelo, limites(max_calories=600))
    assert r.state == "impossible" and "calorias" in r.message and modelo.dados == []


def test_primeira_proposta_atende_e_fica_pronta(tmp_path):
    calculo = Calculo({("frango",): nutricao(520, prot=30), ("frango", "ovo"): nutricao(600, prot=42)})
    r, eventos = rodar(tmp_path, calculo, Modelo(proposta("frango", "ovo")), limites(preco=3500, max_calories=650, min_protein_g=40))
    assert r.state == "ready" and r.attempt == 1 and {o.option_id for o in r.options} == {"frango", "ovo"}
    assert "Pronto!" in r.message and any("Pedido base" in e for e in eventos)


def test_ajusta_com_o_que_o_calculo_mostrou(tmp_path):
    calculo = Calculo({("frango",): nutricao(520, prot=30), ("bacon", "frango"): nutricao(760, prot=36),
                       ("frango", "ovo"): nutricao(600, prot=42)})
    modelo = Modelo(proposta("frango", "bacon"), proposta("frango", "ovo"))
    r, eventos = rodar(tmp_path, calculo, modelo, limites(max_calories=650, min_protein_g=40))
    assert r.state == "ready" and r.attempt == 2
    historico = modelo.dados[1][0]["tentativas"][0]
    assert historico["nutricao"]["calorias"] == 760 and "calorias 760" in historico["fora_do_limite"][0]
    assert modelo.dados[1][0]["pedido_base"]["nutricao"]["calorias"] == 520  # a referência calculada vai ao modelo
    assert any("Conferi:" in e and "Não bateu" in e and "calorias 760" in e for e in eventos)


def test_tres_tentativas_sem_sucesso_pede_que_o_cliente_monte(tmp_path):
    calculo = Calculo({("frango",): nutricao(520, prot=20)}, padrao=nutricao(520, prot=20))
    modelo = Modelo(proposta("frango", "ovo"), proposta("frango", "bacon"), proposta("bife"))
    r, _ = rodar(tmp_path, calculo, modelo, limites(min_protein_g=60))
    assert r.state == "failed" and "3 tentativas" in r.message and len(modelo.dados) == 3


def test_proposta_invalida_recebe_uma_correcao(tmp_path):
    calculo = Calculo({("frango",): nutricao(500, prot=45)}, padrao=nutricao(500, prot=45))
    invalida = {"opcoes": [{"group_id": "g1", "option_id": "nao-existe", "quantity": 1}], "quantidade": 1, "motivo": "x"}
    modelo = Modelo(invalida, proposta("frango"))
    r, _ = rodar(tmp_path, calculo, modelo, limites(min_protein_g=40))
    assert r.state == "ready" and modelo.dados[1][1] and "inexistente" in modelo.dados[1][1]


def test_opcao_que_o_cliente_evita_nunca_e_aceita(tmp_path):
    perfil = UserProfile(id="u", dislikes=["camarão"])
    calculo = Calculo({}, padrao=nutricao(500, prot=45))
    modelo = Modelo(proposta("camarao"), proposta("frango"))
    r, _ = rodar(tmp_path, calculo, modelo, limites(min_protein_g=40), perfil=perfil)
    assert r.state == "ready" and "evita" in modelo.dados[1][1] and r.options[0].option_id == "frango"
    assert ("camarao",) not in calculo.chamadas


def test_pedido_base_pula_o_que_o_cliente_evita():
    base = montagem.pedido_base(prato(), ["frango"])
    assert [o.option_id for o in base] == ["camarao"]  # o mais barato que sobra


def test_sem_nutricao_calculada_nao_inventa(tmp_path):
    r, _ = rodar(tmp_path, Calculo({}, padrao=NutritionResult(state="error")), Modelo(proposta("frango")), limites(max_calories=600))
    assert r.state == "failed" and "Monte o seu" in r.message


def test_quantidade_multiplica_preco_e_nutricao(tmp_path):
    calculo = Calculo({}, padrao=nutricao(300, prot=30))
    r, _ = rodar(tmp_path, calculo, Modelo(proposta("frango", quantidade=2)), limites(min_protein_g=55, max_calories=650))
    assert r.state == "ready" and r.quantity == 2


def test_alvo_pelo_nome_pela_posicao_ou_o_primeiro():
    recs = [Recommendation.model_construct(candidate=candidato(item_id=str(i), name=n)) for i, n in
            enumerate(["Bolo de cenoura", "Marmita Fit", "Pizza"])]
    assert _alvo_da_montagem(recs, "monte a marmita fit").item_id == "1"
    assert _alvo_da_montagem(recs, "monta o terceiro").item_id == "2"
    assert _alvo_da_montagem(recs, "monta pra mim").item_id == "0"
    assert _alvo_da_montagem(recs, "monta pra mim", so_se_citado=True) is None
    assert _alvo_da_montagem(recs, "pegue a pizza grande", so_se_citado=True).item_id == "2"


def test_limites_do_pedido_anterior_valem_para_o_que_nao_foi_repetido():
    alvo = candidato(item_id="1")
    anterior = Assembly(candidate=alvo, limits=limites(preco=4000, max_calories=700))
    sessao = Session.model_construct(assembly=anterior)
    intent = MealIntent(nutrition_preferences=NutritionPreferences(min_protein_g=40))
    r = _limites_da_montagem(intent, sessao, alvo)
    assert r.max_price_cents == 4000 and r.nutrition.max_calories == 700 and r.nutrition.min_protein_g == 40
    outro = _limites_da_montagem(intent, sessao, candidato(item_id="2"))
    assert outro.max_price_cents is None and outro.nutrition.max_calories is None


# ---------- pelo chat, de ponta a ponta (catálogo de demonstração, modelo e cálculo trocados por dublês) ----------

def test_chat_monta_o_pedido_em_segundo_plano_e_a_ui_acompanha(tmp_path, monkeypatch):
    import time
    from fastapi.testclient import TestClient
    from app.core.config import Settings, get_settings
    import app.main as main
    from app.api.endpoints import macro

    cfg = Settings(_env_file=None, database_path=tmp_path / "m.sqlite3", ifood_mode="mock", intent_llm_enabled=False,
                   openrouter_api_key="", openai_api_key="", calorias_base_path=tmp_path / "n.json")
    monkeypatch.setattr(main, "get_settings", lambda: cfg)
    app = main.create_app()
    app.dependency_overrides[get_settings] = lambda: cfg

    async def propor_falso(settings, dados, erro=None):
        escolhas = [{"group_id": g["group_id"], "option_id": g["opcoes"][0]["option_id"], "quantity": 1}
                    for g in dados["grupos"] if g["min_selections"] > 0]
        return {"opcoes": escolhas, "quantidade": 1, "motivo": "escolhi o básico"}

    async def calcular_falso(selecionado, settings):
        return nutricao(500)

    monkeypatch.setattr(montagem, "propor", propor_falso)
    monkeypatch.setattr(macro, "estimate_nutrition", calcular_falso)
    with TestClient(app) as client:
        client.get("/api/session")
        client.put("/api/session/address", json={"address_id": "demo-address"})
        assert client.post("/api/chat", json={"text": "quero uma pizza", "message_id": "a1"}).json()["recommendations"]

        async def intent(*a, **k):
            return MealIntent(montar_pedido=True, nutrition_preferences=NutritionPreferences(max_calories=900))
        monkeypatch.setattr(macro, "interpret_intent", intent)
        sessao = client.post("/api/chat", json={"text": "monte o primeiro pedido com até 900 kcal", "message_id": "a2"}).json()
        assert sessao["last_chat_action"] == "assembly" and sessao["assembly"]["state"] == "running"
        assert sessao["assembly"]["limits"]["nutrition"]["max_calories"] == 900
        for _ in range(50):
            sessao = client.get("/api/assembly").json()
            if sessao["assembly"]["state"] != "running":
                break
            time.sleep(0.1)
        a = sessao["assembly"]
        assert a["state"] == "ready", a["message"]
        assert a["events"] and a["candidate"]["item_id"] and a["nutrition"]["calories"] == 500
        assert sessao["messages"][-1]["role"] == "assistant"
        # o cliente segue pelo fluxo normal: a seleção usa as opções que o assistente montou
        escolhida = client.put("/api/selection", json={"merchant_id": a["candidate"]["merchant_id"],
                                                       "item_id": a["candidate"]["item_id"], "quantity": a["quantity"],
                                                       "options": a["options"]})
        assert escolhida.status_code == 200 and escolhida.json()["assembly"] is None


def test_regras_marcam_montar_pedido_quando_o_modelo_da_interpretacao_falha():
    from app.schemas.macro import MealRequest
    from app.services.meal_intent import parse_intent
    for texto in ("pegue o footlong de 30cm coloque muita carne, não passe de 60 reais", "monte meu pedido", "monta pra mim",
                  "faz o pedido do primeiro"):
        assert parse_intent(MealRequest(text=texto)).montar_pedido, texto
    for texto in ("quero uma pizza", "me mostre sanduíches com muita carne", "o pedido chegou rápido"):
        assert not parse_intent(MealRequest(text=texto)).montar_pedido, texto


def test_meta_qualitativa_sem_numero_usa_a_referencia_do_motor(tmp_path):
    """"Não ter muitas calorias" (low_calorie) sem número: acima de 700 kcal conta como quebra."""
    meta = AssemblyLimits(nutrition=NutritionPreferences(goals=["low_calorie"]))
    r, eventos = rodar(tmp_path, Calculo({("frango",): nutricao(520), ("bacon", "frango"): nutricao(800)}),
                       Modelo(proposta("frango", "bacon"), proposta("frango", "ovo")), meta)
    assert any("acima do máximo de 700 kcal" in e for e in eventos)  # o bacon estourou a referência
    assert r.state == "ready" and r.attempt == 2
    pesado = Calculo({("frango",): nutricao(900)})
    r, _ = rodar(tmp_path, pesado, Modelo(proposta("frango")), AssemblyLimits(nutrition=NutritionPreferences(goals=["low_calorie"])))
    assert r.state == "impossible" and "pouco calórico" in r.message


def test_resposta_do_modelo_com_objetivo_nutricional_em_goals_nao_perde_o_resto():
    """Bug real: "low_calorie" em `goals` derrubava a resposta inteira (e o pedido de montagem junto)."""
    import json
    from app.services.llm_meal_intent import LLMIntent, sanear_objetivos
    bruto = json.dumps({"goals": ["low_calorie", "large_portion", "inventado"], "food_query": "footlong", "search_queries": [],
                        "cuisine": "", "avoid_repeats": False, "pesquisar_na_web": "", "montar_pedido": True,
                        "context_summary": "x", "inferences": [], "budget_cents": 6000,
                        "nutrition_preferences": {"goals": [], "max_calories": None}})
    r = LLMIntent.model_validate_json(sanear_objetivos(bruto))
    assert r.montar_pedido and r.budget_cents == 6000 and r.goals == ["large_portion"]
    assert r.nutrition_preferences.goals == ["low_calorie"]


def test_log_da_decisao_explica_se_monta_a_sugestao_ou_busca(caplog):
    import logging
    from app.api.endpoints.macro import _explicar_decisao
    recs = [Recommendation.model_construct(candidate=candidato(item_id=str(i), name=n)) for i, n in
            enumerate(["Imperdíveis do Subway (Footlong 30cm)", "Combo Imperdíveis do Subway (15cm)"])]
    sessao = Session.model_construct(recommendations=recs)
    from tests.nutricao_comum import settings as cfgs
    import pathlib
    cfg = cfgs(pathlib.Path("/tmp"), busca_log_conteudo=True)
    with caplog.at_level(logging.INFO, logger="app.nutricao"):
        alvo, caminho = _explicar_decisao(cfg, MealIntent(montar_pedido=True, food_query="footlong 30cm"), sessao,
                                          "monte o footlong 30cm que você me mostrou")
        assert alvo.item_id == "0" and caminho == "montar"
        alvo, caminho = _explicar_decisao(cfg, MealIntent(montar_pedido=True, food_query="pizza"), sessao, "monte uma pizza")
        assert alvo is None and caminho == "buscar_e_montar"
        _, caminho = _explicar_decisao(cfg, MealIntent(interpretation_source="rules", fallback_reason="invalid_response"),
                                       sessao, "me mostre subways")
        assert caminho == "buscar"
    texto = "\n".join(caplog.messages)
    assert "MONTAR sugestão já mostrada" in texto and "palavras da mensagem no nome do prato" in texto
    assert "BUSCAR e depois MONTAR" in texto and "caiu por: invalid_response" in texto


def test_conversa_leva_ao_modelo_os_dados_de_cada_sugestao_mostrada():
    from app.services.conversa import montar as montar_conversa, resumo_para_log, sugestoes_mostradas
    pronto = nutricao(404, prot=19, carb=44, gord=15)
    recs = [Recommendation.model_construct(candidate=candidato(item_id="a1", name="Imperdíveis do Subway (Footlong 30cm)",
                                                               price_cents=4040, description="Escolha sua proteína " * 40),
                                           nutrition=pronto),
            Recommendation.model_construct(candidate=candidato(item_id="a2", name="Combo"), nutrition=NutritionResult())]
    s = sugestoes_mostradas(Session.model_construct(recommendations=recs))
    assert s[0]["id"] == "a1" and s[0]["preco_reais"] == 40.4 and len(s[0]["descricao"]) <= 240
    assert s[0]["nutricao"] == {"calorias": 404, "proteina_g": 19, "carboidrato_g": 44, "gordura_g": 15}
    assert "nutricao" not in s[1]  # sem cálculo pronto não inventa
    conversa = montar_conversa(Session.model_construct(recommendations=recs, messages=[], request_intent=None),
                               settings(__import__("pathlib").Path("/tmp")))
    assert resumo_para_log(conversa)["shown_count"] == 2


def test_alvo_escolhido_pelo_modelo_vale_mais_que_o_casamento_de_palavras(caplog):
    import logging, pathlib
    from app.api.endpoints.macro import _explicar_decisao
    from tests.nutricao_comum import settings as cfgs
    recs = [Recommendation.model_construct(candidate=candidato(item_id=i, name=n)) for i, n in
            [("a1", "Imperdíveis do Subway (Footlong 30cm)"), ("a2", "Combo Imperdíveis do Subway (Footlong 30cm)")]]
    sessao = Session.model_construct(recommendations=recs)
    cfg = cfgs(pathlib.Path("/tmp"), busca_log_conteudo=True)
    with caplog.at_level(logging.INFO, logger="app.nutricao"):
        alvo, caminho = _explicar_decisao(cfg, MealIntent(montar_pedido=True, alvo_item_id="a2", food_query="footlong",
                                                          motivo_da_decisao="quer o combo"), sessao, "monte o footlong")
        assert alvo.item_id == "a2" and caminho == "montar"  # as palavras sozinhas escolheriam a1
        alvo, _ = _explicar_decisao(cfg, MealIntent(montar_pedido=True, alvo_item_id="inventado", food_query="footlong"),
                                    sessao, "monte o footlong")
        assert alvo.item_id == "a1"  # id fora das sugestões: volta ao casamento de palavras
    texto = "\n".join(caplog.messages)
    assert "o modelo escolheu este alvo" in texto and "quer o combo" in texto and "não está nas sugestões" in texto


def test_previa_de_nutricao_nao_escolhe_o_prato(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from app.core.config import Settings, get_settings
    import app.main as main
    from app.api.endpoints import macro

    cfg = Settings(_env_file=None, database_path=tmp_path / "p.sqlite3", ifood_mode="mock", intent_llm_enabled=False,
                   openrouter_api_key="", openai_api_key="", calorias_base_path=tmp_path / "n.json")
    monkeypatch.setattr(main, "get_settings", lambda: cfg)
    app = main.create_app()
    app.dependency_overrides[get_settings] = lambda: cfg
    chamadas = []

    async def estimar(selecionado, settings, aguardar=True):
        chamadas.append(aguardar)
        return nutricao(610, prot=33)

    monkeypatch.setattr(macro, "estimate_selected", estimar)
    with TestClient(app) as client:
        client.get("/api/session")
        client.put("/api/session/address", json={"address_id": "demo-address"})
        item = client.post("/api/chat", json={"text": "quero uma pizza", "message_id": "p1"}).json()["recommendations"][0]["candidate"]
        detalhe = client.get(f"/api/items/{item['merchant_id']}/{item['item_id']}").json()
        obrigatorias = [{"group_id": g["id"], "option_id": g["options"][0]["id"], "quantity": 1}
                        for g in detalhe["option_groups"] if g["min_selections"] > 0]
        corpo = {"merchant_id": item["merchant_id"], "item_id": item["item_id"], "quantity": 2, "options": obrigatorias}
        antes = client.get("/api/session").json()
        r = client.post("/api/selection/preview?aguardar=false", json=corpo)
        assert r.status_code == 200, r.text
        assert r.json()["nutrition"]["calories"] == 610 and r.json()["quantity"] == 2 and chamadas == [False]
        depois = client.get("/api/session").json()
        assert depois["selected"] is None and depois == antes  # nada foi escolhido nem gravado na sessão
        invalido = client.post("/api/selection/preview", json={**corpo, "options": []})
        assert invalido.status_code == 422 or not obrigatorias


def test_a_combinacao_so_e_revelada_depois_de_conferir_os_nutrientes(tmp_path):
    """Nenhum evento cita os complementos da proposta antes de o cálculo e a conferência terminarem."""
    eventos, vistos_no_calculo = [], []

    async def calculo(selecionado):
        if len(selecionado.options) > 1:  # a proposta do modelo (o base tem só o obrigatório)
            vistos_no_calculo.append(list(eventos))
        return nutricao(600, prot=42)

    r = asyncio.run(montagem.montar(settings(tmp_path), prato(), limites(max_calories=650, min_protein_g=40),
                                    UserProfile(id="u"), [], eventos.append, calculo,
                                    propor_fn=Modelo(proposta("frango", "ovo"))))
    assert r.state == "ready" and vistos_no_calculo
    antes = " ".join(vistos_no_calculo[0])
    assert "Ovo" not in antes and "Frango" not in antes.replace("Frango grelhado)", "")  # só o base aparece (citado no resumo)
    depois = [e for e in eventos if e.startswith("Conferi:")]
    assert depois and "Ovo" in depois[0] and "kcal" in depois[0] and "Bateu todos os limites" in depois[0]


def test_montagem_pronta_sempre_traz_a_nutricao_conferida(tmp_path):
    calculo = Calculo({("frango",): nutricao(520, prot=45)}, padrao=nutricao(520, prot=45))
    r, _ = rodar(tmp_path, calculo, Modelo(proposta("frango")), limites(min_protein_g=40))
    assert r.state == "ready" and r.nutrition is not None and r.nutrition.state == "ready"
    with pytest.raises(AssertionError):
        montagem._pronto(montagem.select(prato(), montagem.SelectionInput(item_id="i1", merchant_id="m1", quantity=1,
                                                                          options=[montagem.SelectedOption(group_id="g1", option_id="frango", quantity=1)])),
                         NutritionResult(state="pending"), 1)
