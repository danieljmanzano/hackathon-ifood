"""Logs legíveis: formato, ordem das etapas, item em cada linha e níveis."""
import asyncio
import logging
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import SecretStr

from app.core import logs
from app.core.logs import Legivel, configurar_logs, curto
from app.services.nutrition import service
from tests.nutricao_comum import candidato, leitura, settings
from tests.test_nutricao_pipeline import info_base, rodar
from tests.test_nutricao_service import _pronto


class Coletor(logging.Handler):
    def __init__(self):
        super().__init__()
        self.linhas: list[str] = []
        self.setFormatter(Legivel())

    def emit(self, record):
        self.linhas.append(self.format(record))


@pytest.fixture
def capturar():
    coletor, logger = Coletor(), logging.getLogger("app.nutricao")
    antes = logger.level
    logger.addHandler(coletor)
    logger.setLevel(logging.DEBUG)
    yield coletor.linhas
    logger.removeHandler(coletor)
    logger.setLevel(antes)


def _etapas(linhas):
    return [l.split("│")[1].strip() for l in linhas if "│" in l]


def test_formato_de_uma_linha(capturar):
    logs.iniciar_item("Pizza Margherita")
    logs.info("bases", "8 candidatos")
    linha = capturar[0]
    assert "Pizza Margherita" in linha and "│ bases " in linha and linha.endswith("8 candidatos")
    assert linha[2] == ":" and linha[5] == ":"  # HH:MM:SS


def test_aviso_e_erro_tem_simbolo_proprio(capturar):
    logs.aviso("web", "falhou")
    assert " ! " in capturar[0]


def test_curto_trunca_e_une_linhas():
    assert curto("a\n  b\n   c") == "a b c"
    assert len(curto("x" * 500, 50)) == 50 and curto("x" * 500, 50).endswith("…")
    assert "TimeoutError" in curto(asyncio.TimeoutError())


def test_pipeline_conta_a_historia_na_ordem(tmp_path, capturar):
    rodar(settings(tmp_path), bases=info_base(), a=leitura("openrouter", 500), b=leitura("imagem", 520),
          imagem=(b"x" * 2048, "image/jpeg"))
    etapas = _etapas(capturar)
    ordem = ["início", "modo", "porção", "imagem", "estimar A", "estimar B", "consenso", "gramas", "fusão",
             "validação", "RESULTADO"]
    posicoes = [etapas.index(e) for e in ordem]
    assert posicoes == sorted(posicoes), etapas
    texto = "\n".join(capturar)
    assert "400 g declarados" in texto  # porção
    assert "baixada (2 KB, image/jpeg)" in texto
    assert "vence: database" in texto and "método database" in texto


def test_toda_linha_do_pipeline_traz_o_item_inclusive_nas_tasks_paralelas(tmp_path, capturar):
    rodar(settings(tmp_path), c=candidato(name="Frango Grelhado da Casa"), a=leitura("openrouter", 500),
          b=leitura("imagem", 520), imagem=(b"x", "image/jpeg"))
    com_etapa = [l for l in capturar if "│" in l]
    assert com_etapa and all("Frango Grelhado da" in l for l in com_etapa)


def test_motivos_de_pulo_aparecem(tmp_path, capturar):
    rodar(settings(tmp_path, openrouter_api_key="", openai_api_key=SecretStr(""), calorias_busca_web=False),
          c=candidato(image_url=None), b=None)
    texto = " ".join("\n".join(capturar).split())  # ignora o alinhamento em colunas
    assert "estimar B │ pulada: sem imagem" in texto
    assert "sem chave do provedor de texto" in texto
    assert "web │ desligada" in texto
    assert "item sem foto" in texto


def test_modo_economico_explica_o_que_dispensou(tmp_path, capturar):
    rodar(settings(tmp_path, calorias_estimar_sempre=False), bases=info_base())
    assert "estimativas dispensadas" in "\n".join(capturar)


def test_falha_de_etapa_vira_aviso_de_uma_linha(tmp_path, capturar):
    from app.core.exceptions import AppError
    rodar(settings(tmp_path), a=AppError("OpenAI 400 {\n  \"error\": {\n \"message\": \"Web Search cannot be used\"}}"),
          b=leitura("imagem", 600), imagem=(b"x", "image/jpeg"))
    falha = next(l for l in capturar if "FALHOU" in l)
    assert "\n" not in falha and " ! " in falha and "Web Search cannot be used" in falha


def test_service_mostra_miss_gravacao_e_depois_hit(tmp_path, capturar):
    service._cache.clear()
    s = settings(tmp_path)
    c = candidato(item_id="item-logs")
    with patch.object(service, "calcular", AsyncMock(return_value=_pronto())):
        asyncio.run(service.estimate_nutrition(c, s))
        service._cache.clear()
        asyncio.run(service.estimate_nutrition(c, s))
    texto = "\n".join(capturar)
    assert "MISS" in texto and "gravado em" in texto and "HIT" in texto and "nada recalculado" in texto


