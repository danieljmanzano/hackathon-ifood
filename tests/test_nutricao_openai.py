"""Modo --llm openai: cliente HTTP, troca de provedor no pipeline e CLI."""
import asyncio
import json
from unittest.mock import AsyncMock, patch

import httpx
from pydantic import SecretStr

from app import run
from app.core.exceptions import AppError
from app.services import openai_client
from app.services import llm_texto
from app.services.nutrition.etapas import web
from app.services.nutrition.etapas.web import buscar_na_web
from tests.nutricao_comum import candidato, settings
from tests.test_nutricao_pipeline import rodar, info_base, leitura
from tests.test_nutricao_resiliencia import _com_respostas

MENSAGEM = {"type": "message", "content": [{"type": "output_text", "text": '{"ok": true}', "annotations": [
    {"type": "url_citation", "url": "https://www.site.com.br/tabela"}]}]}
BUSCA = {"type": "web_search_call", "action": {"sources": [{"url": "https://outro.com/x"}]}}


def _s(tmp_path, **extra):
    return settings(tmp_path, nutrition_provider="openai", openai_api_key=SecretStr("sk"), **extra)


def _responder(tmp_path, respostas, **kw):
    patcher, chamadas = _com_respostas(openai_client, respostas)
    with patcher, patch.object(openai_client.asyncio, "sleep", AsyncMock()):
        try:
            return asyncio.run(openai_client.responder("pedido JSON", settings=_s(tmp_path), **kw)), chamadas
        except AppError as e:
            return e, chamadas


def test_responder_extrai_texto_e_fontes(tmp_path):
    (texto, fontes), chamadas = _responder(tmp_path, [httpx.Response(200, json={"output": [BUSCA, MENSAGEM]})], web=True)
    assert json.loads(texto) == {"ok": True}
    assert fontes == ["https://outro.com/x", "https://www.site.com.br/tabela"]
    corpo = json.loads(chamadas[0].content)
    assert corpo["tools"] == [{"type": "web_search"}]
    assert "text" not in corpo  # a OpenAI recusa json_object junto com web_search
    assert chamadas[0].headers["authorization"] == "Bearer sk"


def test_web_com_schema_usa_json_schema_estrito(tmp_path):
    schema = {"type": "object", "properties": {"a": {"type": "string"}, "itens": {
        "type": "array", "items": {"type": "object", "properties": {"n": {"type": "number"}}}}}}
    _, chamadas = _responder(tmp_path, [httpx.Response(200, json={"output_text": "{}"})], web=True, schema=schema)
    formato = json.loads(chamadas[0].content)["text"]["format"]
    assert formato["type"] == "json_schema" and formato["strict"] is True
    assert formato["schema"]["additionalProperties"] is False and formato["schema"]["required"] == ["a", "itens"]
    item = formato["schema"]["properties"]["itens"]["items"]
    assert item["additionalProperties"] is False and item["required"] == ["n"]
    assert "additionalProperties" not in schema  # o schema original não é alterado


def test_sem_web_continua_em_json_object(tmp_path):
    _, chamadas = _responder(tmp_path, [httpx.Response(200, json={"output_text": "{}"})])
    assert json.loads(chamadas[0].content)["text"]["format"]["type"] == "json_object"


def test_responder_sem_web_nao_envia_ferramenta(tmp_path):
    _, chamadas = _responder(tmp_path, [httpx.Response(200, json={"output_text": "{}"})])
    assert "tools" not in json.loads(chamadas[0].content)


def test_responder_repete_em_429_e_depois_responde(tmp_path):
    (texto, _), chamadas = _responder(tmp_path, [httpx.Response(429), httpx.Response(200, json={"output_text": "{}"})])
    assert texto == "{}" and len(chamadas) == 2


def test_responder_chave_invalida_falha_na_hora_e_esgotar_tentativas_tambem(tmp_path):
    erro, chamadas = _responder(tmp_path, [httpx.Response(401, text="chave")])
    assert isinstance(erro, AppError) and "401" in str(erro) and len(chamadas) == 1
    erro, chamadas = _responder(tmp_path, [httpx.Response(503)])
    assert "indisponível" in str(erro) and len(chamadas) == 3


def test_sem_chave_openai_erro_claro(tmp_path):
    s = settings(tmp_path, nutrition_provider="openai", openai_api_key=SecretStr(""))
    try:
        asyncio.run(openai_client.responder("x", settings=s))
    except AppError as e:
        assert "OPENAI_API_KEY" in str(e)


