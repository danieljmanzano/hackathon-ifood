"""Fallback entre provedores de texto: se o OpenRouter falhar, usa o GPT (e vice-versa)."""
import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import SecretStr

from app.core.exceptions import AppError
from app.services import llm_texto
from app.services.llm_meal_intent import chat_completion as chat_da_busca
from app.services.llm_texto import chat_completion_fallback, ordem
from app.services.openai_client import OpenAIError
from app.services.openrouter import OpenRouterError
from tests.nutricao_comum import settings

MSGS = [{"role": "system", "content": "Seja breve."}, {"role": "user", "content": "oi"}]


def _s(tmp_path, **extra):
    return settings(tmp_path, openai_api_key=SecretStr("sk"), openrouter_api_key="k", **extra)


def _rodar(s, openrouter, openai, **kw):
    with patch.object(llm_texto, "chat_completion", openrouter) as orr, \
         patch.object(llm_texto, "responder", openai) as oa:
        try:
            return asyncio.run(chat_completion_fallback(MSGS, settings=s, **kw)), orr, oa
        except AppError as e:
            return e, orr, oa


OR_OK = lambda: AsyncMock(return_value="resposta do openrouter")
OA_OK = lambda: AsyncMock(return_value=("resposta do gpt", []))
OR_FALHA = lambda: AsyncMock(side_effect=OpenRouterError("429 sem cota"))
OA_FALHA = lambda: AsyncMock(side_effect=OpenAIError("OpenAI 500"))


def test_openrouter_funcionando_nao_gasta_o_gpt(tmp_path):
    texto, orr, oa = _rodar(_s(tmp_path), OR_OK(), OA_OK())
    assert texto == "resposta do openrouter"
    oa.assert_not_called()


def test_openrouter_falha_e_o_gpt_assume(tmp_path):
    texto, orr, oa = _rodar(_s(tmp_path), OR_FALHA(), OA_OK())
    assert texto == "resposta do gpt"
    orr.assert_awaited_once(); oa.assert_awaited_once()


def test_gpt_recebe_o_system_como_instrucoes_e_o_usuario_como_entrada(tmp_path):
    _, _, oa = _rodar(_s(tmp_path), OR_FALHA(), OA_OK(), json_mode=True)
    assert oa.call_args.args[0] == "oi"
    assert oa.call_args.kwargs["instrucoes"] == "Seja breve." and oa.call_args.kwargs["json_mode"] is True


def test_historico_com_varias_mensagens_vai_como_lista(tmp_path):
    msgs = [{"role": "system", "content": "S"}, {"role": "user", "content": "a"},
            {"role": "assistant", "content": "b"}, {"role": "user", "content": "c"}]
    with patch.object(llm_texto, "chat_completion", OR_FALHA()), patch.object(llm_texto, "responder", OA_OK()) as oa:
        asyncio.run(chat_completion_fallback(msgs, settings=_s(tmp_path)))
    assert oa.call_args.args[0] == msgs[1:] and oa.call_args.kwargs["instrucoes"] == "S"


def test_os_dois_falham_levanta_o_erro_do_preferido_que_quem_chama_ja_trata(tmp_path):
    erro, _, _ = _rodar(_s(tmp_path), OR_FALHA(), OA_FALHA())
    assert isinstance(erro, OpenRouterError) and "429" in str(erro)
    erro, _, _ = _rodar(_s(tmp_path), OR_FALHA(), OA_FALHA(), preferido="openai")
    assert isinstance(erro, OpenAIError)


def test_sem_chave_do_gpt_nao_tenta_e_devolve_o_erro_original(tmp_path):
    s = settings(tmp_path, openai_api_key=SecretStr(""), openrouter_api_key="k")
    erro, _, oa = _rodar(s, OR_FALHA(), OA_OK())
    assert isinstance(erro, OpenRouterError)
    oa.assert_not_called()


def test_fallback_desligado_nao_usa_o_gpt(tmp_path):
    erro, _, oa = _rodar(_s(tmp_path, llm_fallback=False), OR_FALHA(), OA_OK())
    assert isinstance(erro, OpenRouterError)
    oa.assert_not_called()


def test_preferido_openai_cai_para_openrouter(tmp_path):
    texto, orr, oa = _rodar(_s(tmp_path), OR_OK(), OA_FALHA(), preferido="openai")
    assert texto == "resposta do openrouter"
    oa.assert_awaited_once(); orr.assert_awaited_once()


def test_preferido_sem_chave_usa_direto_o_outro(tmp_path):
    s = settings(tmp_path, openai_api_key=SecretStr("sk"), openrouter_api_key="")
    assert ordem(s, "openrouter") == ["openai"]
    texto, orr, oa = _rodar(s, OR_OK(), OA_OK())
    assert texto == "resposta do gpt"
    orr.assert_not_called()