def test_service_diz_a_causa_do_timeout(tmp_path, capturar):
    service._cache.clear()
    with patch.object(service, "calcular", AsyncMock(side_effect=asyncio.TimeoutError())):
        asyncio.run(service.estimate_nutrition(candidato(item_id="item-timeout"), settings(tmp_path)))
    assert "tempo esgotado (NUTRITION_TIMEOUT_SECONDS)" in "\n".join(capturar)


def test_nivel_off_so_mostra_problemas():
    logger = logging.getLogger("app.nutricao")
    antes = logger.level
    try:
        configurar_logs("off")
        assert not logger.isEnabledFor(logging.INFO) and logger.isEnabledFor(logging.WARNING)
        configurar_logs("detalhe")
        assert logger.isEnabledFor(logging.DEBUG)
        configurar_logs("resumo")
        assert logger.isEnabledFor(logging.INFO) and not logger.isEnabledFor(logging.DEBUG)
    finally:
        logging.getLogger("app").setLevel(antes)


def test_configurar_logs_e_idempotente():
    configurar_logs("resumo"); configurar_logs("resumo")
    assert sum(isinstance(h.formatter, Legivel) for h in logging.getLogger("app").handlers) == 1


def test_rotulo_distingue_itens_com_o_mesmo_comeco():
    a = logs.rotulo("Marmita Parmegiana de frango")
    b = logs.rotulo("Marmita Parmegiana de carne")
    assert a != b and len(a) <= logs.LARGURA_ITEM and a.endswith("frango") and b.endswith("carne")
    assert logs.rotulo("Pizza") == "Pizza"


def test_modelo_que_diz_nao_ter_informacao_nao_falha_em_silencio(capturar):
    from app.services.nutrition.etapas.estimar import leitura_de_json
    dados = {"suficiente": False, "calorias": None, "justificativa": "nome genérico, sem descrição"}
    assert leitura_de_json(dados, "openai") is None
    texto = " ".join("\n".join(capturar).split())
    assert "estimar A │ o modelo (openai) respondeu que NÃO há informação suficiente: nome genérico" in texto


# ---------- o que o modelo viu na foto ----------

def test_log_mostra_o_que_o_modelo_viu_na_foto_o_link_e_os_ingredientes(tmp_path, capturar):
    from tests.test_nutricao_pipeline import rodar
    from tests.nutricao_comum import leitura
    b = leitura("imagem", 985, peso=340, itens_na_imagem=["hambúrguer com queijo", "batata frita"])
    rodar(settings(tmp_path), c=candidato(image_url="https://cdn.ifood.com.br/items/4592.jpg"),
          b=b, imagem=(b"x" * 2048, "image/jpeg"), casados=None)
    texto = " ".join("\n".join(capturar).split())
    assert "imagem │ baixada (2 KB, image/jpeg) · abra para conferir: https://cdn.ifood.com.br/items/4592.jpg" in texto
    assert "estimar B │ viu na foto: hambúrguer com queijo; batata frita" in texto
    assert "estimar B │ ingredientes estimados: arroz 200 g, feijão 100 g" in texto


def test_log_avisa_quando_o_modelo_nao_listou_nada_visivel(tmp_path, capturar):
    from tests.test_nutricao_pipeline import rodar
    from tests.nutricao_comum import leitura
    rodar(settings(tmp_path), b=leitura("imagem", 985), imagem=(b"x", "image/jpeg"), casados=None)
    texto = " ".join("\n".join(capturar).split())
    assert "estimar B │ não listou nada visível na foto" in texto
    assert any(" ! " in l and "não listou nada visível" in l for l in capturar)


def test_estimativa_a_so_texto_nao_fala_de_foto(tmp_path, capturar):
    from tests.test_nutricao_pipeline import rodar
    from tests.nutricao_comum import leitura
    rodar(settings(tmp_path), a=leitura("openrouter", 700), casados=None)
    assert "viu na foto" not in "\n".join(capturar)


def test_leitura_guarda_os_itens_vistos_do_json_e_ignora_vazios():
    from app.services.nutrition.etapas.estimar import leitura_de_json
    dados = {"suficiente": True, "calorias": 900, "faixa_min": 800, "faixa_max": 1000, "proteina_g": 40,
             "carbo_g": 80, "gordura_g": 40, "peso_estimado_g": 350, "confianca": "media", "porcao_base": "prato",
             "justificativa": "j", "ingredientes": [], "suposicoes": [],
             "itens_visiveis_na_imagem": ["pizza ", "", "borda recheada"]}
    assert leitura_de_json(dados, "imagem").itens_na_imagem == ["pizza", "borda recheada"]
    del dados["itens_visiveis_na_imagem"]  # modelo que omitiu o campo: não quebra
    assert leitura_de_json(dados, "imagem").itens_na_imagem == []
