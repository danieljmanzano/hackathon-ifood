"""Pipeline de calorias (ver pipeline_calorias_v2.dot): fontes em cascata e junções finais.

online (bases → web) e estimativa (A + B + TACO) rodam em paralelo; fundir, calcular_porcao e validar fecham.
"""
import asyncio
import json
from datetime import datetime, timezone

from jsonschema import ValidationError as SchemaError

from app.core import logs
from app.core.config import Settings
from app.core.exceptions import AppError
from app.schemas.macro import MealCandidate, NutritionResult
from .entrada import baixar_imagem, foto_ilustrativa, montar_prompt, restaurante_valido
from .etapas.bases import carregar_taco, consultar_bases
from .etapas.classificar import classificar_item
from .etapas.consenso import consenso, fundir
from .etapas.estimar import EstimativaInvalida, decompor_ingredientes, estimar_a, estimar_b
from .etapas.ingredientes import casar_ingredientes, somar_ingredientes
from .etapas.porcao import calcular_porcao, converter_em_gramas, extrair_porcao
from .etapas.validar import validar
from .etapas.web import buscar_na_web
from .modelos import Estimativa, InfoOnline, Leitura

PIPELINE_VERSION = "calorias-v3"
ERROS_ETAPA = (AppError, json.JSONDecodeError, SchemaError, KeyError, EstimativaInvalida)



async def _seguro(coro, etapa: str):
    """Falha de uma etapa vira None: as outras fontes continuam."""
    try:
        return await coro
    except ERROS_ETAPA as e:
        logs.aviso(etapa, f"FALHOU: {logs.curto(e, 220)}")
        return None


async def _nada():
    return None


async def _online(settings: Settings, candidate: MealCandidate, opcoes: list[str] | None,
                  descricao: str, imagem) -> InfoOnline | Leitura | None:
    """Onde achar os valores: produto de marca -> tabela oficial na web primeiro; prato -> bases primeiro.

    A web devolve uma InfoOnline (tabela oficial de produto industrializado) ou uma Leitura
    (estimativa pesquisada para prato de restaurante, que entra no consenso).
    Produto de marca tem rótulo publicado: a TACO genérica ("Bolo, pronto, chocolate") não pode tomar o lugar dele.
    """
    web_possivel = (settings.calorias_busca_web and bool(settings.web_api_key) and restaurante_valido(candidate))
    web_tentada = False

    if settings.calorias_classificar and settings.llm_api_key and web_possivel:
        classe = await _seguro(classificar_item(settings, descricao, imagem), "classificar")
        if classe and classe["tipo_item"] == "industrializado":
            logs.info("web", "item de marca/embalagem: procurando a tabela oficial ANTES das bases genéricas")
            web_tentada = True
            achado = await _seguro(buscar_na_web(settings, candidate, opcoes, imagem, marca=classe["marca"]), "web")
            if achado is not None:
                return achado
            logs.info("web", "tabela oficial não encontrada; caindo para as bases genéricas")

    info = None
    if not settings.calorias_buscar_bases:
        logs.info("bases", "desligadas (CALORIAS_BUSCAR_BASES=false)")
    elif not settings.llm_api_key:
        logs.info("bases", f"puladas: sem chave do provedor de texto ({settings.nutrition_provider})")
    else:
        info = await _seguro(consultar_bases(settings, candidate, descricao), "bases")

    if info is not None:
        logs.info("web", "não consultada: as bases já acharam")
    elif web_tentada:
        pass  # a web já foi tentada acima (produto de marca)
    elif not settings.calorias_busca_web:
        logs.info("web", "desligada (CALORIAS_BUSCA_WEB=false)")
    elif not settings.web_api_key:
        logs.info("web", "pulada: sem chave de busca "
                         f"({'OPENAI_API_KEY' if settings.nutrition_provider == 'openai' else 'GEMINI_API_KEY'})")
    elif not restaurante_valido(candidate):
        logs.info("web", "pulada: restaurante simulado/inválido (modo demonstração)")
    else:
        info = await _seguro(buscar_na_web(settings, candidate, opcoes, imagem), "web")
    return info


