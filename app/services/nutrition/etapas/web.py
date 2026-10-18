"""Busca na web (OpenAI web_search). Só roda quando as bases não acharam.

Dois resultados possíveis, conforme o tipo do item:
- industrializado (produto de mercado): tabela nutricional oficial do produto exato -> InfoOnline (vence as estimativas).
- prato (comida de restaurante): não existe tabela; o modelo pesquisa uma ESTIMATIVA, olhando a foto, a partir de
  pratos equivalentes -> Leitura (entra no consenso junto com as outras estimativas).
"""
import math
from urllib.parse import urlparse

from jsonschema import validate

from app.core import logs
from app.core.config import Settings
from app.schemas.macro import MealCandidate
from app.services.gemini import search_web
from app.services.openai_client import responder
from ..entrada import extrair_json, montar_prompt
from ..modelos import InfoOnline, Ingrediente, Leitura, Macros
from app.skills import nutricao_juiz_web, nutricao_web
from .llm import perguntar_json


def dominio(valor: str) -> str:
    """Domínio de uma URL ou de um título que já é domínio (o grounding devolve os dois)."""
    texto = valor.strip().lower()
    host = urlparse(texto).netloc if "://" in texto else texto.split("/")[0]
    return host.removeprefix("www.")


def _numero_valido(v) -> bool:
    return isinstance(v, (int, float)) and math.isfinite(v) and v >= 0


CONFIANCA_WEB = {"baixa": 0.35, "media": 0.5, "alta": 0.65}  # estimativa pesquisada nunca passa de 0,65


async def _pesquisar(settings: Settings, prompt: str, imagem: tuple[bytes, str] | None) -> tuple[str, list[str]]:
    """Texto da resposta e as fontes realmente consultadas, pelo provedor escolhido (com a foto, se houver)."""
    if settings.nutrition_provider == "openai":
        return await responder(prompt, instrucoes=nutricao_web.INSTRUCAO_CURTA_OPENAI, web=True,
                               schema=nutricao_web.SCHEMA, imagem=imagem, settings=settings)
    return await search_web(prompt, imagem=imagem, settings=settings)


TOLERANCIA_SOMA = 1.05  # proteína+carbo+gordura acima disso da base declarada: o rótulo da fonte está errado


def _da_tabela(dados: dict) -> Macros | None | bool:
    """Conta a tabela copiada da fonte para o peso do item (a conta é do código, não do modelo).

    None = o modelo não copiou a tabela (vale o que ele converteu); False = não dá para confiar nela;
    senão, os macros do item inteiro.
    """
    kcal, base, peso = dados.get("tabela_kcal"), dados.get("tabela_base_g"), dados.get("porcao_g")
    if not _numero_valido(kcal):
        return None
    macros = [_opcional(dados.get(c)) for c in ("tabela_proteina_g", "tabela_carbo_g", "tabela_gordura_g")]
    if not _numero_valido(base) or base <= 0:
        return None  # a fonte não diz a que se refere: sem base não há conversão confiável aqui
    if sum(m or 0 for m in macros) > base * TOLERANCIA_SOMA:
        logs.info("web", f"tabela incoerente: macros somam {sum(m or 0 for m in macros):.0f} g numa base de {base:.0f} g "
                         "→ os valores devem ser por 100 g; convertendo assim")
        base = 100.0
    if not _numero_valido(peso) or peso <= 0:
        logs.info("web", "tabela copiada, mas sem o peso do item para converter → descartada")
        return False
    fator = peso / base
    logs.info("web", f"conversão no código: tabela {kcal:.0f} kcal por {base:.0f} g × {fator:.3f} (item {peso:.0f} g)")
    return Macros(kcal * fator, *(None if m is None else m * fator for m in macros))


def _opcional(v) -> float | None:
    return float(v) if _numero_valido(v) else None


