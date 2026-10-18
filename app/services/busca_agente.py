"""Busca com laço de agente: se nada sobrar, um modelo replaneja (ou explica) em vez de um `if` fixo.

    interpretar -> buscar -> ranking -> achou? sim: pronto
                                         não : diagnóstico -> modelo decide ->
                                               buscar_de_novo (consultas novas, talvez sem o orçamento padrão)
                                               desistir (mensagem pensada para o caso)
O código fornece a observação (o diagnóstico) e aplica as guardas; quem decide o que tentar é o modelo
(skill busca_replanejar). Guardas, que valem mesmo se o modelo pedir o contrário:
  - número máximo de replanejamentos e prazo total (o frontend desiste aos 30 s);
  - restrições, alergias e alimentos evitados continuam no ranking (o modelo não os toca);
  - o orçamento que o usuário pediu nunca é relaxado; só o padrão do perfil;
  - consulta já tentada não é repetida;
  - qualquer falha do modelo cai na mensagem fixa de app/services/mensagens_busca.py.
Logs: eventos só com contagens (como o resto da busca, sem texto do usuário). Consultas e respostas dos modelos
só aparecem com BUSCA_LOG_CONTEUDO=true.
"""
import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Callable

from jsonschema import ValidationError as SchemaError, validate

from app.core import logs
from app.core.config import Settings
from app.core.exceptions import AppError
from app.core.search_logs import elapsed_ms, event
from app.domain import rank
from app.schemas.macro import MealCandidate, MealIntent, MealRequest, Recommendation, Session
from app.services import horario
from app.services.llm_texto import chat_completion_fallback as chat_completion
from app.services.mensagens_busca import sem_resultado
from app.services.nutrition.entrada import extrair_json
from app.services.review_processing import normalized
from app.skills import busca_replanejar
from app.skills.comum import pedir_json

TEMPO_MINIMO_PARA_REPLANEJAR = 10  # segundos que precisam sobrar do prazo total (modelo + nova busca)


@dataclass
class ResultadoBusca:
    candidates: list[MealCandidate]
    recommendations: list[Recommendation]
    budget: int | None
    queries: list[str]
    aviso_vazio: str | None = None  # mensagem quando nada sobrou
    aviso_adaptacao: str | None = None  # mensagem quando o replanejamento deu certo
    tentativas: list[dict] = field(default_factory=list)
    extra: dict = field(default_factory=dict)  # o que `rank_extra` devolveu na última rodada (ex.: nutrition_by_item)


def _conteudo(settings: Settings, mensagem: str) -> None:
    """Texto derivado do pedido do usuário: só com BUSCA_LOG_CONTEUDO=true."""
    if settings.busca_log_conteudo:
        logs.info("busca", mensagem)


def _origem_orcamento(intent: MealIntent, session: Session) -> str:
    if intent.budget_cents is not None:
        return "pedido_do_usuario"
    return "padrao_do_perfil" if session.profile.default_budget_cents is not None else "nenhum"


def _resumir(candidates: list[MealCandidate], recomendacoes: int, descartes: dict, queries: list[str],
             cuisine: str | None, budget: int | None) -> dict:
    abertos = [c for c in candidates if c.available]
    mais_barato = min((c.price_cents for c in abertos), default=None)
    return {
        "consultas": queries, "culinaria": cuisine or None,
        "orcamento_reais": budget / 100 if budget is not None else None,
        "itens_encontrados": len(candidates), "itens_abertos": len(abertos),
        "restaurantes_fechados": len({c.merchant_id for c in candidates if not c.available}),
        "mais_barato_aberto_reais": mais_barato / 100 if mais_barato is not None else None,
        "recomendacoes": recomendacoes, "descartes_do_ranking": descartes,
    }


async def _replanejar(settings: Settings, texto: str, agora: dict, budget: int | None, origem: str,
                      tentativas: list[dict], prazo: float, conversa: dict | None = None) -> dict | None:
    """Pergunta ao modelo o próximo passo. None se ele falhar, demorar ou responder fora do formato."""
    diagnostico = {"pedido": texto, "agora": agora,
                   "orcamento": {"valor_reais": budget / 100 if budget is not None else None, "origem": origem},
                   "tentativas": tentativas}
    if conversa:
        diagnostico["conversa"] = conversa
    mensagens = [{"role": "system", "content": busca_replanejar.INSTRUCOES},
                 {"role": "user", "content": pedir_json(busca_replanejar.pedido(diagnostico),
                                                         busca_replanejar.SCHEMA)}]
    started = time.perf_counter()
    try:
        texto_resposta = await asyncio.wait_for(
            chat_completion(mensagens, json_mode=True, temperature=0.2, prazo_primeiro=prazo / 2,
                            log_content=settings.busca_log_conteudo, settings=settings), prazo)
        plano = extrair_json(texto_resposta)
        validate(plano, busca_replanejar.SCHEMA)
    except (asyncio.TimeoutError, AppError, ValueError, SchemaError) as e:
        event("search.replan_failed", level=logging.WARNING, error_type=type(e).__name__,
              duration_ms=elapsed_ms(started))
        return None
    event("search.replan", action=plano["acao"], new_query_count=len(plano["search_queries"]),
          relax_default_budget=plano["relaxar_orcamento_padrao"], has_adaptation_notice=bool(plano["aviso_adaptacao"]),
          duration_ms=elapsed_ms(started))
    _conteudo(settings, f"planejador: {plano['acao']} · diagnóstico: {logs.curto(plano['diagnostico'], 200)} · "
                        f"consultas={plano['search_queries']} · culinária={plano['cuisine'] or '—'}")
    return plano