def test_nenhuma_chave_erro_claro(tmp_path):
    s = settings(tmp_path, openai_api_key=SecretStr(""), openrouter_api_key="")
    erro, _, _ = _rodar(s, OR_OK(), OA_OK())
    assert isinstance(erro, OpenRouterError) and "chave" in str(erro).lower()


def test_log_diz_quem_falhou_e_quem_assumiu(tmp_path):
    import logging
    from tests.test_nutricao_logs import Coletor
    coletor, logger = Coletor(), logging.getLogger("app.nutricao")
    nivel = logger.level
    logger.addHandler(coletor); logger.setLevel(logging.INFO)
    try:
        _rodar(_s(tmp_path), OR_FALHA(), OA_OK())
    finally:
        logger.removeHandler(coletor); logger.setLevel(nivel)
    texto = " ".join("\n".join(coletor.linhas).split())
    assert "llm │ openrouter falhou" in texto and "usando openai como reserva" in texto


def test_busca_e_agente_usam_a_versao_com_fallback():
    from app.agent import orchestrator
    assert chat_da_busca is chat_completion_fallback and orchestrator.chat_completion is chat_completion_fallback


def test_chave_do_pipeline_cai_para_a_do_outro_provedor_so_com_fallback(tmp_path):
    so_gpt = settings(tmp_path, nutrition_provider="openrouter", openrouter_api_key="", openai_api_key=SecretStr("sk"))
    assert so_gpt.llm_api_key == "sk"
    assert settings(tmp_path, nutrition_provider="openrouter", openrouter_api_key="",
                    openai_api_key=SecretStr("sk"), llm_fallback=False).llm_api_key == ""


# ---------- logs de "quem respondeu" ----------

import logging

from app.services import gemini, openai_client, openrouter
from tests.test_nutricao_logs import Coletor
from tests.test_nutricao_resiliencia import _com_respostas, _ok_gemini, _ok_openrouter
import httpx


def _capturar():
    coletor, logger = Coletor(), logging.getLogger("app.nutricao")
    nivel = logger.level
    logger.addHandler(coletor); logger.setLevel(logging.INFO)

    def restaurar():
        logger.removeHandler(coletor); logger.setLevel(nivel)
    return coletor, restaurar


def _linhas(coletor):
    return " ".join("\n".join(coletor.linhas).split())


def test_log_openrouter_diz_qual_modelo_de_reserva_respondeu(tmp_path):
    coletor, restaurar = _capturar()
    patcher, _ = _com_respostas(openrouter, [httpx.Response(429, text="limite"), _ok_openrouter("ok")])
    try:
        with patcher:
            asyncio.run(openrouter.chat_completion([{"role": "user", "content": "x"}], settings=settings(tmp_path)))
    finally:
        restaurar()
    s = settings(tmp_path)
    assert (f"RESERVA respondeu: {s.openrouter_fallback_models[0]} no lugar de {s.openrouter_model} "
            "(1 falha(s) antes)") in _linhas(coletor)


def test_log_openrouter_nao_fala_de_reserva_quando_o_principal_responde(tmp_path):
    coletor, restaurar = _capturar()
    patcher, _ = _com_respostas(openrouter, [_ok_openrouter("ok")])
    try:
        with patcher:
            asyncio.run(openrouter.chat_completion([{"role": "user", "content": "x"}], settings=settings(tmp_path)))
    finally:
        restaurar()
    assert "RESERVA" not in _linhas(coletor)


def test_log_gemini_reserva_e_nova_tentativa(tmp_path):
    from unittest.mock import AsyncMock, patch
    s = settings(tmp_path)
    for respostas, esperado in (
        ([httpx.Response(404), _ok_gemini()], f"RESERVA respondeu: {s.gemini_fallback_models[0]} no lugar de {s.gemini_model}"),
        ([httpx.Response(503), _ok_gemini()], f"{s.gemini_model} respondeu na tentativa 2/3"),
    ):
        coletor, restaurar = _capturar()
        patcher, _ = _com_respostas(gemini, respostas)
        try:
            with patcher, patch.object(gemini.asyncio, "sleep", AsyncMock()):
                asyncio.run(gemini.generate_text("x", settings=s))
        finally:
            restaurar()
        assert esperado in _linhas(coletor)