def test_perguntar_json_usa_o_provedor_escolhido(tmp_path):
    from app.services.nutrition.etapas import llm
    schema = {"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]}
    with patch.object(llm_texto, "responder", AsyncMock(return_value=('{"ok": true}', []))) as oa, \
         patch.object(llm_texto, "chat_completion", AsyncMock(return_value='{"ok": true}')) as orr:
        assert asyncio.run(llm.perguntar_json(_s(tmp_path), "sys", "p", schema)) == {"ok": True}
        oa.assert_awaited_once(); orr.assert_not_called()
    with patch.object(llm_texto, "responder", AsyncMock()) as oa, \
         patch.object(llm_texto, "chat_completion", AsyncMock(return_value='{"ok": true}')) as orr:
        asyncio.run(llm.perguntar_json(settings(tmp_path), "sys", "p", schema))
        orr.assert_awaited_once(); oa.assert_not_called()


def test_web_usa_openai_e_aplica_a_mesma_checagem_de_fonte(tmp_path):
    from tests.test_nutricao_web import resposta_json
    resposta = resposta_json(fonte_url="https://www.site.com.br/tabela")
    with patch.object(web, "responder", AsyncMock(return_value=(json.dumps(resposta), ["https://site.com.br/outra"]))), \
         patch.object(web, "search_web", AsyncMock()) as gemini, \
         patch.object(web, "perguntar_json", AsyncMock(return_value={"corresponde": True, "motivo": "m"})):
        info = asyncio.run(buscar_na_web(_s(tmp_path), candidato(), None))
        assert info.method == "web" and info.macros.kcal == 1800
        gemini.assert_not_called()
    with patch.object(web, "responder", AsyncMock(return_value=(json.dumps(resposta), ["https://fora.com/x"]))), \
         patch.object(web, "perguntar_json", AsyncMock(return_value={"corresponde": True, "motivo": "m"})):
        assert asyncio.run(buscar_na_web(_s(tmp_path), candidato(), None)) is None  # fonte não consultada


def test_openai_recebe_a_foto_na_pesquisa_do_prato(tmp_path):
    from tests.test_nutricao_web import FOTO, PRATO, resposta_json
    resposta = resposta_json(**PRATO)
    with patch.object(web, "responder", AsyncMock(return_value=(json.dumps(resposta), ["https://tabelanutri.com.br/x"]))) as r:
        achado = asyncio.run(buscar_na_web(_s(tmp_path), candidato(), None, FOTO))
    assert achado.fonte == "web" and r.call_args.kwargs["imagem"] == FOTO and r.call_args.kwargs["web"] is True


def test_cliente_openai_monta_o_corpo_com_imagem_e_web(tmp_path):
    import base64
    _, chamadas = _responder(tmp_path, [httpx.Response(200, json={"output_text": "{}"})], web=True,
                             imagem=(b"FOTO", "image/jpeg"))
    corpo = json.loads(chamadas[0].content)
    conteudo = corpo["input"][0]["content"]
    assert corpo["input"][0]["role"] == "user" and corpo["tools"] == [{"type": "web_search"}]
    assert conteudo[0]["type"] == "input_text" and conteudo[1]["type"] == "input_image"
    assert conteudo[1]["image_url"] == "data:image/jpeg;base64," + base64.b64encode(b"FOTO").decode()


def test_pipeline_no_modo_openai_exige_chave_openai_para_texto_e_web(tmp_path):
    s = settings(tmp_path, nutrition_provider="openai", openai_api_key=SecretStr(""), openrouter_api_key="k",
                 gemini_api_key="k", llm_fallback=False)
    r, m = rodar(s, b=leitura("gemini", 800), imagem=(b"x", "image/jpeg"), casados=None)
    assert r.state == "ready"  # Gemini estima sozinho
    m["estimar_a"].assert_not_called(); m["consultar_bases"].assert_not_called(); m["buscar_na_web"].assert_not_called()

    s = _s(tmp_path)
    r, m = rodar(s, bases=info_base(), a=leitura("openai", 800))
    m["consultar_bases"].assert_awaited_once(); m["buscar_na_web"].assert_not_called()  # base achou: sem web


def test_cli_openai_sem_chave_recusa(capsys):
    assert run.main(["--llm", "openai", "--check"]) == 2
    assert "OPENAI_API_KEY" in capsys.readouterr().err


def test_cli_openai_com_chave_valida_e_resume(monkeypatch, capsys):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-teste")
    assert run.main(["--llm", "openai", "--check"]) == 0
    saida = capsys.readouterr().out
    assert "openai" in saida and "web_search" in saida and "Gemini" in saida


def test_cli_padrao_e_openrouter(capsys):
    assert run.main(["--check"]) == 0
    assert "openrouter" in capsys.readouterr().out