def _descrever(l) -> str:
    m = l.macros
    macros = f" · P {m.proteina_g:.0f} C {m.carbo_g:.0f} G {m.gordura_g:.0f}" if m.completo() else ""
    peso = f" · peso ~{l.peso_g:.0f} g" if l.peso_g else ""
    return f"{m.kcal:.0f} kcal ({l.faixa_min:.0f}–{l.faixa_max:.0f}){macros}{peso} · confiança do modelo {l.confianca:.2f}"


async def _leituras(settings: Settings, candidate: MealCandidate, opcoes: list[str] | None,
                    peso_g: float | None, imagem) -> list[Leitura]:
    """A (OpenRouter/OpenAI, texto) e B (Gemini, texto + imagem) em paralelo, mais a soma de ingredientes pela TACO."""
    if not settings.llm_api_key:
        logs.info("estimar A", f"pulada: sem chave do provedor de texto ({settings.nutrition_provider})")
    if imagem is None:
        logs.info("estimar B", "pulada: sem imagem")
    elif not settings.gemini_api_key:
        logs.info("estimar B", "pulada: sem GEMINI_API_KEY")

    with logs.Cronometro() as t:
        a, b = await asyncio.gather(
            _seguro(estimar_a(settings, candidate, opcoes, peso_g), "estimar A") if settings.llm_api_key
            else _nada(),
            _seguro(estimar_b(settings, candidate, opcoes, peso_g, imagem), "estimar B"),
        )
    for nome, leitura in (("estimar A", a), ("estimar B", b)):
        if leitura is not None:
            logs.info(nome, f"{_descrever(leitura)} ({t.texto} no total)")
            logs.detalhe(nome, f"justificativa: {logs.curto(leitura.justificativa, 300)}")
            ingredientes = ", ".join(f"{i.nome} {i.gramas:.0f} g" for i in leitura.ingredientes) or "—"
            if nome == "estimar B":  # o único que enxerga a foto: mostra o que ele viu ao lado do que estimou
                if leitura.itens_na_imagem:
                    logs.info(nome, "viu na foto: " + "; ".join(leitura.itens_na_imagem))
                else:
                    logs.aviso(nome, "não listou nada visível na foto (a imagem pode não ter sido lida; confira o link)")
                logs.info(nome, f"ingredientes estimados: {ingredientes}")
            else:
                logs.detalhe(nome, f"ingredientes: {ingredientes}")
    leituras = [x for x in (a, b) if x is not None]

    alimentos = carregar_taco(str(settings.calorias_dados_dir)) if settings.calorias_buscar_bases else ()
    if alimentos and settings.llm_api_key:
        ingredientes = next((l.ingredientes for l in (b, a) if l is not None and l.ingredientes), [])
        if not ingredientes:
            ingredientes = await _seguro(decompor_ingredientes(settings, candidate, opcoes, peso_g),
                                         "ingredientes") or []
            if ingredientes:
                logs.info("ingredientes", "nenhuma estimativa trouxe a lista; decomposta pelo LLM: "
                          + ", ".join(f"{i.nome} {i.gramas:.0f} g" for i in ingredientes))
        if ingredientes:
            casados = await _seguro(casar_ingredientes(settings, ingredientes, alimentos), "casar TACO")
            if casados:
                for ing in ingredientes:
                    alvo = casados.get(ing.nome)
                    logs.info("casar TACO", f"{ing.nome} ({ing.gramas:.0f} g) → "
                              f"{alvo.nome if alvo else 'sem correspondência'}")
            soma = somar_ingredientes(ingredientes, casados) if casados else None
            if soma is not None:
                logs.info("soma TACO", _descrever(soma))
                leituras.append(soma)
            elif casados:
                logs.info("soma TACO", "descartada: menos de 70% da massa casada com a TACO")
        else:
            logs.info("ingredientes", "nenhuma lista de ingredientes disponível; soma pela TACO pulada")
    elif not alimentos and settings.calorias_buscar_bases:
        logs.aviso("soma TACO", f"arquivo taco.csv não encontrado em {settings.calorias_dados_dir}")

    return leituras


