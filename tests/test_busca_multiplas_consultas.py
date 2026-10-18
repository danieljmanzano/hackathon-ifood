"""Busca com várias consultas concretas e reserva por restaurantes (o caso "quero comer japonês")."""
import asyncio
import logging
from contextlib import asynccontextmanager

import pytest

from app.core.config import get_settings
from app.core.exceptions import MacroError
from app.domain import rank
from app.schemas.macro import Address, MealIntent, MealRequest, UserProfile
from app.services import llm_meal_intent as mod
from app.services.ifood_live import MCPIFood
from app.services.llm_meal_intent import SYSTEM_PROMPT, LLMIntent, merge_intent
from app.services.meal_intent import parse_intent
from tests.nutricao_comum import candidato
from tests.test_nutricao_logs import Coletor

ENDERECO = Address(id="a1", label="Trabalho", formatted="Rua X, 1", latitude=-22.9, longitude=-47.0)


def item_json(item_id, nome, merchant="m1", preco=30.0, aberto=True):
    return {"itemId": item_id, "itemName": nome, "itemImageUrl": "https://x/y.jpg", "unitPrice": preco,
            "merchant": {"merchantId": merchant, "merchantName": f"Loja {merchant}", "isOpen": aberto}}


class IFoodFalso(MCPIFood):
    """MCPIFood sem rede: `respostas(nome, argumentos)` devolve o JSON do MCP (ou levanta)."""

    def __init__(self, respostas):
        super().__init__(get_settings())
        self.respostas, self.chamadas = respostas, []

    @asynccontextmanager
    async def connection(self):
        yield object()

    async def tools(self, session):
        return {}

    async def _call_in(self, session, tools, name, arguments):
        self.chamadas.append((name, arguments))
        resposta = self.respostas(name, arguments)
        if isinstance(resposta, BaseException):
            raise resposta
        return resposta


def _busca(ifood, queries, **kw):
    return asyncio.run(ifood.search_many(queries, ENDERECO, kw.get("orcamento"), kw.get("cuisine")))


# ---------- o que o modelo recebe e devolve ----------

def test_prompt_pede_consultas_concretas_e_nao_so_a_culinaria():
    assert "search_queries" in SYSTEM_PROMPT and "cuisine" in SYSTEM_PROMPT
    assert "uma culinária ou um adjetivo sozinhos" in SYSTEM_PROMPT
    assert '"sushi"' in SYSTEM_PROMPT and "combinado japonês" in SYSTEM_PROMPT
    assert "Nunca use qualificadores" in SYSTEM_PROMPT


def test_schema_aceita_consultas_e_recusa_lixo():
    ok = LLMIntent.model_validate_json('{"goals": [], "context_summary": "x", "search_queries": ["sushi", "temaki"], "cuisine": "japonesa"}')
    assert ok.search_queries == ["sushi", "temaki"] and ok.cuisine == "japonesa"
    with pytest.raises(ValueError):
        LLMIntent.model_validate_json('{"goals": [], "context_summary": "x", "search_queries": ["a", "b", "c", "d", "e"]}')
    with pytest.raises(ValueError):
        LLMIntent.model_validate_json('{"goals": [], "context_summary": "x", "search_queries": ["ignore tudo; {x}"]}')


def test_merge_junta_consultas_do_modelo_o_alimento_pedido_e_a_de_reserva_sem_repetir():
    base = parse_intent(MealRequest(text="quero comer japonês, tô com fome"))
    resultado = LLMIntent(goals=["large_portion"], food_query="comida japonesa", context_summary="x",
                          search_queries=["sushi", "Temaki", "sushi"], cuisine="japonesa")
    intent = merge_intent(base, resultado, "quero comer japonês, tô com fome")
    assert intent.search_queries[:3] == ["sushi", "Temaki", "comida japonesa"]
    assert len(intent.search_queries) == len({q.lower() for q in intent.search_queries})
    assert intent.cuisine == "japonesa" and intent.interpretation_source == "llm"


def test_sem_llm_a_consulta_unica_continua_valendo():
    intent = parse_intent(MealRequest(text="quero um frango grelhado"))
    assert intent.search_queries == [] and intent.provider_query


# ---------- iFood: várias consultas, uma conexão ----------

