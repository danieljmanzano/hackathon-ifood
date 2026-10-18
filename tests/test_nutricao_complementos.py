"""Complementos escolhidos (coberturas, adicionais) somados ao item base, vezes a quantidade."""
import asyncio
from contextlib import ExitStack
from unittest.mock import AsyncMock, patch

from app.core.exceptions import AppError
from app.schemas.macro import Option, OptionGroup, SelectedItem, SelectedOption
from app.services.nutrition import pipeline
from app.services.nutrition.etapas import complementos
from app.services.nutrition.etapas.complementos import Adicional, Separacao, quantidade_e_nome
from app.services.nutrition.modelos import InfoOnline, Macros
from app.services.nutrition.produtos import chave_produto
from tests.nutricao_comum import candidato, leitura, settings

ACAI_OPCOES = ["1 × Tradicional", "2 × Nutella", "1 × Paçoca"]


def acai(**campos):
    grupos = [OptionGroup(id="g-acai", name="Escolha o açaí", min_selections=1, max_selections=1,
                          options=[Option(id="o-trad", name="Tradicional")]),
              OptionGroup(id="g-cob", name="Coberturas", min_selections=0, max_selections=5,
                          options=[Option(id="o-nut", name="Nutella", max_quantity=3),
                                   Option(id="o-pac", name="Paçoca", max_quantity=3)])]
    dados = dict(name="Açaí 300ml", merchant_name="Açaí da Praça", description="Copo de açaí cremoso de 300ml.",
                 option_groups=grupos)
    dados.update(campos)
    return candidato(**dados)


def taco_acai():
    return InfoOnline(macros=Macros(58, 0.8, 6.2, 3.9), base="100g", porcao_base="100 g", fonte_nome="TACO",
                      fonte_url=None, method="database", evidencia="“Açaí, polpa” 58 kcal por 100 g.")


def resposta(*itens):
    """Itens como (índice, opção, tipo, gramas, kcal, proteína, carbo, gordura); índice None = sem índice."""
    campos = ("indice", "opcao", "tipo", "gramas_por_unidade", "kcal_por_unidade", "proteina_g", "carbo_g", "gordura_g")
    return {"opcoes": [{k: v for k, v in zip(campos, i) if not (k == "indice" and v is None)} for i in itens]}


def separar(tmp_path, dados, opcoes=ACAI_OPCOES, perguntar=None):
    complementos._unidades.clear()
    perguntar = perguntar or AsyncMock(return_value=dados)
    with patch.object(complementos, "perguntar_json", perguntar):
        return asyncio.run(complementos.separar_complementos(settings(tmp_path), acai(), opcoes))


def test_sem_indice_reconhece_pelo_nome_mesmo_com_prefixo_de_grupo(tmp_path):
    # Resposta real de um modelo: repetiu "grupo: opção" em vez de só a opção.
    s = separar(tmp_path, resposta((None, "Escolha o açaí: Tradicional", "base", None, None, None, None, None),
                                   (None, "Coberturas: Nutella", "adicional", 20, 107, None, None, None),
                                   (None, "2 × Paçoca", "adicional", 22, 110, None, None, None)))
    assert s.opcoes_base == ["1 × Tradicional"]
    assert [(a.nome, a.macros.kcal) for a in s.adicionais] == [("Nutella", 214), ("Paçoca", 110)]


def test_valor_por_unidade_e_reaproveitado_e_mais_quantidade_nunca_diminui(tmp_path):
    primeira = AsyncMock(return_value=resposta((0, "Tradicional", "base", None, None, None, None, None),
                                               (1, "Nutella", "adicional", 20, 108, None, None, None),
                                               (2, "Paçoca", "adicional", 22, 110, None, None, None)))
    um = separar(tmp_path, None, ["1 × Tradicional", "1 × Nutella", "1 × Paçoca"], perguntar=primeira)
    # Segunda chamada: o modelo daria outro valor, mas o da Nutella já está guardado e nem é perguntado.
    outra = AsyncMock(return_value=resposta((0, "Nutella", "adicional", 20, 70, None, None, None)))
    with patch.object(complementos, "perguntar_json", outra):
        dois = asyncio.run(complementos.separar_complementos(
            settings(tmp_path), acai(), ["1 × Tradicional", "2 × Nutella", "1 × Paçoca"]))
    outra.assert_not_called()
    total = lambda s: sum(a.macros.kcal for a in s.adicionais)
    assert total(dois) == total(um) + 108


def test_quantidade_e_nome():
    assert quantidade_e_nome("2 × Nutella") == (2, "Nutella")
    assert quantidade_e_nome("1 x Leite condensado") == (1, "Leite condensado")
    assert quantidade_e_nome("Paçoca") == (1, "Paçoca")


