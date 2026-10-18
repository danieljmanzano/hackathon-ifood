"""Mesclado com o trabalho do Kenzo: nenhum texto do usuário nos logs da busca, a menos que BUSCA_LOG_CONTEUDO."""
import asyncio
import json
import logging
import time
from types import SimpleNamespace

import httpx
import pytest
from pydantic import SecretStr

from app.schemas.macro import MealIntent, MealRequest, UserProfile
from app.services import busca_agente, gemini, llm_texto, openai_client, openrouter
from app.services.ifood_live import MCPIFood
from tests.nutricao_comum import candidato, settings
from tests.test_busca_agente import LLM, FECHADO, Provedor, plano
from tests.test_busca_multiplas_consultas import ENDERECO, IFoodFalso, item_json
from tests.test_llm_texto import OA_OK, OR_FALHA, _capturar, _linhas, _rodar, _s
from tests.test_nutricao_resiliencia import _com_respostas, _ok_openrouter

SEGREDO = "XABLAU-PRIVADO"


def _planejador(monkeypatch, tmp_path, **cfg):
    coletor, restaurar = _capturar()
    monkeypatch.setattr(busca_agente, "chat_completion", LLM(plano(search_queries=[SEGREDO, "lanche"],
                                                                    diagnostico=f"o usuário pediu {SEGREDO}")))
    s = settings(tmp_path, **cfg)
    intent = MealIntent(provider_query="x", search_queries=["sushi"], cuisine="japonesa")
    sessao = SimpleNamespace(profile=UserProfile(id="u"), address=ENDERECO, mode="live", recent_recommendations=[])
    logging.getLogger("app.busca").addHandler(coletor); logging.getLogger("app.busca").setLevel(logging.DEBUG)
    try:
        asyncio.run(busca_agente.buscar(MealRequest(text=f"quero {SEGREDO}"), sessao, Provedor([FECHADO()]), s, intent,
                                        None, time.monotonic()))
    finally:
        logging.getLogger("app.busca").removeHandler(coletor)
        restaurar()
    return _linhas(coletor)


def test_laco_da_busca_loga_so_contagens_por_padrao(monkeypatch, tmp_path):
    texto = _planejador(monkeypatch, tmp_path)
    assert "search.replan" in texto and "new_query_count" in texto and "catalog.completed" in texto
    assert SEGREDO not in texto and "japonesa" not in texto and "sushi" not in texto


def test_laco_da_busca_mostra_o_conteudo_com_a_chave_ligada(monkeypatch, tmp_path):
    texto = _planejador(monkeypatch, tmp_path, busca_log_conteudo=True)
    assert "consultas ao iFood ['sushi']" in texto and SEGREDO in texto  # consultas e diagnóstico do planejador


def test_planejador_pede_ao_fallback_para_nao_registrar_conteudo(monkeypatch, tmp_path):
    visto = {}

    async def falso(messages, **kw):
        visto.update(kw)
        return json.dumps(plano(), ensure_ascii=False)
    monkeypatch.setattr(busca_agente, "chat_completion", falso)
    asyncio.run(busca_agente._replanejar(settings(tmp_path), "x", {}, None, "nenhum", [], 5))
    assert visto["log_content"] is False
    asyncio.run(busca_agente._replanejar(settings(tmp_path, busca_log_conteudo=True), "x", {}, None, "nenhum", [], 5))
    assert visto["log_content"] is True


def test_resposta_da_reserva_nao_e_registrada_quando_log_content_e_falso(tmp_path):
    coletor, restaurar = _capturar()
    try:
        with __import__("unittest.mock").mock.patch.object(llm_texto, "chat_completion", OR_FALHA()), \
             __import__("unittest.mock").mock.patch.object(
                 llm_texto, "responder", __import__("unittest.mock").mock.AsyncMock(return_value=(f"resposta {SEGREDO}", []))):
            asyncio.run(llm_texto.chat_completion_fallback([{"role": "user", "content": "oi"}], settings=_s(tmp_path),
                                                           log_content=False))
    finally:
        restaurar()
    texto = _linhas(coletor)
    assert "RESERVA respondeu: openai" in texto and SEGREDO not in texto and "resposta da reserva" not in texto


def test_openrouter_reserva_respeita_log_content(tmp_path):
    for log_content, esperado in ((False, False), (True, True)):
        coletor, restaurar = _capturar()
        patcher, _ = _com_respostas(openrouter, [httpx.Response(429), _ok_openrouter(f"resposta {SEGREDO}")])
        try:
            with patcher:
                asyncio.run(openrouter.chat_completion([{"role": "user", "content": "x"}], log_content=log_content,
                                                       settings=settings(tmp_path)))
        finally:
            restaurar()
        assert (SEGREDO in _linhas(coletor)) is esperado


def test_erro_do_gpt_nao_expoe_o_corpo_quando_log_content_e_falso(tmp_path):
    patcher, _ = _com_respostas(openai_client, [httpx.Response(400, text=f"eco do pedido {SEGREDO}")])
    with patcher:
        with pytest.raises(Exception) as erro:
            asyncio.run(openai_client.responder("json", log_content=False, settings=_s(tmp_path)))
    assert SEGREDO not in str(erro.value) and "400" in str(erro.value)


def test_consultas_do_ifood_ficam_ocultas_nos_logs_por_padrao(tmp_path):
    for conteudo, esperado in ((False, False), (True, True)):
        coletor, restaurar = _capturar()
        ifood = IFoodFalso(lambda n, a: {"results": [item_json("i1", "Prato")]})
        ifood.settings = settings(tmp_path, busca_log_conteudo=conteudo)
        try:
            asyncio.run(ifood.search_many([SEGREDO], ENDERECO, None))
        finally:
            restaurar()
        assert (SEGREDO in _linhas(coletor)) is esperado


def test_a_interpretacao_da_busca_pede_para_nao_registrar_conteudo(monkeypatch):
    from app.services import llm_meal_intent as mod
    visto = {}

    async def falso(messages, **kw):
        visto.update(kw)
        return '{"goals": [], "context_summary": "x"}'
    monkeypatch.setattr(mod, "chat_completion", falso)
    mod._cache.clear()
    asyncio.run(mod.interpret_intent(MealRequest(text="quero algo"), settings(__import__("pathlib").Path("."))))
    assert visto["log_content"] is False and visto["prazo_primeiro"] == 9