def _consolidar(leituras: list[Leitura]) -> Estimativa | None:
    """Consenso (mediana) entre todas as estimativas disponíveis: A, B, soma TACO e a pesquisada na web."""
    resultado = consenso(leituras)
    if resultado is None:
        logs.aviso("consenso", "nenhuma fonte de estimativa respondeu")
    else:
        disp = f"{resultado.dispersao:.0%}" if resultado.dispersao is not None else "— (fonte única)"
        logs.info("consenso", f"fontes {resultado.fontes} → {resultado.macros.kcal:.0f} kcal "
                              f"({resultado.faixa_min:.0f}–{resultado.faixa_max:.0f}) · dispersão {disp}")
    return resultado


def _indisponivel(motivo: str) -> NutritionResult:
    return NutritionResult(state="unavailable", pipeline_version=PIPELINE_VERSION,
                           obtained_at=datetime.now(timezone.utc), evidence=motivo)


def _modo(settings: Settings) -> str:
    return (f"provedor={settings.nutrition_provider} · estimar_sempre={settings.calorias_estimar_sempre} · "
            f"bases={settings.calorias_buscar_bases} · web={settings.calorias_busca_web} · "
            f"amostras={settings.calorias_amostras}")


async def calcular(settings: Settings, candidate: MealCandidate, opcoes: list[str] | None) -> NutritionResult:
    logs.iniciar_item(candidate.name)
    with logs.Cronometro() as total:
        resultado = await _calcular(settings, candidate, opcoes)
    r = resultado
    if r.state == "ready":
        macros = f" · P {r.protein_g} C {r.carbs_g} G {r.fat_g}" if r.protein_g is not None else ""
        logs.info("RESULTADO", f"{r.calories:.0f} kcal ({r.minimum:.0f}–{r.maximum:.0f}){macros} · método {r.method} · "
                               f"confiança {r.confidence}{' · REVISAR' if r.revisar else ''} · {total.texto}")
    else:
        logs.aviso("RESULTADO", f"{r.state}: {logs.curto(r.evidence)} · {total.texto}")
    return resultado