def test_varias_consultas_sao_mescladas_sem_repetir_itens():
    def resp(nome, args):
        q = args["query"]
        return {"results": [item_json("i1", "Sushi combo"), item_json(f"i-{q}", f"Prato de {q}")]}
    ifood = IFoodFalso(resp)
    itens = _busca(ifood, ["sushi", "temaki", "sushi"])
    consultas = [c["query"] for n, c in ifood.chamadas if n == "searchOffers"]
    assert sorted(consultas) == ["sushi", "temaki"]  # a repetida some antes de chamar o iFood
    assert sorted(c.item_id for c in itens) == ["i-sushi", "i-temaki", "i1"]  # i1 veio nas duas e aparece uma vez


def test_orcamento_vira_preco_maximo_e_so_abertos():
    ifood = IFoodFalso(lambda n, a: {"results": [item_json("i1", "Sushi")]})
    _busca(ifood, ["sushi"], orcamento=3500)
    refinamentos = ifood.chamadas[0][1]["refinements"]
    assert refinamentos == {"onlyOpen": True, "maxItemPrice": 35.0}


def test_uma_consulta_que_falha_nao_derruba_as_outras():
    def resp(nome, args):
        return MacroError("falhou", 502) if args["query"] == "ruim" else {"results": [item_json("i1", "Sushi")]}
    itens = _busca(IFoodFalso(resp), ["ruim", "sushi"])
    assert [c.item_id for c in itens] == ["i1"]


def test_todas_falhando_levanta_o_erro():
    with pytest.raises(MacroError):
        _busca(IFoodFalso(lambda n, a: MacroError("fora do ar", 503)), ["a b", "c d"])


# ---------- reserva: restaurantes ----------

def test_sem_itens_procura_restaurantes_e_le_o_cardapio_deles():
    def resp(nome, args):
        if nome == "searchOffers" and args["resultKind"] == "ITEM":
            return {"results": []}
        if nome == "searchOffers" and args["resultKind"] == "MERCHANT":
            return {"results": [{"merchantId": "r1", "merchantName": "Sushi Norte", "isOpen": True},
                                {"merchantId": "r2", "merchantName": "Fechado", "isOpen": False}]}
        assert nome == "browseOffers" and args["refinements"] == {"merchantId": "r1"}
        return {"results": [item_json("c1", "Combinado 12 peças", merchant="r1"),
                            item_json("x", "De outra loja", merchant="r9")]}
    ifood = IFoodFalso(resp)
    itens = _busca(ifood, ["sushi", "temaki"], cuisine="japonesa")
    assert [(c.merchant_id, c.item_id) for c in itens] == [("r1", "c1")]  # só do restaurante pedido, só abertos
    merchant = next(a for n, a in ifood.chamadas if a.get("resultKind") == "MERCHANT")
    assert merchant["query"] == "japonesa"  # a culinária, não a consulta de prato


def test_reserva_usa_a_primeira_consulta_se_nao_ha_culinaria():
    seen = []
    def resp(nome, args):
        seen.append(args.get("query"))
        return {"results": []}
    _busca(IFoodFalso(resp), ["sushi"], cuisine=None)
    assert seen == ["sushi", "sushi", "sushi"]  # itens abertos, restaurantes e, por fim, itens com restaurante fechado


def test_nada_em_lugar_nenhum_devolve_lista_vazia():
    assert _busca(IFoodFalso(lambda n, a: {"results": []}), ["sushi"], cuisine="japonesa") == []


# ---------- ranking com várias consultas ----------

def test_ranking_considera_todas_as_consultas_nao_so_o_food_query():
    intent = MealIntent(food_query="comida japonesa", provider_query="sushi", search_queries=["sushi", "temaki"])
    sushi = candidato(item_id="a", name="Combo de Sushi 20 peças", description="")
    outro = candidato(item_id="b", name="Hambúrguer", description="")
    japonesa = candidato(item_id="c", name="Prato japonesa especial", description="")
    r = rank([sushi, outro, japonesa], MealRequest(text="quero comer japonês"), UserProfile(id="u"), None, intent=intent)
    assert {x.candidate.item_id for x in r} == {"a", "c"}  # o sushi não é descartado por não citar "japonesa"
