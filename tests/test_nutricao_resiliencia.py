"""Queda dos LLMs: troca de modelo, erros de autenticação, indisponibilidade total e recuperação."""
import asyncio
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.core.exceptions import AppError
from app.services import gemini, openrouter
from app.services.nutrition import service
from tests.nutricao_comum import candidato, leitura, settings
from tests.test_nutricao_pipeline import rodar

_AsyncClient = httpx.AsyncClient


def _com_respostas(modulo, respostas):
    """Substitui o httpx do módulo por um transporte falso que devolve `respostas` em ordem."""
    chamadas = []

    def handler(request: httpx.Request) -> httpx.Response:
        chamadas.append(request)
        item = respostas[min(len(chamadas) - 1, len(respostas) - 1)]
        if isinstance(item, Exception):
            raise item
        return item

    def fabrica(**kw):
        return _AsyncClient(transport=httpx.MockTransport(handler), **kw)

    return patch.object(modulo.httpx, "AsyncClient", fabrica), chamadas


def _ok_openrouter(texto="ok"):
    return httpx.Response(200, json={"choices": [{"message": {"content": texto}}]})


def _ok_gemini(texto="ok"):
    return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": texto}]}}]})


def _openrouter(tmp_path, respostas):
    patcher, chamadas = _com_respostas(openrouter, respostas)
    with patcher:
        try:
            return asyncio.run(openrouter.chat_completion([{"role": "user", "content": "x"}],
                                                          settings=settings(tmp_path))), chamadas
        except AppError as e:
            return e, chamadas


def test_openrouter_troca_de_modelo_quando_o_primeiro_cai(tmp_path):
    texto, chamadas = _openrouter(tmp_path, [httpx.Response(429, text="limite"), _ok_openrouter("segundo")])
    assert texto == "segundo" and len(chamadas) == 2


def test_openrouter_erro_de_rede_tambem_passa_para_o_proximo(tmp_path):
    texto, chamadas = _openrouter(tmp_path, [httpx.ConnectError("sem rede"), _ok_openrouter("voltou")])
    assert texto == "voltou" and len(chamadas) == 2


def test_openrouter_chave_invalida_nao_gasta_os_outros_modelos(tmp_path):
    erro, chamadas = _openrouter(tmp_path, [httpx.Response(401, text="chave inválida")])
    assert isinstance(erro, AppError) and "401" in str(erro) and len(chamadas) == 1


def test_openrouter_todos_fora_lista_o_motivo_de_cada_modelo(tmp_path):
    erro, chamadas = _openrouter(tmp_path, [httpx.Response(503, text="fora")])
    assert isinstance(erro, AppError) and "Todos os modelos falharam" in str(erro)
    assert len(chamadas) == 4  # modelo do .env + 3 reservas


def test_openrouter_resposta_sem_conteudo_vai_para_o_proximo(tmp_path):
    texto, _ = _openrouter(tmp_path, [httpx.Response(200, json={"choices": []}), _ok_openrouter("ok")])
    assert texto == "ok"


def _gemini(tmp_path, respostas):
    patcher, chamadas = _com_respostas(gemini, respostas)
    with patcher, patch.object(gemini.asyncio, "sleep", AsyncMock()):
        try:
            return asyncio.run(gemini.generate_text("x", settings=settings(tmp_path))), chamadas
        except AppError as e:
            return e, chamadas


def test_gemini_repete_em_503_e_depois_responde(tmp_path):
    texto, chamadas = _gemini(tmp_path, [httpx.Response(503), httpx.Response(503), _ok_gemini("veio")])
    assert texto == "veio" and len(chamadas) == 3


def test_gemini_modelo_aposentado_404_pula_para_o_reserva_sem_repetir(tmp_path):
    texto, chamadas = _gemini(tmp_path, [httpx.Response(404, text="modelo removido"), _ok_gemini("reserva")])
    assert texto == "reserva" and len(chamadas) == 2


def test_gemini_chave_invalida_falha_na_hora(tmp_path):
    erro, chamadas = _gemini(tmp_path, [httpx.Response(403, text="chave")])
    assert isinstance(erro, AppError) and len(chamadas) == 1


def test_gemini_bloqueio_de_conteudo_vira_erro_claro(tmp_path):
    erro, _ = _gemini(tmp_path, [httpx.Response(200, json={"promptFeedback": {"blockReason": "SAFETY"}})])
    assert isinstance(erro, AppError) and "bloqueio" in str(erro)


def test_gemini_todos_fora(tmp_path):
    erro, chamadas = _gemini(tmp_path, [httpx.Response(503)])
    assert isinstance(erro, AppError) and "Todos os modelos falharam" in str(erro)
    assert len(chamadas) == 3 * 2  # 3 tentativas x (modelo + reserva)


# ---------- pipeline e serviço ----------

def test_openrouter_fora_gemini_assume(tmp_path):
    r, _ = rodar(settings(tmp_path), a=AppError("openrouter fora"), b=leitura("gemini", 800),
                 bases=None, web=None, imagem=(b"x", "image/jpeg"), casados=None)
    assert r.state == "ready" and r.method == "estimated"
    assert any("Apenas uma fonte" in x for x in r.assumptions)


def test_gemini_fora_openrouter_assume(tmp_path):
    r, _ = rodar(settings(tmp_path), a=leitura("openrouter", 800), b=AppError("gemini fora"),
                 imagem=(b"x", "image/jpeg"), casados=None)
    assert r.state == "ready" and r.method == "estimated"


def test_os_dois_fora_fica_indisponivel_sem_estourar(tmp_path):
    r, _ = rodar(settings(tmp_path), a=AppError("x"), b=AppError("y"), casados=None)
    assert r.state == "unavailable"


def test_queda_temporaria_nao_fica_presa_no_cache(tmp_path):
    service._cache.clear()
    s = settings(tmp_path)
    c = candidato(item_id="item-recuperacao")
    fora = service._resultado("unavailable", evidence="nenhuma fonte")
    with patch.object(service, "calcular", AsyncMock(return_value=fora)) as calc:
        assert asyncio.run(service.estimate_nutrition(c, s)).state == "unavailable"
        assert not (tmp_path / "produtos.json").exists()
        assert asyncio.run(service.estimate_nutrition(c, s)).state == "unavailable"
        assert calc.await_count == 2  # tentou de novo: o "indisponível" não foi memorizado

    from tests.test_nutricao_service import _pronto
    with patch.object(service, "calcular", AsyncMock(return_value=_pronto())):
        assert asyncio.run(service.estimate_nutrition(c, s)).state == "ready"


@pytest.mark.parametrize("erro", [asyncio.TimeoutError(), AppError("x"), KeyError("campo")])
def test_erros_do_pipeline_viram_state_error(tmp_path, erro):
    service._cache.clear()
    with patch.object(service, "calcular", AsyncMock(side_effect=erro)):
        r = asyncio.run(service.estimate_nutrition(candidato(item_id=f"item-{type(erro).__name__}"), settings(tmp_path)))
    assert r.state == "error"
