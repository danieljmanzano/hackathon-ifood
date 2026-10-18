"""Uma cena por aresta do pipeline_calorias_v2.dot, com todas as fontes substituídas por falsos."""
import asyncio
from contextlib import ExitStack
from unittest.mock import AsyncMock, patch

from app.core.exceptions import AppError
from app.services.nutrition import pipeline
from app.services.nutrition.etapas.bases import carregar_taco
from app.services.nutrition.modelos import InfoOnline, Macros
from tests.nutricao_comum import DADOS, candidato, leitura, settings

ALIMENTOS = carregar_taco(str(DADOS))
ARROZ = next(a for a in ALIMENTOS if a.nome == "Arroz, tipo 1, cozido")
FEIJAO = next(a for a in ALIMENTOS if a.nome == "Feijão, carioca, cozido")
CASADOS = {"arroz": ARROZ, "feijão": FEIJAO}


def info_base():
    return InfoOnline(macros=Macros(128, 2.5, 28.1, 0.2), base="100g", porcao_base="100 g", fonte_nome="TACO",
                      fonte_url=None, method="database", evidencia="“Arroz” 128 kcal por 100 g.")


def info_web():
    return InfoOnline(macros=Macros(1800, 70, 220, 60), base="item", porcao_base="pizza inteira",
                      fonte_nome="Pizza Express", fonte_url="https://pizzaexpress.com.br/n", method="web",
                      evidencia="“1800 kcal” tabela do site", porcao_g=700)


def rodar(s, c=None, *, bases=None, web=None, a=None, b=None, casados=CASADOS, imagem=None):
    """Executa a pipeline; devolve (resultado, mocks)."""
    mocks = {
        "consultar_bases": AsyncMock(return_value=bases),
        "buscar_na_web": AsyncMock(return_value=web),
        "estimar_a": AsyncMock(side_effect=a) if isinstance(a, Exception) else AsyncMock(return_value=a),
        "estimar_b": AsyncMock(side_effect=b) if isinstance(b, Exception) else AsyncMock(return_value=b),
        "casar_ingredientes": AsyncMock(return_value=casados),
        "decompor_ingredientes": AsyncMock(return_value=[]),
        "baixar_imagem": AsyncMock(return_value=imagem),
    }
    with ExitStack() as stack:
        for nome, mock in mocks.items():
            stack.enter_context(patch.object(pipeline, nome, mock))
        resultado = asyncio.run(pipeline.calcular(s, c or candidato(), None))
    return resultado, mocks


def test_so_estimativas_com_taco_vira_consenso_com_macros(tmp_path):
    r, m = rodar(settings(tmp_path), a=leitura("openrouter", 800, peso=None), b=leitura("gemini", 820, peso=380),
                 imagem=(b"x", "image/jpeg"))
    assert r.state == "ready" and r.method == "consensus"
    assert r.protein_g is not None and r.carbs_g is not None and r.fat_g is not None
    assert r.minimum <= r.calories <= r.maximum
    # TACO: 200 g de arroz + 100 g de feijão = ~331 kcal, bem abaixo das estimativas -> dispersão alta
    assert any("diferentes entre si" in x for x in r.assumptions)


def test_base_vence_estimativa_e_web_nao_e_chamada(tmp_path):
    r, m = rodar(settings(tmp_path), bases=info_base(), a=leitura("openrouter", 500), b=leitura("gemini", 520))
    assert r.method == "database" and r.source_name == "TACO"
    assert r.portion_grams == 400  # "400 g" da descrição
    assert r.calories == round(128 * 4)
    m["buscar_na_web"].assert_not_called()


def test_web_so_roda_quando_as_bases_falham(tmp_path):
    r, m = rodar(settings(tmp_path), bases=None, web=info_web(), a=leitura("openrouter", 1700), casados=None)
    assert r.method == "web" and r.source_url == "https://pizzaexpress.com.br/n"
    m["buscar_na_web"].assert_awaited_once()
    assert r.confidence == "high"


def test_web_nao_roda_para_restaurante_simulado(tmp_path):
    r, m = rodar(settings(tmp_path), c=candidato(simulated=True), a=leitura("openrouter", 700))
    m["buscar_na_web"].assert_not_called()
    assert r.state == "ready"


