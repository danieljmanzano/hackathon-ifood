from app.services.nutrition.etapas.consenso import consenso, fundir
from app.services.nutrition.etapas.validar import validar
from app.services.nutrition.modelos import InfoOnline, Macros
from tests.nutricao_comum import leitura


def test_consenso_com_uma_duas_e_tres_fontes():
    uma = consenso([leitura("gemini", 800)])
    assert uma.macros.kcal == 800 and uma.dispersao is None

    duas = consenso([leitura("gemini", 700), leitura("openrouter", 900)])
    assert duas.macros.kcal == 800
    assert abs(duas.dispersao - 0.25) < 1e-9
    assert duas.faixa_min <= 700 and duas.faixa_max >= 900

    tres = consenso([leitura("gemini", 700), leitura("openrouter", 900), leitura("taco", 760)])
    assert tres.macros.kcal == 760 and tres.fontes == ["gemini", "openrouter", "taco"]
    assert consenso([]) is None


def test_consenso_mediana_ignora_macro_ausente_e_pesos():
    a = leitura("gemini", 800, peso=400)
    b = leitura("openrouter", 800, prot=None, peso=None)
    junto = consenso([a, b])
    assert junto.macros.proteina_g == 35 and junto.peso_g == 400


def _info(kcal=700, method="web"):
    return InfoOnline(macros=Macros(kcal, 30, 80, 25), base="item", porcao_base="pizza", fonte_nome="Site",
                      fonte_url="https://site.com/x", evidencia="e", method=method)


def test_fundir_online_vence_e_guarda_divergencia():
    est = consenso([leitura("gemini", 500)])
    f = fundir(_info(700), Macros(700, 30, 80, 25), est)
    assert f.method == "web" and f.macros.kcal == 700
    assert abs(f.divergencia - 0.4) < 1e-9
    assert (round(f.faixa_min), round(f.faixa_max)) == (630, 770)  # ±10% para fonte web


def test_fundir_so_estimativa_e_metodo_por_numero_de_fontes():
    assert fundir(None, None, consenso([leitura("gemini")])).method == "estimated"
    assert fundir(None, None, consenso([leitura("gemini"), leitura("openrouter")])).method == "consensus"
    assert fundir(None, None, None) is None


def test_fundir_base_tem_faixa_larga():
    f = fundir(_info(400, "database"), Macros(400), None)
    assert (round(f.faixa_min), round(f.faixa_max)) == (300, 500)


def test_validar_web_consistente_e_alta():
    f = fundir(_info(), Macros(700, 30, 80, 25), None)  # Atwater: 120+320+225=665 vs 700
    v = validar(f, 400, 0.55)
    assert v.confianca == "high" and not v.revisar


def test_validar_atwater_quebrado_derruba_confianca():
    f = fundir(None, None, consenso([leitura("a", 800, prot=5, carb=5, gord=5), leitura("b", 800, prot=5, carb=5, gord=5)]))
    v = validar(f, 400, 0.55)
    assert any("Atwater" in m for m in v.motivos)
    assert v.score < 0.7


def test_validar_dispersao_e_divergencia():
    est = consenso([leitura("a", 300), leitura("b", 900)])
    f = fundir(_info(2000), Macros(2000, 100, 200, 60), est)
    v = validar(f, None, 0.55)
    assert v.revisar and v.confianca == "low"
    assert any("diferentes entre si" in m for m in v.motivos) and any("divergem" in m for m in v.motivos)


def test_validar_calorias_implausiveis_e_macros_maiores_que_o_prato():
    f = fundir(None, None, consenso([leitura("a", 9000, prot=900, carb=900, gord=900)]))
    v = validar(f, 400, 0.55)
    assert any("plausível" in m for m in v.motivos) and any("excede" in m for m in v.motivos)