async def _calcular(settings: Settings, candidate: MealCandidate, opcoes: list[str] | None) -> NutritionResult:
    logs.info("início", f"{candidate.merchant_name} · opções: {', '.join(opcoes) if opcoes else 'nenhuma'}")
    logs.info("modo", _modo(settings))

    porcao = extrair_porcao(candidate, opcoes)
    partes = []
    if porcao.gramas:
        partes.append(f"{porcao.gramas:.0f} g declarados (\"{porcao.trecho}\")")
    if porcao.pessoas_min:
        partes.append(f"serve {porcao.pessoas_min}" + (f"–{porcao.pessoas_max}" if porcao.pessoas_max != porcao.pessoas_min else ""))
    if porcao.tamanho_cm:
        partes.append(f"{porcao.tamanho_cm:g} cm")
    logs.info("porção", " · ".join(partes) if partes else "nada declarado no nome/descrição (peso será estimado)")

    ilustrativa = foto_ilustrativa(candidate)
    imagem = None if ilustrativa else await baixar_imagem(candidate.image_url, settings.nutrition_timeout_seconds)
    if ilustrativa:
        logs.info("imagem", "ignorada: a descrição diz que a foto é ilustrativa")
    elif imagem:
        logs.info("imagem", f"baixada ({len(imagem[0]) // 1024} KB, {imagem[1]}) · abra para conferir: {candidate.image_url}")
    else:
        logs.info("imagem", "indisponível" + ("" if candidate.image_url else " (item sem foto)") + " → só texto")
    descricao = montar_prompt(candidate, opcoes, porcao.gramas)
    logs.detalhe("prompt", logs.curto(descricao, 400))

    online = _online(settings, candidate, opcoes, descricao, imagem)
    leituras: list[Leitura] = []
    if settings.calorias_estimar_sempre:
        logs.info("modo", "estimativa roda em paralelo com as fontes online (mede a divergência)")
        achado, leituras = await asyncio.gather(online, _leituras(settings, candidate, opcoes, porcao.gramas, imagem))
    else:
        achado = await online
        if achado is None:
            logs.info("modo", "econômico: nenhuma fonte online → rodando a estimativa")
            leituras = await _leituras(settings, candidate, opcoes, porcao.gramas, imagem)
        else:
            logs.info("modo", "econômico: a pesquisa online achou → estimativas dispensadas")

    info = achado if isinstance(achado, InfoOnline) else None
    if isinstance(achado, Leitura):  # estimativa pesquisada na web: mais uma estimativa no consenso
        leituras = [*leituras, achado]
    est: Estimativa | None = _consolidar(leituras) if leituras else None

    peso_estimado = (est.peso_g if est else None) or (info.porcao_g if info else None)
    gramas, origem_gramas, avisos = converter_em_gramas(porcao, peso_estimado)
    logs.info("gramas", f"{gramas:.0f} g ({origem_gramas})" if gramas else "peso do prato desconhecido")
    for aviso in avisos:
        logs.aviso("gramas", aviso)

    info_macros = calcular_porcao(info, gramas) if info else None
    if info is not None and info_macros is None:
        avisos.append(f"Fonte {info.fonte_nome} é por 100 g e o peso do prato é desconhecido: não foi usada.")
        logs.aviso("porção", f"{info.fonte_nome} é por 100 g e não há peso do prato → fonte descartada")
        info = None
        if not settings.calorias_estimar_sempre and est is None:  # modo econômico: ainda não rodou
            logs.info("modo", "econômico: fonte descartada → rodando a estimativa")
            est = _consolidar(await _leituras(settings, candidate, opcoes, porcao.gramas, imagem))
    elif info is not None:
        logs.info("porção", f"{info.fonte_nome} ({info.base}) → {info_macros.kcal:.0f} kcal para o prato"
                  + (f" (×{gramas / 100:.2f})" if info.base == "100g" and gramas else ""))

    fundido = fundir(info, info_macros, est)
    if fundido is None:
        logs.aviso("fusão", "sem nenhuma fonte (nem online nem estimativa)")
        return _indisponivel("Não foi possível obter calorias de nenhuma fonte para este item.")
    div = f" · divergência fonte×estimativa {fundido.divergencia:.0%}" if fundido.divergencia is not None else ""
    logs.info("fusão", f"vence: {fundido.method} ({', '.join(fundido.fontes)}){div}")

    validacao = validar(fundido, gramas, settings.calorias_limiar_confianca)
    logs.info("validação", f"confiança {validacao.score:.2f} → {validacao.confianca}"
              f"{' · abaixo do limiar ' + str(settings.calorias_limiar_confianca) + ' → REVISAR' if validacao.revisar else ''}")
    for motivo in validacao.motivos:
        logs.info("validação", f"  - {motivo}")

    suposicoes = list(est.suposicoes) if est else []
    if ilustrativa:
        suposicoes.append("Foto ilustrativa: não foi usada para medir a porção.")
    elif candidate.image_url and imagem is None:
        suposicoes.append("Imagem indisponível: estimativa feita só com o texto.")
    suposicoes += avisos + validacao.motivos

    porcao_base = fundido.porcao_base or "unidade do item"
    if gramas:
        porcao_base += f" (~{gramas:.0f} g, peso {origem_gramas})"
    macros = fundido.macros
    evidencia = fundido.info.evidencia if fundido.info else (est.justificativa if est else "") or "Estimativa."
    return NutritionResult(
        state="ready", method=fundido.method, portion_basis=porcao_base,
        calories=round(macros.kcal), minimum=round(fundido.faixa_min), maximum=round(fundido.faixa_max),
        protein_g=_arred(macros.proteina_g), carbs_g=_arred(macros.carbo_g), fat_g=_arred(macros.gordura_g),
        portion_grams=round(gramas) if gramas else None, confidence=validacao.confianca,
        source_name=fundido.info.fonte_nome if fundido.info else None,
        source_url=fundido.info.fonte_url if fundido.info else None,
        evidence=evidencia, assumptions=suposicoes, revisar=validacao.revisar,
        motivo_revisao="; ".join(validacao.motivos) if validacao.revisar and validacao.motivos else None,
        pipeline_version=PIPELINE_VERSION, obtained_at=datetime.now(timezone.utc),
    )


def _arred(valor: float | None) -> float | None:
    return None if valor is None else round(valor, 1)