async def buscar_na_web(settings: Settings, candidate: MealCandidate, opcoes: list[str] | None,
                        imagem: tuple[bytes, str] | None = None, marca: str = "") -> InfoOnline | Leitura | None:
    prompt = nutricao_web.pedido(montar_prompt(candidate, opcoes), com_foto=bool(imagem), marca=marca)
    fornecedor = "OpenAI web_search" if settings.nutrition_provider == "openai" else "Gemini + Google Search"
    logs.info("web", f"pesquisando \"{candidate.name}\" de {candidate.merchant_name} via {fornecedor}"
                     f"{' com a foto' if imagem else ' (sem foto)'}")
    with logs.Cronometro() as t:
        texto, consultados = await _pesquisar(settings, prompt, imagem)
    logs.info("web", f"busca terminou em {t.texto}; {len(consultados)} fontes consultadas")
    logs.detalhe("web", "domínios consultados: " + (", ".join(sorted({dominio(c) for c in consultados})) or "nenhum"))
    logs.detalhe("web", f"resposta: {logs.curto(texto, 400)}")
    dados = extrair_json(texto)
    validate(dados, nutricao_web.SCHEMA)
    logs.info("web", f"o modelo classificou o item como: {dados['tipo_item']}")
    if imagem is not None:
        vistos = [str(i).strip() for i in dados.get("itens_na_foto", []) if str(i).strip()]
        if vistos:
            logs.info("web", "viu na foto: " + "; ".join(vistos))
        else:
            logs.aviso("web", "não listou nada visível na foto (a imagem pode não ter sido lida)")

    if not dados["encontrado"]:
        logs.info("web", "o modelo não achou base para "
                         + ("a tabela do produto" if dados["tipo_item"] == "industrializado" else "uma estimativa"))
        return None
    if not dados["fonte_url"] or not dados["trecho_fonte"].strip():
        logs.info("web", "descartada: resposta sem URL da fonte ou sem trecho que a sustente")
        return None
    if dominio(dados["fonte_url"]) not in {dominio(c) for c in consultados}:
        logs.info("web", f"descartada: {dominio(dados['fonte_url'])} não está entre os sites realmente consultados")
        return None
    tabela = _da_tabela(dados) if dados["tipo_item"] == "industrializado" else None
    if tabela is False:
        return None
    if tabela is not None:
        modelo = dados["calorias"]
        if _numero_valido(modelo) and abs(modelo - tabela.kcal) > 0.05 * tabela.kcal:
            logs.info("web", f"o modelo converteu para {modelo:.0f} kcal; vale a conta do código: {tabela.kcal:.0f} kcal")
        dados = {**dados, "calorias": tabela.kcal}
    kcal = dados["calorias"]
    if not _numero_valido(kcal) or kcal == 0 and dados["tipo_item"] == "prato":
        logs.info("web", "descartada: calorias ausentes ou inválidas na resposta")
        return None
    faixa = None
    if _numero_valido(dados["faixa_min"]) and _numero_valido(dados["faixa_max"]) \
            and dados["faixa_min"] <= kcal <= dados["faixa_max"]:
        faixa = (float(dados["faixa_min"]), float(dados["faixa_max"]))
    macros = tabela if tabela is not None else Macros(float(kcal), _opcional(dados["proteina_g"]),
                                                      _opcional(dados["carbo_g"]), _opcional(dados["gordura_g"]))
    fonte = f"{dados['fonte_nome'] or dominio(dados['fonte_url'])} ({dominio(dados['fonte_url'])})"

    if dados["tipo_item"] == "prato":
        return _estimativa_pesquisada(dados, macros, faixa, fonte)
    return await _tabela_oficial(settings, candidate, opcoes, dados, macros, faixa)


def _estimativa_pesquisada(dados: dict, macros: Macros, faixa, fonte: str) -> Leitura:
    """Prato de restaurante: a pesquisa vira mais uma estimativa (não é fonte oficial, não atropela as outras)."""
    kcal = macros.kcal
    minimo, maximo = faixa or (kcal * 0.75, kcal * 1.25)
    ingredientes = [Ingrediente(i["nome"], float(i["gramas"])) for i in dados["ingredientes"] if i["gramas"] > 0]
    logs.info("web", f"estimativa pesquisada: {kcal:.0f} kcal ({minimo:.0f}–{maximo:.0f}) com base em "
                     f"\"{dados['produto_na_fonte']}\" · {fonte} · confiança {dados['confianca']}")
    return Leitura(
        fonte="web", macros=macros, faixa_min=min(minimo, kcal), faixa_max=max(maximo, kcal),
        confianca=CONFIANCA_WEB[dados["confianca"]], porcao_base=dados["porcao_base"],
        peso_g=_opcional(dados["porcao_g"]), ingredientes=ingredientes,
        itens_na_imagem=[str(i).strip() for i in dados.get("itens_na_foto", []) if str(i).strip()],
        suposicoes=[f"Estimativa pesquisada na web com base em “{dados['produto_na_fonte']}” — {fonte}.",
                    *dados["suposicoes"]],
        justificativa=f"“{dados['trecho_fonte'].strip()}” {dados['justificativa']}".strip(),
    )


async def _tabela_oficial(settings, candidate, opcoes, dados: dict, macros: Macros, faixa) -> InfoOnline | None:
    """Produto industrializado: a tabela precisa ser do mesmo produto; um juiz confirma antes de aceitar."""
    logs.info("web", f"candidata: {macros.kcal:.0f} kcal em {dominio(dados['fonte_url'])} "
                     f"(\"{dados['produto_na_fonte']}\")")
    juiz = await perguntar_json(
        settings, nutricao_juiz_web.INSTRUCOES,
        nutricao_juiz_web.pedido(montar_prompt(candidate, opcoes), dados["produto_na_fonte"], dados["fonte_nome"],
                                 dados["fonte_url"], dados["trecho_fonte"], dados["porcao_base"]),
        nutricao_juiz_web.SCHEMA)
    if not juiz["corresponde"]:
        logs.info("web", f"descartada: juiz diz que é outro produto ({logs.curto(juiz['motivo'], 160)})")
        return None
    logs.info("web", f"juiz confirmou o mesmo produto ({logs.curto(juiz['motivo'], 120)}) → tabela aceita")
    return InfoOnline(
        macros=macros, base="item", porcao_base=dados["porcao_base"],
        fonte_nome=dados["fonte_nome"] or dominio(dados["fonte_url"]), fonte_url=dados["fonte_url"], method="web",
        porcao_g=_opcional(dados["porcao_g"]), faixa=faixa,
        evidencia=f"“{dados['trecho_fonte'].strip()}” {dados['justificativa']}".strip(),
    )
