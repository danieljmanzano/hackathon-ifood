from app.services.nutrition.etapas.porcao import calcular_porcao, converter_em_gramas, extrair_porcao
from app.services.nutrition.modelos import InfoOnline, Macros, Porcao
from tests.nutricao_comum import candidato, candidato_do_mcp


def test_descricao_real_do_mcp_so_traz_tamanho_e_pessoas():
    porcao = extrair_porcao(candidato_do_mcp())
    assert porcao.gramas is None
    assert porcao.tamanho_cm == 35
    assert (porcao.pessoas_min, porcao.pessoas_max) == (1, 2)


def test_gramatura_em_varias_unidades():
    assert extrair_porcao(candidato(description="Marmita de 500g com arroz")).gramas == 500
    assert extrair_porcao(candidato(description="Peso: 1,5 kg")).gramas == 1500
    assert extrair_porcao(candidato(description="Suco 350 ml")).gramas == 350
    assert extrair_porcao(candidato(description="Refrigerante 2 litros")).gramas == 2000
    assert extrair_porcao(candidato(name="Hambúrguer 180 g", description="")).gramas == 180


def test_sem_gramatura_nem_confunde_palavras():
    assert extrair_porcao(candidato(description="Serve bem 2 pessoas, 3 fatias de gordura")).gramas is None


def test_serve_em_portugues():
    porcao = extrair_porcao(candidato(description="Serve 2 a 3 pessoas"))
    assert (porcao.pessoas_min, porcao.pessoas_max) == (2, 3)


def test_converter_prefere_declarada_e_avisa_divergencia():
    gramas, origem, avisos = converter_em_gramas(Porcao(gramas=400), 900)
    assert (gramas, origem) == (400, "declarada") and avisos
    assert converter_em_gramas(Porcao(gramas=400), 450)[2] == []


def test_converter_usa_estimada_ou_ausente():
    assert converter_em_gramas(Porcao(), 380)[:2] == (380, "estimada")
    assert converter_em_gramas(Porcao(), None)[:2] == (None, "ausente")


def _info(base):
    return InfoOnline(macros=Macros(200, 10, 20, 8), base=base, porcao_base="x", fonte_nome="TACO", fonte_url=None,
                      evidencia="e", method="database")


def test_calcular_porcao_por_100g_exige_gramas():
    assert calcular_porcao(_info("100g"), None) is None
    assert calcular_porcao(_info("100g"), 300).kcal == 600
    assert calcular_porcao(_info("item"), None).kcal == 200