def test_log_openai_nova_tentativa(tmp_path):
    from unittest.mock import AsyncMock, patch
    coletor, restaurar = _capturar()
    patcher, _ = _com_respostas(openai_client, [httpx.Response(429), httpx.Response(200, json={"output_text": "{}"})])
    try:
        with patcher, patch.object(openai_client.asyncio, "sleep", AsyncMock()):
            asyncio.run(openai_client.responder("json", settings=_s(tmp_path)))
    finally:
        restaurar()
    assert "respondeu na tentativa 2/3" in _linhas(coletor)


def test_log_do_fallback_entre_provedores_diz_quem_respondeu_no_lugar_de_quem(tmp_path):
    coletor, restaurar = _capturar()
    try:
        _rodar(_s(tmp_path), OR_FALHA(), OA_OK())
    finally:
        restaurar()
    s = _s(tmp_path)
    assert f"RESERVA respondeu: openai ({s.nutrition_model}) no lugar de openrouter" in _linhas(coletor)


def test_log_mostra_o_que_a_reserva_respondeu(tmp_path):
    # OpenRouter: o segundo modelo responde
    coletor, restaurar = _capturar()
    patcher, _ = _com_respostas(openrouter, [httpx.Response(429), _ok_openrouter('{"goals": ["protein"], "food_query": "japonesa"}')])
    try:
        with patcher:
            asyncio.run(openrouter.chat_completion([{"role": "user", "content": "x"}], settings=settings(tmp_path)))
    finally:
        restaurar()
    assert 'resposta da reserva: {"goals": ["protein"], "food_query": "japonesa"}' in _linhas(coletor)

    # GPT assume pelo OpenRouter
    coletor, restaurar = _capturar()
    try:
        _rodar(_s(tmp_path), OR_FALHA(), AsyncMock(return_value=('{"ok": true}', [])))
    finally:
        restaurar()
    assert 'resposta da reserva: {"ok": true}' in _linhas(coletor)

    # resposta longa é truncada em uma linha só
    coletor, restaurar = _capturar()
    try:
        _rodar(_s(tmp_path), OR_FALHA(), AsyncMock(return_value=("linha\n" * 400, [])))
    finally:
        restaurar()
    linha = next(l for l in coletor.linhas if "resposta da reserva" in l)
    assert "\n" not in linha and linha.endswith("…")


# ---------- o principal demora demais: a reserva precisa ter tempo de rodar ----------

async def _trava(*args, **kwargs):
    await asyncio.sleep(5)
    return "tarde demais"


def test_principal_que_demora_e_cortado_e_o_gpt_assume_dentro_do_prazo(tmp_path):
    import time
    inicio = time.perf_counter()
    texto, orr, oa = _rodar(_s(tmp_path), _trava, OA_OK(), prazo_primeiro=0.05)
    assert texto == "resposta do gpt" and time.perf_counter() - inicio < 1
    oa.assert_awaited_once()


def test_log_diz_que_o_principal_estourou_o_tempo(tmp_path):
    coletor, restaurar = _capturar()
    try:
        _rodar(_s(tmp_path), _trava, OA_OK(), prazo_primeiro=0.05)
    finally:
        restaurar()
    texto = _linhas(coletor)
    assert "openrouter falhou (openrouter não respondeu em" in texto and "→ usando openai como reserva" in texto
    assert "RESERVA respondeu: openai" in texto


def test_sem_reserva_o_principal_nao_e_cortado(tmp_path):
    async def demora_um_pouco(*a, **k):
        await asyncio.sleep(0.15)
        return "ok sem pressa"
    s = settings(tmp_path, openai_api_key=SecretStr(""), openrouter_api_key="k")  # só OpenRouter
    texto, _, _ = _rodar(s, demora_um_pouco, OA_OK(), prazo_primeiro=0.05)
    assert texto == "ok sem pressa"


def test_timeout_dos_dois_levanta_o_erro_do_preferido(tmp_path):
    async def trava_openai(*a, **k):
        await asyncio.sleep(5)
    erro, _, _ = _rodar(_s(tmp_path), _trava, AsyncMock(side_effect=OpenAIError("OpenAI 500")), prazo_primeiro=0.05)
    assert isinstance(erro, OpenRouterError) and "não respondeu" in str(erro)


def test_busca_reserva_metade_do_prazo_para_a_reserva(monkeypatch):
    from app.schemas.macro import MealRequest
    visto = {}

    async def falso(messages, **kw):
        visto.update(kw)
        return '{"goals": [], "context_summary": "x"}'
    monkeypatch.setattr(mod, "chat_completion", falso)
    mod._cache.clear()
    s = settings(__import__("pathlib").Path("."), intent_llm_timeout_seconds=18)
    asyncio.run(mod.interpret_intent(MealRequest(text="quero comer algo"), s))
    assert visto["prazo_primeiro"] == 9


from app.services import llm_meal_intent as mod  # noqa: E402
