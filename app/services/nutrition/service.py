"""Pipeline nutricional como serviço.

1. Se o restaurante é real e conhecido, procura a tabela nutricional publicada (busca na web).
2. Senão, ou se nada confiável for encontrado, estima com descrição, opções e imagem.

Sempre devolve um NutritionResult: falhas viram state="error" para não derrubar a busca.
"""
import asyncio
import base64
import hashlib
import json
import logging
import math
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx
from pydantic import ValidationError

from app.core.config import Settings
from app.schemas.macro import MealCandidate, NutritionResult, Recommendation, SelectedItem
from .llm import LLMError, OpenAIBackend, OpenRouterBackend, criar_backend
from .prompts import INSTRUCOES_BUSCA, INSTRUCOES_ESTIMATIVA, SCHEMA_BUSCA, SCHEMA_ESTIMATIVA

Backend = OpenAIBackend | OpenRouterBackend

PIPELINE_VERSION = "calorias-v1"
CONFIANCA = {"baixa": "low", "media": "medium", "alta": "high"}
RESTAURANTES_INVALIDOS = {"", "não informado", "nao informado", "desconhecido", "n/a", "na", "null", "none", "-"}
LIMITACAO_SEM_NUTRICAO = "Informação nutricional indisponível"
MAX_IMAGEM_BYTES = 5 * 1024 * 1024

log = logging.getLogger(__name__)

# Resultados prontos por item; estimativas que passam do prazo da resposta terminam aqui em segundo plano.
_cache: dict[str, NutritionResult] = {}
_em_andamento: dict[str, asyncio.Task] = {}
_limites: dict[int, asyncio.Semaphore] = {}  # estimativas simultâneas por loop (limite de uso do provedor)


def _semaforo(settings: Settings) -> asyncio.Semaphore:
    loop = id(asyncio.get_running_loop())
    if loop not in _limites:
        _limites[loop] = asyncio.Semaphore(settings.nutrition_concurrency)
    return _limites[loop]


class NutritionFailure(Exception):
    """Resposta do modelo inutilizável (números inconsistentes, formato inesperado)."""


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _resultado(state: str, **campos) -> NutritionResult:
    return NutritionResult(state=state, pipeline_version=PIPELINE_VERSION, obtained_at=_agora(), **campos)


def _partes(item: MealCandidate | SelectedItem) -> tuple[MealCandidate, list[str] | None]:
    """Candidato e opções escolhidas (None quando o usuário ainda não escolheu)."""
    if isinstance(item, SelectedItem):
        return item.candidate, item.option_labels
    return item, None


def _chave(candidate: MealCandidate, opcoes: list[str] | None) -> str:
    bruto = json.dumps([PIPELINE_VERSION, candidate.merchant_id, candidate.merchant_name, candidate.simulated,
                        candidate.item_id, candidate.name, candidate.description, candidate.image_url, opcoes],
                       ensure_ascii=False)
    return hashlib.sha256(bruto.encode()).hexdigest()


def restaurante_valido(candidate: MealCandidate) -> bool:
    nome = candidate.merchant_name.strip().lower()
    return not candidate.simulated and nome not in RESTAURANTES_INVALIDOS


def foto_ilustrativa(candidate: MealCandidate) -> bool:
    return "ilustrativ" in candidate.description.lower()


def montar_prompt(candidate: MealCandidate, opcoes: list[str] | None) -> str:
    if opcoes:
        texto_opcoes = "Opções escolhidas:\n" + "\n".join(f"- {o}" for o in opcoes)
    elif opcoes is None and candidate.option_groups:
        grupos = []
        for g in candidate.option_groups:
            regra = "obrigatório" if g.min_selections else "opcional"
            grupos.append(f"- {g.name} ({regra}, até {g.max_selections}): " + ", ".join(o.name for o in g.options))
        texto_opcoes = ("Opções ainda não escolhidas. Estime para a combinação mais provável e reflita a variação "
                        "entre as opções na faixa:\n" + "\n".join(grupos))
    else:
        texto_opcoes = "Opções escolhidas: nenhuma"
    return (f"Nome: {candidate.name}\n"
            f"Restaurante: {candidate.merchant_name}\n"
            f"Descrição: {candidate.description or '(sem descrição)'}\n"
            f"{texto_opcoes}")


def _faixa(calorias, minimo, maximo) -> tuple[int, int, int]:
    numeros = (calorias, minimo, maximo)
    if any(n is None or not math.isfinite(n) or n < 0 for n in numeros):
        raise NutritionFailure(f"valores inválidos: {numeros}")
    if not minimo <= calorias <= maximo:
        raise NutritionFailure(f"faixa inconsistente: {numeros}")
    return calorias, minimo, maximo


def _dominio(url: str) -> str:
    return urlparse(url).netloc.lower().removeprefix("www.")