def test_fonte_por_100g_sem_peso_e_descartada_e_estimativa_assume(tmp_path):
    c = candidato(description="Sem peso informado")
    r, _ = rodar(settings(tmp_path), c=c, bases=info_base(), a=leitura("openrouter", 600, peso=None), casados=None)
    assert r.method == "estimated"
    assert any("100 g" in x for x in r.assumptions)


def test_peso_estimado_pela_imagem_destrava_fonte_por_100g(tmp_path):
    c = candidato(description="Sem peso informado")
    r, _ = rodar(settings(tmp_path), c=c, bases=info_base(), b=leitura("gemini", 600, peso=300),
                 imagem=(b"x", "image/jpeg"), casados=None)
    assert r.method == "database" and r.portion_grams == 300 and r.calories == round(128 * 3)


def test_modo_economico_com_fonte_nao_chama_estimadores(tmp_path):
    r, m = rodar(settings(tmp_path, calorias_estimar_sempre=False), bases=info_base())
    assert r.method == "database"
    m["estimar_a"].assert_not_called()
    m["estimar_b"].assert_not_called()


def test_modo_economico_sem_fonte_estima(tmp_path):
    r, m = rodar(settings(tmp_path, calorias_estimar_sempre=False), a=leitura("openrouter", 700))
    assert r.state == "ready"
    m["estimar_a"].assert_awaited_once()


def test_modo_economico_fonte_100g_sem_peso_cai_na_estimativa(tmp_path):
    c = candidato(description="Sem peso")
    r, m = rodar(settings(tmp_path, calorias_estimar_sempre=False), c=c, bases=info_base(),
                 a=leitura("openrouter", 700), casados=None)
    assert r.method == "estimated"
    m["estimar_a"].assert_awaited_once()


def test_falha_de_uma_fonte_nao_derruba(tmp_path):
    r, _ = rodar(settings(tmp_path), a=leitura("openrouter", 800), b=AppError("gemini fora do ar"),
                 imagem=(b"x", "image/jpeg"))
    assert r.state == "ready"


def test_tudo_falha_vira_indisponivel(tmp_path):
    r, _ = rodar(settings(tmp_path), a=AppError("x"), b=AppError("y"), casados=None)
    assert r.state == "unavailable" and r.calories is None


def test_macros_que_nao_fecham_marcam_revisao(tmp_path):
    ruim = dict(prot=5, carb=5, gord=5)
    r, _ = rodar(settings(tmp_path, calorias_limiar_confianca=0.9), a=leitura("openrouter", 800, **ruim),
                 b=leitura("gemini", 1500, **ruim), imagem=(b"x", "image/jpeg"), casados=None)
    assert r.revisar and r.motivo_revisao and r.confidence in ("low", "medium")


def test_foto_ilustrativa_nao_baixa_imagem(tmp_path):
    c = candidato(description="Foto meramente ilustrativa. 300 g")
    r, m = rodar(settings(tmp_path), c=c, a=leitura("openrouter", 700))
    m["baixar_imagem"].assert_not_called()
    assert any("ilustrativa" in x for x in r.assumptions)


def test_decompoe_so_quando_nenhuma_estimativa_trouxe_ingredientes(tmp_path):
    sem = dict(ingredientes=[])
    r, m = rodar(settings(tmp_path), a=leitura("openrouter", 800, **sem))
    m["decompor_ingredientes"].assert_awaited_once()
    m["decompor_ingredientes"].reset_mock()
    rodar(settings(tmp_path), a=leitura("openrouter", 800))
    m2 = rodar(settings(tmp_path), a=leitura("openrouter", 800))[1]
    m2["decompor_ingredientes"].assert_not_called()


def test_sem_chaves_de_openrouter_so_gemini_estima(tmp_path):
    r, m = rodar(settings(tmp_path, openrouter_api_key=""), b=leitura("gemini", 800), imagem=(b"x", "image/jpeg"))
    assert r.state == "ready" and r.method == "estimated"
    m["estimar_a"].assert_not_called()
    m["consultar_bases"].assert_not_called()