async def _consultar_catalogo(provider, queries: list[str], address, budget: int | None,
                              cuisine: str | None) -> list[MealCandidate]:
    """Várias consultas de uma vez; provedores que só sabem buscar uma (`search`) recebem a primeira."""
    if hasattr(provider, "search_many"):
        return await provider.search_many(queries, address, budget, cuisine)
    return await provider.search(queries[0], address, budget)


def _mensagem_valida(texto: str | None) -> str | None:
    texto = (texto or "").strip()
    return texto if 20 <= len(texto) <= 600 else None


async def buscar(payload: MealRequest, session: Session, provider, settings: Settings, intent: MealIntent,
                 context, inicio: float, *, texto_pedido: str | None = None, conversa: dict | None = None, trace=None,
                 rank_extra: Callable[[list[MealCandidate]], dict] | None = None) -> ResultadoBusca:
    """`inicio`: time.monotonic() de quando a requisição começou (para respeitar o prazo total).

    `context`: contexto de avaliações, ou uma função que o calcula (chamada depois da busca no catálogo).
    `texto_pedido`: o pedido sem os alimentos já consumidos (o que o planejador deve ler).
    `conversa`: últimas mensagens e busca anterior (app/services/conversa.py), para o planejador entender o contexto.
    `rank_extra(candidatos)`: argumentos a mais do ranking para cada rodada (ranking nutricional, limite).
    """
    texto = texto_pedido if texto_pedido is not None else payload.text
    queries = intent.search_queries or [intent.provider_query]
    cuisine = intent.cuisine
    budget = intent.budget_cents if intent.budget_cents is not None else session.profile.default_budget_cents
    origem = _origem_orcamento(intent, session)
    agora = horario.agora(settings)
    tentativas: list[dict] = []
    tentadas = {normalized(q) for q in queries}
    plano: dict | None = None
    adaptou = False
    extra: dict = {}

    maximo = settings.busca_max_replanejamentos if settings.busca_replanejar else 0
    for rodada in range(1 + maximo):
        if trace is not None:
            trace.stage = "catalog"
        started = time.perf_counter()
        _conteudo(settings, f"rodada {rodada + 1}: consultas ao iFood {queries}"
                            + (f" · culinária: {cuisine}" if cuisine else ""))
        candidates = await _consultar_catalogo(provider, queries, session.address, budget, cuisine)
        event("catalog.completed", provider=type(provider).__name__, candidate_count=len(candidates),
              has_budget=budget is not None, query_terms=sum(len(q.split()) for q in queries),
              query_count=len(queries), round=rodada + 1, duration_ms=elapsed_ms(started))
        revisoes = context() if callable(context) else context  # avaliações: calculadas só depois do catálogo
        if trace is not None:
            trace.stage = "ranking"
        extra = rank_extra(candidates) if rank_extra else {}
        descartes: dict = {}
        recommendations = rank(candidates, payload, session.profile, budget, revisoes,
                               session.recent_recommendations, intent=intent, diagnostico=descartes, **extra)
        tentativas.append(_resumir(candidates, len(recommendations), descartes, queries, cuisine, budget))
        if recommendations:
            aviso = _mensagem_valida(plano and plano.get("aviso_adaptacao")) if adaptou else None
            return ResultadoBusca(candidates, recommendations, budget, queries, aviso_adaptacao=aviso,
                                  tentativas=tentativas, extra=extra)

        restante = settings.busca_prazo_total_segundos - (time.monotonic() - inicio)
        if rodada >= maximo:
            break
        if restante < TEMPO_MINIMO_PARA_REPLANEJAR:
            event("search.replan_skipped", reason="no_time", remaining_seconds=round(restante, 1))
            break
        plano = await _replanejar(settings, texto, agora, budget, origem, tentativas,
                                  min(settings.busca_replanejar_timeout_seconds, restante - 5), conversa)
        if plano is None or plano["acao"] != "buscar_de_novo":
            break
        novas = [q.strip() for q in plano["search_queries"] if q.strip() and normalized(q) not in tentadas][:4]
        if not novas:
            event("search.replan_skipped", reason="no_new_queries")
            break
        tentadas.update(normalized(q) for q in novas)
        queries, adaptou = novas, True
        cuisine = plano["cuisine"].strip() or cuisine
        if plano["relaxar_orcamento_padrao"]:
            if origem == "padrao_do_perfil":
                event("search.budget_relaxed", previous_budget_cents=budget)
                budget = None
            else:
                event("search.budget_relax_refused", level=logging.WARNING, budget_origin=origem)

    fixa = sem_resultado(candidates, budget, [q for t in tentativas for q in t["consultas"]])
    escrita = _mensagem_valida(plano and plano.get("mensagem_se_nada_for_encontrado"))
    return ResultadoBusca(candidates, [], budget, queries, aviso_vazio=escrita or fixa, tentativas=tentativas,
                          extra=extra)