async def buscar_publicado(backend: Backend, candidate: MealCandidate,
                           opcoes: list[str] | None) -> NutritionResult | None:
    """Tabela nutricional publicada para este item, ou None se nada confiável foi encontrado."""
    resposta = await backend.json(
        nome="busca_nutricional", schema=SCHEMA_BUSCA, instrucoes=INSTRUCOES_BUSCA, buscar_na_web=True,
        texto="Procure a informação nutricional oficial deste item.\n\n" + montar_prompt(candidate, opcoes),
    )
    dados = resposta.dados
    if not dados["encontrado"]:
        return None
    if not dados["fonte_url"] or not dados["trecho_fonte"].strip():
        log.info("Busca sem fonte ou trecho para %s; descartada.", candidate.name)
        return None
    if _dominio(dados["fonte_url"]) not in {_dominio(u) for u in resposta.urls}:
        log.info("Fonte %s não está entre os sites consultados; descartada.", dados["fonte_url"])
        return None
    try:
        calorias, minimo, maximo = _faixa(dados["calorias"], dados["faixa_min"], dados["faixa_max"])
    except NutritionFailure as e:
        log.info("Busca com números inválidos para %s (%s); descartada.", candidate.name, e)
        return None
    return _resultado(
        "ready", method="published", calories=calorias, minimum=minimo, maximum=maximo,
        confidence=CONFIANCA[dados["confianca"]], portion_basis=dados["porcao_base"],
        source_name=dados["fonte_nome"] or _dominio(dados["fonte_url"]), source_url=dados["fonte_url"],
        evidence=f"“{dados['trecho_fonte'].strip()}” {dados['justificativa']}".strip(),
    )


async def baixar_imagem(url: str | None, timeout: float) -> str | None:
    """Imagem como data URL, ou None se não houver ou o download falhar."""
    if not url or not url.startswith("https://"):
        return None
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True,
                                     headers={"User-Agent": "Mozilla/5.0"}) as http:
            resp = await http.get(url)
            resp.raise_for_status()
    except httpx.HTTPError as e:
        log.info("Imagem indisponível (%s); estimando sem ela.", e)
        return None
    tipo = resp.headers.get("Content-Type", "").split(";")[0]
    if not tipo.startswith("image/") or len(resp.content) > MAX_IMAGEM_BYTES:
        return None
    return f"data:{tipo};base64,{base64.b64encode(resp.content).decode()}"


async def estimar(backend: Backend, settings: Settings, candidate: MealCandidate,
                  opcoes: list[str] | None) -> NutritionResult:
    ilustrativa = foto_ilustrativa(candidate)
    imagem = None if ilustrativa else await baixar_imagem(candidate.image_url, settings.nutrition_timeout_seconds)
    resposta = await backend.json(
        nome="estimativa_calorias", schema=SCHEMA_ESTIMATIVA, instrucoes=INSTRUCOES_ESTIMATIVA, imagem=imagem,
        texto="Estime as calorias deste item.\n\n" + montar_prompt(candidate, opcoes),
    )
    dados = resposta.dados
    suposicoes = list(dados["suposicoes"])
    if ilustrativa:
        suposicoes.append("Foto ilustrativa: não foi usada para medir a porção.")
    elif candidate.image_url and not imagem:
        suposicoes.append("Imagem indisponível: estimativa feita só com o texto.")
    elif imagem and not resposta.usou_imagem:
        suposicoes.append("O modelo não aceitou a imagem: estimativa feita só com o texto.")

    if not dados["suficiente"]:
        return _resultado("unavailable", evidence=dados["justificativa"], assumptions=suposicoes)
    calorias, minimo, maximo = _faixa(dados["calorias"], dados["faixa_min"], dados["faixa_max"])
    return _resultado(
        "ready", method="estimated", calories=calorias, minimum=minimo, maximum=maximo,
        confidence=CONFIANCA[dados["confianca"]], portion_basis=dados["porcao_base"],
        evidence=dados["justificativa"], assumptions=suposicoes,
    )


def criar_cliente(settings: Settings) -> Backend | None:
    return criar_backend(settings)


async def _calcular(client: Backend, settings: Settings, candidate: MealCandidate,
                    opcoes: list[str] | None) -> NutritionResult:
    if settings.nutrition_web_search and client.web_search and restaurante_valido(candidate):
        try:
            publicado = await buscar_publicado(client, candidate, opcoes)
            if publicado:
                return publicado
        except (LLMError, json.JSONDecodeError, KeyError, ValidationError) as e:
            log.warning("Busca nutricional falhou para %s: %s", candidate.name, e)
    return await estimar(client, settings, candidate, opcoes)