def test_separa_base_de_adicionais_e_multiplica_pela_quantidade(tmp_path):
    s = separar(tmp_path, resposta((0, "Tradicional", "base", None, None, None, None, None),
                                   (1, "Nutella", "adicional", 20, 108, 1.2, 11.5, 6.2),
                                   (2, "Paçoca", "adicional", 22, 110, 3.0, 11.0, 6.0)))
    assert s.opcoes_base == ["1 × Tradicional"]
    nutella, pacoca = s.adicionais
    assert (nutella.quantidade, nutella.macros.kcal, nutella.gramas) == (2, 216, 40)
    assert nutella.macros.proteina_g == 2.4
    assert pacoca.macros.kcal == 110 and not s.sem_estimativa


def test_opcao_que_o_modelo_nao_devolveu_fica_na_base_e_kcal_absurda_nao_e_somada(tmp_path):
    s = separar(tmp_path, resposta((1, "Nutella", "adicional", 20, 99999, None, None, None)))
    assert s.opcoes_base == ["1 × Tradicional", "1 × Paçoca"]  # não classificadas: conservador
    assert s.adicionais == [] and s.sem_estimativa == ["2 × Nutella"]


def rodar(tmp_path, separacao, *, bases=None, a=None):
    """Pipeline com as fontes falsas; devolve (resultado, mocks)."""
    mocks = {
        "separar_complementos": (AsyncMock(side_effect=separacao) if isinstance(separacao, Exception)
                                 else AsyncMock(return_value=separacao)),
        "consultar_bases": AsyncMock(return_value=bases), "buscar_na_web": AsyncMock(return_value=None),
        "estimar_a": AsyncMock(return_value=a), "estimar_b": AsyncMock(return_value=None),
        "casar_ingredientes": AsyncMock(return_value=None), "decompor_ingredientes": AsyncMock(return_value=[]),
        "baixar_imagem": AsyncMock(return_value=None),
    }
    with ExitStack() as stack:
        for nome, mock in mocks.items():
            stack.enter_context(patch.object(pipeline, nome, mock))
        resultado = asyncio.run(pipeline.calcular(settings(tmp_path), acai(), ACAI_OPCOES))
    return resultado, mocks


def test_taco_do_acai_puro_nao_apaga_mais_os_complementos(tmp_path):
    separacao = Separacao(["1 × Tradicional"], [Adicional("Nutella", 2, Macros(216, 2.4, 23, 12.4), 40),
                                                Adicional("Paçoca", 1, Macros(110, 3, 11, 6), 22)], [])
    r, m = rodar(tmp_path, separacao, bases=taco_acai(), a=leitura("openrouter", 400))
    assert r.state == "ready"
    base = round(58 * 3)  # TACO × 300 g, só o copo de açaí
    assert r.calories == base + 216 + 110
    assert r.minimum <= r.calories <= r.maximum and r.maximum > r.calories
    assert r.portion_grams == 300 + 40 + 22
    assert r.method == "consensus" and r.source_name == "TACO"  # fonte do copo + estimativa dos complementos
    assert r.confidence in ("low", "medium")
    assert any("2× Nutella" in x for x in r.assumptions)
    # o item base foi calculado SÓ com a opção que o define, não com as coberturas
    _, opcoes_base = m["estimar_a"].call_args.args[1:3]
    assert opcoes_base == ["1 × Tradicional"]


def test_complemento_sem_estimativa_vai_para_revisao(tmp_path):
    separacao = Separacao(["1 × Tradicional", "1 × Paçoca"], [], ["2 × Nutella"])
    r, _ = rodar(tmp_path, separacao, bases=taco_acai(), a=leitura("openrouter", 400))
    assert r.calories == round(58 * 3) and r.revisar
    assert any("Sem estimativa para: 2 × Nutella" in x for x in r.assumptions)


def test_se_a_separacao_falha_o_item_e_calculado_com_todas_as_opcoes(tmp_path):
    r, m = rodar(tmp_path, AppError("modelo fora do ar"), a=leitura("openrouter", 700))
    assert r.state == "ready"
    _, opcoes = m["estimar_a"].call_args.args[1:3]
    assert opcoes == ACAI_OPCOES


def test_chave_do_produto_considera_a_quantidade_de_cada_opcao():
    def item(qtd):
        return SelectedItem(candidate=acai(), quantity=1, unit_total_cents=1800,
                            options=[SelectedOption(group_id="g-cob", option_id="o-nut", quantity=qtd)],
                            option_labels=[f"{qtd} × Nutella"])
    assert chave_produto(item(1)) != chave_produto(item(2))