async def estimate_nutrition(item: MealCandidate | SelectedItem, settings: Settings,
                             client: Backend | None = None) -> NutritionResult:
    """Calorias de uma unidade do item (a quantidade comprada é aplicada por quem chama)."""
    client = client or criar_cliente(settings)
    if client is None:
        chave = "OPENROUTER_API_KEY" if settings.nutrition_provider == "openrouter" else "OPENAI_API_KEY"
        return _resultado("unavailable", evidence=f"Pipeline nutricional não configurada ({chave} ausente).")

    candidate, opcoes = _partes(item)
    chave = _chave(candidate, opcoes)
    if chave in _cache:
        return _cache[chave]
    try:
        resultado = await asyncio.wait_for(_calcular(client, settings, candidate, opcoes),
                                           settings.nutrition_timeout_seconds)
    except (asyncio.TimeoutError, LLMError, json.JSONDecodeError, KeyError, ValidationError,
            NutritionFailure) as e:
        log.warning("Estimativa nutricional falhou para %s: %s", candidate.name, e)
        return _resultado("error", evidence="Não foi possível obter a informação nutricional agora.")
    _cache[chave] = resultado
    return resultado


def _com_nutricao(rec: Recommendation, nutricao: NutritionResult) -> Recommendation:
    limitacoes = rec.limitations
    if nutricao.state == "ready":
        limitacoes = [l for l in limitacoes if not l.startswith(LIMITACAO_SEM_NUTRICAO)]
    return rec.model_copy(update={"nutrition": nutricao, "limitations": limitacoes})


def _iniciar(rec: Recommendation, settings: Settings, client: Backend) -> asyncio.Task:
    async def uma() -> NutritionResult:
        async with _semaforo(settings):
            return await estimate_nutrition(rec.candidate, settings, client)
    return _tarefa(rec.candidate, uma)


async def enrich_recommendations(recommendations: list[Recommendation], settings: Settings,
                                 client: Backend | None = None,
                                 prazo: float | None = None) -> list[Recommendation]:
    """Inicia a nutrição das recomendações e espera no máximo `prazo` segundos.

    O que não termina a tempo volta como "pending" e continua em segundo plano, indo para o cache;
    refresh_recommendations entrega o resultado quando ficar pronto.
    """
    client = client or criar_cliente(settings)
    if client is None or not recommendations:
        return [_com_nutricao(r, await estimate_nutrition(r.candidate, settings, client)) for r in recommendations]
    tarefas = [_iniciar(rec, settings, client) for rec in recommendations]
    espera = settings.nutrition_response_budget_seconds if prazo is None else prazo
    if espera > 0:
        await asyncio.wait(tarefas, timeout=espera)
    return [_com_nutricao(rec, _estado_da_tarefa(t)) for rec, t in zip(recommendations, tarefas)]


def refresh_recommendations(recommendations: list[Recommendation], settings: Settings,
                            client: Backend | None = None) -> list[Recommendation]:
    """Atualiza, sem esperar, as recomendações ainda "pending".

    Se o cálculo se perdeu (ex.: o servidor reiniciou), ele é iniciado de novo em segundo plano.
    """
    client = client or criar_cliente(settings)
    atualizadas = []
    for rec in recommendations:
        if rec.nutrition.state != "pending" or client is None:
            atualizadas.append(rec)
            continue
        chave = _chave(rec.candidate, None)
        nutricao = _cache.get(chave) or _estado_da_tarefa(_iniciar(rec, settings, client))
        atualizadas.append(_com_nutricao(rec, nutricao))
    return atualizadas


async def estimate_selected(selected: SelectedItem, settings: Settings,
                            client: Backend | None = None, aguardar: bool = True) -> NutritionResult:
    """Calorias do prato montado (com as opções escolhidas), dentro do prazo da resposta HTTP.

    Com aguardar=False só consulta: devolve o resultado se já terminou, ou "pending" se ainda está calculando.
    """
    client = client or criar_cliente(settings)
    if client is None:
        return await estimate_nutrition(selected, settings, client)
    chave = _chave(*_partes(selected))
    if chave in _cache:
        return _cache[chave]
    if not aguardar and chave not in _em_andamento:
        return _resultado("error", evidence="O cálculo foi interrompido. Escolha o prato de novo para recalcular.")
    tarefa = _tarefa(selected.candidate, lambda: estimate_nutrition(selected, settings, client), chave)
    if aguardar:
        await asyncio.wait([tarefa], timeout=settings.nutrition_response_budget_seconds)
    return _estado_da_tarefa(tarefa)


def _tarefa(candidate: MealCandidate, criar, chave: str | None = None) -> asyncio.Task:
    """Reaproveita o cálculo em andamento para o mesmo item, ou inicia um novo em segundo plano."""
    chave = chave or _chave(candidate, None)
    tarefa = _em_andamento.get(chave)
    if tarefa is None or tarefa.done():
        tarefa = asyncio.create_task(criar())
        _em_andamento[chave] = tarefa
        tarefa.add_done_callback(lambda t, c=chave: _em_andamento.pop(c, None) if _em_andamento.get(c) is t else None)
    return tarefa


def _estado_da_tarefa(tarefa: asyncio.Task) -> NutritionResult:
    if not tarefa.done():
        return NutritionResult(state="pending", pipeline_version=PIPELINE_VERSION)
    if tarefa.exception() is not None:
        log.error("Erro inesperado na pipeline nutricional", exc_info=tarefa.exception())
        return _resultado("error", evidence="Não foi possível obter a informação nutricional agora.")
    return tarefa.result()
