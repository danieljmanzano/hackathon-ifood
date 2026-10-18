from __future__ import annotations

import re
import time
from collections import Counter
from datetime import date, timedelta
from typing import Annotated
from typing import TYPE_CHECKING
from uuid import uuid4

from fastapi import APIRouter, Depends, Request, Response
from pydantic import Field, ValidationError

from app.core import logs
from app.core.config import Settings, get_settings
from app.core.exceptions import MacroError
from app.core.search_logs import elapsed_ms, event, trace_search
from app.domain import rank, select
from app.schemas.macro import (
    Address,
    AddressCreated,
    AddressInput,
    Assembly,
    AssemblyLimits,
    CheckoutInput,
    ChatInput,
    CheckoutSummary,
    ConfirmationInput,
    CreateAddressInput,
    GeocodeInput,
    GeocodeResult,
    MealCandidate,
    MealRequest,
    NutritionSearchProgress,
    MerchantSummary,
    Message,
    OrderRecord,
    OrderReview,
    OrderReviewEdit,
    OrderReviewInput,
    SelectedItem,
    SelectionInput,
    Session,
    UserProfile,
    ConsumptionRecord,
    DailyFoodDiary,
    FoodDiaryEntry,
)
if TYPE_CHECKING:
    from app.services.ifood_live import MCPIFood
from app.services.mock_ifood import MockIFood
from app.services import montagem
from app.services.nutrition import enrich_recommendations, estimate_nutrition, estimate_selected, refresh_recommendations
from app.schemas.reviews import Review, ReviewInput, UserTastes
from app.schemas.macro import now
from app.services.review_interpretation import llm_available, schedule_interpretation, sync_taste_review
from app.services.review_recommendations import review_context
from app.services.llm_meal_intent import interpret_intent
from app.services.nutrition_preferences import apply_profile_preferences, update_explanation, meets_explicit_limits
from app.services.nutrition.service import cached_candidates
from app.services.diet_context import GOAL_LABELS, apply_diet_context, build_diet_context, local_date, split_daily_message
from app.services.preferencias import preferencias_do_cliente
from app.services.busca_agente import buscar
from app.services.conversa import montar as montar_conversa, resumo_para_log as resumo_conversa

router = APIRouter()
_mock_provider = MockIFood()
_live_provider: MCPIFood | None = None


async def _com_descricoes(provider, recommendations, address):
    """Troca a descrição vazia da busca pela do getItem antes da nutrição (marca e peso vêm dela)."""
    ler = getattr(provider, "descricoes", None)
    if ler is None or not recommendations:
        return recommendations
    try:
        achadas = await ler([r.candidate for r in recommendations], address)
    except Exception as e:  # a nutrição segue com o que já tem
        logs.aviso("getItem", f"descrições indisponíveis: {logs.curto(e, 120)}")
        return recommendations
    return [r.model_copy(update={"candidate": r.candidate.model_copy(update={"description": achadas[chave]})})
            if (chave := (r.candidate.merchant_id, r.candidate.item_id)) in achadas else r
            for r in recommendations]


ORDINAIS = {"primeiro": 0, "primeira": 0, "1": 0, "segundo": 1, "segunda": 1, "2": 1, "terceiro": 2, "terceira": 2, "3": 2}


def _escolher_alvo(recomendacoes, texto: str, so_se_citado: bool = False) -> tuple[MealCandidate | None, str]:
    """Prato que o cliente quer montar e POR QUE (para o log): nome inteiro, posição, melhor casamento de palavras.

    Sem citação devolve o primeiro da lista, ou None com `so_se_citado` (aí a mensagem pede outra busca).
    """
    from app.services.review_processing import normalized
    pedido = normalized(texto)
    for r in recomendacoes:
        if normalized(r.candidate.name) in pedido:
            return r.candidate, "o nome inteiro do prato aparece na mensagem"
    palavras_do_pedido = re.findall(r"\w+", pedido)
    for palavra in palavras_do_pedido:
        if palavra in ORDINAIS and ORDINAIS[palavra] < len(recomendacoes):
            return recomendacoes[ORDINAIS[palavra]].candidate, f"posição citada (“{palavra}”)"
    palavras = {p for p in palavras_do_pedido if len(p) > 3 and p not in {"pedido", "monte", "pegue", "coloque", "voce", "mostrou"}}
    do_nome = lambda r: set(re.findall(r"\w+", normalized(r.candidate.name)))  # "(Footlong 30cm)" -> footlong, 30cm
    melhor = max(recomendacoes, key=lambda r: len(palavras & do_nome(r)), default=None)
    comuns = palavras & do_nome(melhor) if melhor is not None else set()
    if comuns:
        return melhor.candidate, f"palavras da mensagem no nome do prato: {sorted(comuns)}"
    if so_se_citado or not recomendacoes:
        return None, "nenhuma sugestão mostrada foi citada na mensagem"
    return recomendacoes[0].candidate, "nada citado e sem comida nova: primeira sugestão"


def _alvo_da_montagem(recomendacoes, texto: str, so_se_citado: bool = False) -> MealCandidate | None:
    return _escolher_alvo(recomendacoes, texto, so_se_citado)[0]


def _explicar_decisao(settings: Settings, intent, session: Session, texto: str) -> tuple[MealCandidate | None, str]:
    """Decide entre MONTAR uma sugestão já mostrada e BUSCAR (e talvez montar), e registra o raciocínio no log."""
    nomes = [r.candidate.name for r in session.recommendations]
    conteudo = settings.busca_log_conteudo
    logs.info("decisão", f"interpretação={intent.interpretation_source}"
                         + (f" (caiu por: {intent.fallback_reason})" if intent.fallback_reason else "")
                         + f" · montar_pedido={intent.montar_pedido} · sugestões na sessão={len(nomes)}"
                         + (f" · comida pedida={intent.food_query!r}" if conteudo else "")
                         + (f" · orçamento={intent.budget_cents / 100:.2f}" if intent.budget_cents is not None else "")
                         + (f" · metas={intent.nutrition_preferences.model_dump(exclude_none=True)}"
                            if intent.nutrition_preferences.active else ""))
    if conteudo and nomes:
        logs.info("decisão", f"sugestões mostradas: {nomes}")
    if not intent.montar_pedido:
        logs.info("decisão", "→ BUSCAR: a mensagem não foi lida como pedido de montagem"
                             + (" (a interpretação por regras não reconheceu o verbo de montar)"
                                if intent.interpretation_source == "rules" else ""))
        return None, "buscar"
    if not session.recommendations:
        logs.info("decisão", "→ BUSCAR e depois MONTAR o primeiro resultado: não há sugestões anteriores para montar")
        return None, "buscar_e_montar"
    if intent.motivo_da_decisao and conteudo:
        logs.info("decisão", f"o modelo leu o pedido assim: {logs.curto(intent.motivo_da_decisao, 240)}")
    escolhido = next((r.candidate for r in session.recommendations if r.candidate.item_id == intent.alvo_item_id), None) \
        if intent.alvo_item_id else None
    if escolhido is not None:
        logs.info("decisão", f"→ MONTAR sugestão já mostrada «{logs.curto(escolhido.name, 60)}» ({escolhido.merchant_name}): "
                             "o modelo escolheu este alvo entre as sugestões")
        return escolhido, "montar"
    if intent.alvo_item_id:
        logs.aviso("decisão", "o modelo indicou um id que não está nas sugestões; usando o casamento de palavras")
    alvo, porque = _escolher_alvo(session.recommendations, texto, so_se_citado=bool(intent.food_query.strip()))
    if alvo is None:
        logs.info("decisão", f"→ BUSCAR e depois MONTAR o primeiro resultado: {porque}, e a mensagem pede comida nova")
        return None, "buscar_e_montar"
    logs.info("decisão", f"→ MONTAR sugestão já mostrada «{logs.curto(alvo.name, 60)}» ({alvo.merchant_name}): {porque}")
    return alvo, "montar"


def _limites_da_montagem(intent, session: Session, alvo: MealCandidate) -> AssemblyLimits:
    """Limites ditos agora; o que o cliente não repetiu vem da montagem anterior do mesmo prato ("agora até 600 kcal")."""
    antes = session.assembly.limits if session.assembly and session.assembly.candidate \
        and session.assembly.candidate.item_id == alvo.item_id else AssemblyLimits()
    novo = intent.nutrition_preferences
    campos = {c: getattr(novo, c) if getattr(novo, c) is not None else getattr(antes.nutrition, c)
              for c in ("max_calories", "min_protein_g", "max_carbs_g", "max_fat_g")}
    return AssemblyLimits(max_price_cents=intent.budget_cents if intent.budget_cents is not None else antes.max_price_cents,
                          nutrition=novo.model_copy(update=campos))


def _texto_dos_limites(l: AssemblyLimits) -> str:
    n, partes = l.nutrition, []
    if l.max_price_cents is not None:
        partes.append(f"preço até R$ {l.max_price_cents / 100:.2f}".replace(".", ","))
    for rotulo, v, un in (("até", n.max_calories, "kcal"), ("proteína mínima de", n.min_protein_g, "g"),
                          ("carboidrato até", n.max_carbs_g, "g"), ("gordura até", n.max_fat_g, "g")):
        if v is not None:
            partes.append(f"{rotulo} {v:g} {un}" if rotulo == "até" else f"{rotulo} {v:g} {un}")
    return ", ".join(partes) or "sem limites numéricos"


async def _iniciar_montagem(request: Request, session: Session, provider, settings: Settings, intent, alvo: MealCandidate,
                            payload: MealRequest, com_usuario: bool) -> Session:
    """Abre o prato, registra a montagem e a deixa rodando em segundo plano (GET /assembly acompanha)."""
    detalhe = await provider.item(alvo.merchant_id, alvo.item_id, session.address)
    limites = _limites_da_montagem(intent, session, alvo)
    assembly = Assembly(candidate=detalhe, limits=limites)
    aviso = (f"Vou montar o pedido de {detalhe.name} ({detalhe.merchant_name}) com: {_texto_dos_limites(limites)}. "
             "Acompanhe os passos aqui; no final você confere e continua.")

    def update(s: Session):
        s.assembly = assembly
        s.selected = s.summary = None
        s.last_chat_action = "assembly"
        novas = ([Message(role="user", text=payload.text)] if com_usuario else []) + [Message(role="assistant", text=aviso)]
        s.messages = (s.messages + novas)[-40:]

    resultado = mutate_session(request, session, update)
    montagem.iniciar(request.app.state.db, settings, resultado.id, assembly.id, detalhe, limites, resultado.profile,
                     payload.restrictions, lambda sel: estimate_nutrition(sel, settings), payload.text)
    return resultado


def get_provider(settings: Settings = Depends(get_settings)):
    """Modo live usa o MCP real do iFood; mock usa o catálogo fictício."""
    global _live_provider
    if settings.ifood_mode != "live":
        return _mock_provider
    if _live_provider is None:
        from app.services.ifood_live import MCPIFood

        _live_provider = MCPIFood(settings)
    return _live_provider


def live_only(provider, feature: str):
    """Restaurantes próximos, cardápio e cadastro de endereço só existem no iFood real."""
    if not hasattr(provider, feature):
        raise MacroError("Disponível somente no modo live (IFOOD_MODE=live).", 409)


def offered(session: Session, merchant_id: str, item_id: str) -> bool:
    """Item veio da busca atual ou do cardápio aberto."""
    return any(
        (r.candidate.merchant_id, r.candidate.item_id) == (merchant_id, item_id)
        for r in session.recommendations
    ) or (session.menu_merchant_id == merchant_id and item_id in session.menu_item_ids)


def current_session(request: Request, settings: Settings = Depends(get_settings)) -> Session:
    db = request.app.state.db
    session = db.get(request.cookies.get("macro_session", ""))
    if session is None or session.mode != settings.ifood_mode:
        raise MacroError("Sua sessão expirou ou o modo mudou. Recarregue a página.", 401)
    return session


def editable(session: Session) -> None:
    if session.order:
        raise MacroError("Este pedido já foi confirmado. Inicie uma nova sessão para outro pedido.")


def mutate_session(request: Request, snapshot: Session, operation) -> Session:
    db = request.app.state.db
    with db.transaction() as connection:
        session = db.get(snapshot.id, connection)
        if session != snapshot:
            raise MacroError("A sessão mudou em outra aba. Atualize antes de continuar.")
        operation(session)
        db.save(session, connection)
        return session


@router.get("/assembly", response_model=Session)
def assembly_status(request: Request, session: Session = Depends(current_session)):
    """Progresso da montagem. Se o servidor reiniciou no meio, encerra como falha em vez de deixar a UI esperando."""
    a = session.assembly
    if a is None or a.state != "running" or montagem.em_andamento(a.id):
        return session

    def perdeu(s: Session):
        if s.assembly and s.assembly.id == a.id and s.assembly.state == "running":
            s.assembly.state = "failed"
            s.assembly.message = "A montagem foi interrompida. Monte o seu pedido pela tela."
    return mutate_session(request, session, perdeu)


@router.get("/catalog/enrichment/status")
def enrichment_status(settings: Settings = Depends(get_settings)):
    from app.storage.catalog import CatalogStore
    return {**CatalogStore(settings.database_path).status(),
            "enabled": settings.catalog_enrichment_enabled and settings.ifood_mode == "live",
            "reviews_simulated": settings.live_mock_reviews,
            "limits": {"calls_per_day": settings.catalog_calls_per_day,
                       "products_per_day": settings.catalog_products_per_day,
                       "calls_per_product": settings.catalog_calls_per_product,
                       "products_per_search": settings.catalog_products_per_search}}


@router.get("/health")
def health(settings: Settings = Depends(get_settings)):
    return {"status": "ok", **settings.public_status()}


@router.get("/session", response_model=Session)
def session(request: Request, response: Response, settings: Settings = Depends(get_settings)):
    db = request.app.state.db
    existing = db.get(request.cookies.get("macro_session", ""))
    if existing and existing.mode == settings.ifood_mode:
        return existing
    identity = str(uuid4())
    created = Session(id=identity, mode=settings.ifood_mode, profile=UserProfile(id=identity))
    db.save(created)
    review_context(db, created.profile.id, created.mode == "mock", created.profile)
    response.set_cookie(
        "macro_session",
        identity,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 7,
    )
    return created


@router.get("/integration/diagnostic")
async def diagnostic(
    session: Session = Depends(current_session),
    provider: MockIFood = Depends(get_provider),
):
    return await provider.diagnostic()


async def available_addresses(request: Request, session: Session, provider) -> list[Address]:
    """Endereços do iFood; no mock, o fixo de demonstração mais os cadastrados localmente."""
    found = await provider.addresses()
    if provider.simulated:
        found += request.app.state.db.mock_addresses(session.profile.id)
    return found


@router.get("/addresses", response_model=list[Address])
async def addresses(
    request: Request,
    session: Session = Depends(current_session),
    provider: MockIFood = Depends(get_provider),
):
    return await available_addresses(request, session, provider)


@router.post("/addresses/geocode", response_model=GeocodeResult)
async def geocode(
    payload: GeocodeInput,
    session: Session = Depends(current_session),
    provider: MockIFood = Depends(get_provider),
):
    """Etapa 1 do cadastro: localiza o endereço digitado. Nada é salvo ainda."""
    editable(session)
    live_only(provider, "geocode")
    return await provider.geocode(payload.address)


@router.post("/addresses", response_model=AddressCreated)
async def create_address(
    payload: CreateAddressInput,
    request: Request,
    session: Session = Depends(current_session),
    provider: MockIFood = Depends(get_provider),
):
    """Etapa 2: salva o candidato confirmado (na conta do iFood ou, no mock, localmente) e já o seleciona."""
    editable(session)
    if provider.simulated:
        created = provider.new_address(payload)
        request.app.state.db.save_mock_address(session.profile.id, created)
        found = await available_addresses(request, session, provider)
    else:
        live_only(provider, "create_address")
        before = {a.id for a in await provider.addresses()}
        new_id = await provider.create_address(payload)
        found = await provider.addresses()
        created = next((a for a in found if a.id == new_id), None) or next(
            (a for a in found if a.id not in before), None
        )
        if created is None:
            raise MacroError("Endereço salvo no iFood, mas ainda não apareceu na lista. Recarregue os endereços.", 502)

    def update(s: Session):
        s.nutrition_search = None
        s.address = created
        s.selected = None
        s.summary = None
        s.recommendations = []

    return AddressCreated(session=mutate_session(request, session, update), addresses=found)


@router.put("/session/address", response_model=Session)
async def set_address(
    payload: AddressInput,
    request: Request,
    session: Session = Depends(current_session),
    provider: MockIFood = Depends(get_provider),
):
    editable(session)
    address = next((a for a in await available_addresses(request, session, provider) if a.id == payload.address_id), None)
    if address is None:
        raise MacroError("Selecione um endereço da lista atual.", 422)

    def update(s: Session):
        s.nutrition_search = None
        s.address = address
        s.selected = None
        s.summary = None
        s.recommendations = []

    return mutate_session(request, session, update)


@router.put("/profile", response_model=Session)
def update_profile(
    payload: UserProfile,
    request: Request,
    session: Session = Depends(current_session),
):
    if payload.id != session.id:
        raise MacroError("Perfil não pertence à sessão.", 403)

    def update(s: Session):
        s.nutrition_search = None
        s.profile = payload
        s.pending_preference_update = None

    updated = mutate_session(request, session, update)
    review_context(request.app.state.db, updated.profile.id, updated.mode == "mock", updated.profile)
    return updated


@router.post("/search", response_model=Session)
async def search(
    payload: MealRequest,
    request: Request,
    response: Response,
    session: Session = Depends(current_session),
    provider: MockIFood = Depends(get_provider),
    settings: Settings = Depends(get_settings),
):
    inicio = time.monotonic()  # o laço da busca respeita o prazo total (o frontend desiste aos 30 s)
    with trace_search(session.mode) as trace:
        response.headers["X-Search-Id"] = trace.id
        editable(session)
        if session.nutrition_search and session.nutrition_search.state == "pending":
            session = mutate_session(request, session, lambda s: setattr(s, "nutrition_search", None))
        if session.address is None:
            raise MacroError("Selecione o endereço antes de buscar.", 422)
        trace.stage = "diet_context"
        diet_context, meal_text = build_diet_context(
            session.profile, request.app.state.db.food_entries(session.profile.id),
            request.app.state.db.consumption(session.profile.id), settings.timezone, message=payload.text,
        )
        has_diet_context = bool(diet_context.goal or diet_context.details or diet_context.meal_count
                                or any(v is not None for v in diet_context.targets.model_dump().values()))
        event("diet.ready", has_goal=diet_context.goal is not None, entry_count=diet_context.meal_count,
              known_counts=diet_context.known_counts)
        trace.stage = "intent"
        started = time.perf_counter()
        # O agente lê as últimas mensagens e a busca anterior para entender "mais barato", "outra opção"...
        conversa = montar_conversa(session, settings)
        event("conversation.ready", **resumo_conversa(conversa))
        try:
            interpreted = await interpret_intent(payload.model_copy(update={"text": meal_text}), settings,
                                                diet_context=diet_context if has_diet_context else None,
                                                conversa=conversa, preferencias=preferencias_do_cliente(session.profile))
            intent = apply_profile_preferences(apply_diet_context(interpreted, diet_context, meal_text), session.profile)
        except (ValueError, ValidationError):
            raise MacroError("Os limites nutricionais se contradizem. Confira os mínimos e máximos do pedido e das preferências.", 422) from None
        event("intent.ready", source=intent.interpretation_source, goals=intent.goals,
              fallback_reason=intent.fallback_reason, duration_ms=elapsed_ms(started))
        # "pegue o footlong de 30cm": se cita uma das sugestões já mostradas (ou não pede comida nova), monta ela
        # sem nova busca; com comida nova, busca e monta o primeiro resultado. O raciocínio vai para o log.
        alvo, caminho = _explicar_decisao(settings, intent, session, payload.text)
        if alvo is not None:
            return await _iniciar_montagem(request, session, provider, settings, intent, alvo, payload, True)
        nutritional = intent.nutrition_preferences.active
        batch_mode = nutritional and session.mode == "live" and settings.catalog_enrichment_enabled
        paging = {}

        async def first_page(queries, address, budget, cuisine, refinements):
            page = await provider.search_page(queries, address, budget, cuisine, refinements)
            paging.clear()
            paging.update({"cursor": page["cursor"], "refinements": refinements})
            return page["candidates"]
        avaliacoes = {}

        def contexto_de_avaliacoes():
            """Calculado depois da busca no catálogo (ordem dos eventos) e uma vez só, mesmo com várias rodadas."""
            if "contexto" not in avaliacoes:
                trace.stage = "reviews"
                started = time.perf_counter()
                ctx = review_context(request.app.state.db, session.profile.id, session.mode == "mock", session.profile)
                event("reviews.ready", history_count=len(ctx.history), community_count=len(ctx.community),
                      processed_count=len(ctx.processed), duration_ms=elapsed_ms(started))
                avaliacoes["contexto"] = ctx
            return avaliacoes["contexto"]

        def prepare_catalog(found):
            ctx = contexto_de_avaliacoes()
            if session.mode == "live" and settings.live_mock_reviews:
                from app.services.catalog_reviews import attach_reviews
                attach_reviews(ctx, found[:10], settings, request.app.state.db, session.profile)
            return {
                "nutrition_by_item": cached_candidates(found, settings) if nutritional and not batch_mode else {},
                "limit": 15 if batch_mode else (12 if nutritional else 3),
                "strict_nutrition": not batch_mode,
                "ignore_nutrition": batch_mode,
            }

        # Busca com laço de agente (app/services/busca_agente.py): sem resultado, um modelo replaneja ou explica.
        # O ranking nutricional do catálogo (cache) entra por `rank_extra`, a cada rodada.
        resultado = await buscar(
            payload, session, provider, settings, intent, contexto_de_avaliacoes, inicio, texto_pedido=meal_text,
            conversa=conversa, trace=trace,
            rank_extra=prepare_catalog,
            catalog_search=first_page if batch_mode and hasattr(provider, "search_page") else None)
        candidates, budget, recommendations = resultado.candidates, resultado.budget, resultado.recommendations
        nutrition_by_item = resultado.extra.get("nutrition_by_item", {})
        aviso_vazio, aviso_adaptacao = resultado.aviso_vazio, resultado.aviso_adaptacao
        trace.stage = "nutrition"
        started = time.perf_counter()
        batch_pool = recommendations
        batch_pending = batch_mode and bool(batch_pool or paging.get("cursor"))
        if batch_mode:
            recommendations = []
        else:
            recommendations = await _com_descricoes(provider, recommendations, session.address)
            recommendations = await enrich_recommendations(
                recommendations, settings, prazo=settings.nutrition_search_budget_seconds
            )

        if nutritional and not batch_mode:
            # Estima um conjunto limitado, compara com todo o catálogo já em cache
            # e só então escolhe os três pratos. Não envia o catálogo inteiro ao LLM.
            nutrition_by_item.update({(r.candidate.merchant_id, r.candidate.item_id): r.nutrition
                                      for r in recommendations})
            event("nutrition.ranking", pool_count=len(recommendations),
                  known_count=sum(n.state == "ready" for n in nutrition_by_item.values()),
                  goal_count=len(intent.nutrition_preferences.goals))
            trace.stage = "ranking"
            recommendations = rank(candidates, payload, session.profile, budget, contexto_de_avaliacoes(),
                                   session.recent_recommendations, intent=intent,
                                   nutrition_by_item=nutrition_by_item, strict_nutrition=True)
            trace.stage = "nutrition"

        event("nutrition.prepared", states=dict(Counter(r.nutrition.state for r in recommendations)),
              duration_ms=elapsed_ms(started))

        def update(s: Session):
            s.assembly = None
            s.nutrition_search = NutritionSearchProgress(id=str(uuid4())) if batch_pending else None
            s.budget_cents = budget
            s.request_intent = intent
            s.recommendations = recommendations
            s.recent_recommendations = (
                s.recent_recommendations
                + [(r.candidate.merchant_id, r.candidate.item_id) for r in recommendations]
            )[-18:]
            s.selected = None
            s.summary = None
            message = (
                ("Busquei opções considerando: " + ", ".join(intent.labels) + ". Confira os detalhes de cada sugestão."
                 if intent.labels else "Encontrei estas opções. Escolha um prato para ver os complementos.")
                if recommendations
                else aviso_vazio  # por que não houve resultado (app/services/busca_agente.py)
            )
            if batch_pending:
                message = "Estou avaliando a nutrição em lotes de três, até encontrar três opções adequadas ou testar 15 candidatos."
            if recommendations and aviso_adaptacao:
                message = aviso_adaptacao + " " + message
            if recommendations and intent.context_summary:
                message = intent.context_summary + " " + message
            s.messages = (
                s.messages
                + [
                    Message(role="user", text=payload.text),
                    Message(role="assistant", text=message),
                ]
            )[-40:]

        trace.stage = "session"
        result = mutate_session(request, session, update)
        if intent.montar_pedido and result.recommendations and not batch_pending:
            # Pediu a comida e a montagem juntas: monta o primeiro prato encontrado.
            result = await _iniciar_montagem(request, result, provider, settings, intent,
                                             result.recommendations[0].candidate, payload, False)
        if batch_pending:
            from app.services.nutrition_batch_search import enqueue
            enqueue(result, payload, candidates, batch_pool, resultado.queries, paging, settings)
        trace.result_count = len(result.recommendations)
        return result


@router.post("/chat", response_model=Session)
async def chat(payload: ChatInput, request: Request, response: Response,
               session: Session = Depends(current_session), provider: MockIFood = Depends(get_provider),
               settings: Settings = Depends(get_settings)):
    """Guarda o contexto relatado na conversa; pedidos de comida seguem o motor existente."""
    from app.services.preference_updates import interpret_update
    preference_update = await interpret_update(payload.text, session.profile, settings,
                                              pending=session.pending_preference_update, messages=session.messages)
    if preference_update is not None:
        def save_preferences(s: Session):
            s.profile = preference_update.profile
            s.pending_preference_update = preference_update.pending
            s.nutrition_search = None
            s.last_chat_action = 'preferences'
            s.messages = (s.messages + [Message(role='user', text=payload.text),
                          Message(role='assistant', text=preference_update.message)])[-40:]
        updated = mutate_session(request, session, save_preferences)
        if updated.profile != session.profile:
            review_context(request.app.state.db, updated.profile.id, updated.mode == 'mock', updated.profile)
        return updated
    if session.pending_preference_update:
        session = mutate_session(request, session, lambda s: setattr(s, 'pending_preference_update', None))
    if session.nutrition_search and session.nutrition_search.state == "pending":
        session = mutate_session(request, session, lambda s: setattr(s, "nutrition_search", None))
    meal_text, foods, goal = split_daily_message(payload.text)
    if goal:
        def update_goal(s: Session):
            s.profile.diet_plan = s.profile.diet_plan.model_copy(update={"goal": goal})
        session = mutate_session(request, session, update_goal)
    for index, description in enumerate(foods):
        request.app.state.db.save_food_entry(session.profile.id, FoodDiaryEntry(
            id=f"chat-{payload.message_id}-{index}", description=description,
        ))
    # Informar o objetivo ou o que comeu não dispara uma compra/busca involuntária.
    remaining_words = set(meal_text.strip(' ,;.!').split()) - {'e', 'eu', 'quero', 'meu', 'objetivo', 'de', 'para'}
    context_only = bool(foods or goal) and (meal_text == 'refeição' or not remaining_words)
    if context_only:
        acknowledgements = []
        if goal:
            acknowledgements.append(f"Objetivo salvo: {GOAL_LABELS[goal]}.")
        if foods:
            acknowledgements.append("Registrei o que você informou que comeu hoje. Vou considerar isso nas próximas sugestões.")
        def acknowledge(s: Session):
            s.last_chat_action = 'context'
            s.messages = (s.messages + [Message(role='user', text=payload.text),
                          Message(role='assistant', text=' '.join(acknowledgements) + ' O que você gostaria de comer agora?')])[-40:]
        return mutate_session(request, session, acknowledge)
    if session.order:
        session = new_order(request, session)
    result = await search(MealRequest(text=meal_text, budget_cents=payload.budget_cents,
                                      restrictions=payload.restrictions,
                                      nutrition_preferences=payload.nutrition_preferences),
                          request, response, session, provider, settings)
    def mark_search(s: Session):
        s.last_chat_action = 'assembly' if s.assembly and s.assembly.state == 'running' else 'search'
        for i in range(len(s.messages) - 1, -1, -1):  # a montagem acrescenta mensagens depois da do usuário
            if s.messages[i].role == 'user':
                s.messages[i] = Message(role='user', text=payload.text)
                break
    return mutate_session(request, result, mark_search)


@router.post("/session/new-order", response_model=Session)
def new_order(request: Request, session: Session = Depends(current_session)):
    if session.order and session.order.review and session.order.review.interpretation_state == 'pending':
        raise MacroError("Aguarde a interpretação da avaliação antes de iniciar outro pedido.", 409)
    def reset(s: Session):
        s.selected = s.summary = s.order = s.request_intent = None
        s.assembly = None
        s.nutrition_search = None
        s.last_chat_action = None
        s.recommendations = []
        s.menu_merchant_id = None
        s.menu_item_ids = []
        s.messages = (s.messages + [Message(role='assistant', text='Vamos encontrar sua próxima refeição. Seu objetivo e suas preferências continuam salvos.')])[-40:]
    return mutate_session(request, session, reset)


@router.get("/consumption", response_model=list[ConsumptionRecord])
def consumption(request: Request, session: Session = Depends(current_session)):
    return request.app.state.db.consumption(session.profile.id)


@router.put("/consumption", response_model=list[ConsumptionRecord])
def save_consumption(payload: Annotated[list[ConsumptionRecord], Field(max_length=500)],
                     request: Request, session: Session = Depends(current_session)):
    keys = {(e.order_id, e.item_id) for e in payload}
    if len(keys) != len(payload):
        raise MacroError("Há registros duplicados para o mesmo prato e pedido.", 422)
    if any(e.consumed_at > now() + timedelta(minutes=5) for e in payload):
        raise MacroError("O consumo precisa ter ocorrido antes de agora.", 422)
    request.app.state.db.replace_consumption(session.profile.id, payload)
    return payload


@router.get("/daily-context", response_model=DailyFoodDiary)
def daily_context(request: Request, on_date: date | None = None,
                  session: Session = Depends(current_session), settings: Settings = Depends(get_settings)):
    entries = request.app.state.db.food_entries(session.profile.id)
    context, _ = build_diet_context(session.profile, entries,
                                    request.app.state.db.consumption(session.profile.id),
                                    settings.timezone, on_date=on_date)
    return DailyFoodDiary(entries=sorted([e for e in entries if local_date(e.consumed_at, settings.timezone) == context.date],
                                        key=lambda e: e.consumed_at), context=context)


@router.post("/food-diary", response_model=FoodDiaryEntry)
def add_food(payload: FoodDiaryEntry, request: Request, session: Session = Depends(current_session)):
    if payload.consumed_at > now() + timedelta(minutes=5):
        raise MacroError("Registre apenas alimentos já consumidos.", 422)
    entries = request.app.state.db.food_entries(session.profile.id)
    if len(entries) >= 500 and not any(e.id == payload.id for e in entries):
        raise MacroError("O diário chegou ao limite de 500 registros. Remova registros antigos para continuar.", 422)
    request.app.state.db.save_food_entry(session.profile.id, payload)
    return payload


@router.delete("/food-diary/{entry_id}", status_code=204)
def remove_food(entry_id: str, request: Request, session: Session = Depends(current_session)):
    request.app.state.db.delete_food_entry(session.profile.id, entry_id)


@router.get("/reviews/me", response_model=list[Review])
def my_reviews(request: Request, session: Session = Depends(current_session)):
    return review_context(request.app.state.db, session.profile.id, session.mode == "mock", session.profile).history


@router.get("/profile/tastes", response_model=UserTastes)
def my_tastes(request: Request, session: Session = Depends(current_session)):
    return review_context(request.app.state.db, session.profile.id, session.mode == "mock", session.profile).tastes


@router.put("/reviews", response_model=Review)
async def save_review(
    payload: ReviewInput,
    request: Request,
    session: Session = Depends(current_session),
    provider: MockIFood = Depends(get_provider),
):
    # Apenas itens conhecidos pela sessão podem receber avaliações. Não implica compra verificada.
    selected = session.selected
    history = review_context(request.app.state.db, session.profile.id, session.mode == "mock").history
    previously_reviewed = any(
        (r.merchant_id, r.item_id) == (payload.merchant_id, payload.item_id) for r in history
    )
    if not previously_reviewed and not offered(session, payload.merchant_id, payload.item_id) and not (
        selected and (selected.candidate.merchant_id, selected.candidate.item_id)
        == (payload.merchant_id, payload.item_id)
    ):
        raise MacroError("Escolha um item da busca ou do cardápio para avaliar.", 422)
    if session.address is None:
        raise MacroError("Selecione um endereço antes de avaliar.", 422)
    candidate = await provider.item(payload.merchant_id, payload.item_id, session.address)
    review = Review(
        **payload.model_dump(), id=str(uuid4()), user_id=session.profile.id,
        created_at=now(), simulated=session.mode == "mock",
        merchant_name=candidate.merchant_name, item_name=candidate.name,
    )
    request.app.state.db.save_review(review)
    review_context(request.app.state.db, session.profile.id, session.mode == "mock", session.profile)
    return review


@router.get("/merchants", response_model=list[MerchantSummary])
async def merchants(
    session: Session = Depends(current_session),
    provider: MockIFood = Depends(get_provider),
):
    if session.address is None:
        raise MacroError("Selecione o endereço antes de ver os restaurantes.", 422)
    live_only(provider, "merchants")
    return await provider.merchants(session.address)


@router.get("/merchants/{merchant_id}/menu", response_model=list[MealCandidate])
async def menu(
    merchant_id: str,
    request: Request,
    session: Session = Depends(current_session),
    provider: MockIFood = Depends(get_provider),
):
    if session.address is None:
        raise MacroError("Selecione o endereço antes de ver o cardápio.", 422)
    live_only(provider, "menu")
    items = await provider.menu(merchant_id, session.address)

    def update(s: Session):
        s.menu_merchant_id = merchant_id
        s.menu_item_ids = [i.item_id for i in items]

    mutate_session(request, session, update)
    return items


@router.get("/recommendations/nutrition", response_model=Session)
async def recommendations_nutrition(  # async: reiniciar um cálculo perdido exige o loop de eventos (create_task)
    request: Request,
    session: Session = Depends(current_session),
    settings: Settings = Depends(get_settings),
):
    """Entrega as calorias das recomendações que estavam "pending" quando a busca respondeu."""
    if session.nutrition_search is not None:
        return session
    if not any(r.nutrition.state == "pending" for r in session.recommendations):
        return session
    updated = refresh_recommendations(session.recommendations, settings)
    if session.request_intent:
        updated = [update_explanation(before, after, session.request_intent.nutrition_preferences)
                   for before, after in zip(session.recommendations, updated)]
        updated = [r for r in updated if meets_explicit_limits(r.nutrition, session.request_intent.nutrition_preferences) is not False]
    if [r.nutrition for r in updated] == [r.nutrition for r in session.recommendations]:
        return session
    ids = [(r.candidate.merchant_id, r.candidate.item_id) for r in session.recommendations]

    def update(s: Session):
        # Só aplica se a busca não mudou enquanto isso.
        if [(r.candidate.merchant_id, r.candidate.item_id) for r in s.recommendations] == ids:
            s.recommendations = updated
            if not updated:
                s.messages.append(Message(role="assistant", text="As estimativas disponíveis ficaram fora dos limites nutricionais informados. Posso buscar outras opções; seus limites foram mantidos."))

    return mutate_session(request, session, update)


@router.get("/items/{merchant_id}/{item_id}")
async def item(
    merchant_id: str,
    item_id: str,
    session: Session = Depends(current_session),
    provider: MockIFood = Depends(get_provider),
):
    if not session.address or not offered(session, merchant_id, item_id):
        raise MacroError("Escolha um item da busca atual ou do cardápio aberto.", 422)
    return await provider.item(merchant_id, item_id, session.address)


@router.put("/selection", response_model=Session)
async def selection(
    payload: SelectionInput,
    request: Request,
    session: Session = Depends(current_session),
    provider: MockIFood = Depends(get_provider),
    settings: Settings = Depends(get_settings),
):
    editable(session)
    if not session.address or not offered(session, payload.merchant_id, payload.item_id):
        raise MacroError("Escolha um item da busca atual ou do cardápio aberto.", 422)
    candidate = await provider.item(payload.merchant_id, payload.item_id, session.address)
    selected_item = select(candidate, payload)
    # Prato montado: calcula as calorias com a descrição completa e as opções escolhidas.
    selected_item = selected_item.model_copy(
        update={"nutrition": await estimate_selected(selected_item, settings)}
    )

    def update(s: Session):
        s.assembly = None
        s.nutrition_search = None
        s.selected = selected_item
        s.summary = None
        s.messages = (s.messages + [Message(role='user', text=f'Escolhi {selected_item.quantity} unidade(s) de {candidate.name}.'),
                      Message(role='assistant', text='Prato escolhido. Vamos selecionar a entrega e o pagamento.')])[-40:]

    return mutate_session(request, session, update)


@router.post("/selection/preview", response_model=SelectedItem)
async def selection_preview(
    payload: SelectionInput,
    aguardar: bool = True,
    session: Session = Depends(current_session),
    provider: MockIFood = Depends(get_provider),
    settings: Settings = Depends(get_settings),
):
    """Calorias e macros do prato com as opções escolhidas, SEM escolher o prato: a sessão não muda.

    `aguardar=true` inicia o cálculo e espera o prazo da resposta; se ainda estiver "pending", a tela chama de novo com
    `aguardar=false` até terminar (reaproveita o cálculo em andamento ou o resultado já guardado).
    """
    editable(session)
    if not session.address or not offered(session, payload.merchant_id, payload.item_id):
        raise MacroError("Escolha um item da busca atual ou do cardápio aberto.", 422)
    candidate = await provider.item(payload.merchant_id, payload.item_id, session.address)
    selected_item = select(candidate, payload)
    nutrition = await estimate_selected(selected_item, settings, aguardar=aguardar)
    return selected_item.model_copy(update={"nutrition": nutrition})


@router.get("/selection/nutrition", response_model=Session)
async def selection_nutrition(
    request: Request,
    session: Session = Depends(current_session),
    settings: Settings = Depends(get_settings),
):
    """Atualiza a estimativa do prato escolhido quando ela ainda estava "pending"."""
    if not session.selected or session.selected.nutrition.state != "pending":
        return session
    nutrition = await estimate_selected(session.selected, settings, aguardar=False)
    if nutrition.state == "pending":
        return session

    def update(s: Session):
        if s.selected and s.selected.nutrition.state == "pending":
            s.selected = s.selected.model_copy(update={"nutrition": nutrition})

    return mutate_session(request, session, update)


@router.get("/checkout/choices")
def choices(
    session: Session = Depends(current_session),
    provider: MockIFood = Depends(get_provider),
    settings: Settings = Depends(get_settings),
):
    if not provider.simulated or settings.ifood_mode != "mock":
        raise MacroError("Checkout real bloqueado até validar ferramentas e ambiente de teste.", 403)
    return provider.checkout_choices()


@router.post("/checkout/review", response_model=Session)
def review(
    payload: CheckoutInput,
    request: Request,
    session: Session = Depends(current_session),
    provider: MockIFood = Depends(get_provider),
    settings: Settings = Depends(get_settings),
):
    if not provider.simulated or settings.ifood_mode != "mock":
        raise MacroError("Checkout real bloqueado até validar ferramentas e ambiente de teste.", 403)
    editable(session)
    if not session.selected or not session.address:
        raise MacroError("Selecione prato, complementos e endereço antes de revisar.", 422)
    available_choices = provider.checkout_choices()
    delivery = next((d for d in available_choices["delivery"] if d.id == payload.delivery_id), None)
    payment = next((p for p in available_choices["payment"] if p.id == payload.payment_id), None)
    if not delivery or not payment:
        raise MacroError("Entrega ou pagamento não pertence às opções disponíveis.", 422)

    def update(s: Session):
        subtotal = s.selected.unit_total_cents * s.selected.quantity
        s.summary = CheckoutSummary(
            cart_id=s.summary.cart_id if s.summary else f"demo-cart-{uuid4()}",
            items=[s.selected],
            address=s.address,
            delivery=delivery,
            payment=payment,
            subtotal_cents=subtotal,
            total_cents=subtotal + delivery.fee_cents,
            version=str(uuid4()),
            simulated=True,
        )
        total = f'R$ {s.summary.total_cents / 100:.2f}'.replace('.', ',')
        s.messages = (s.messages + [Message(role='user', text=f'Entrega: {delivery.label}. Pagamento: {payment.label}.'),
                      Message(role='assistant', text=f'Confira os itens e o total de {total}. O pedido ainda não foi confirmado.')])[-40:]

    return mutate_session(request, session, update)


@router.post("/checkout/confirm", response_model=Session)
async def confirm(
    payload: ConfirmationInput,
    request: Request,
    settings: Settings = Depends(get_settings),
):
    if settings.ifood_mode != "mock":
        raise MacroError("Checkout real bloqueado até validar ferramentas e ambiente de teste.", 403)
    db = request.app.state.db
    with db.transaction() as connection:
        s = db.get(request.cookies.get("macro_session", ""), connection)
        if not s or s.mode != "mock":
            raise MacroError("Sessão inválida. Recarregue a página.", 401)
        if not s.summary or payload.version != s.summary.version:
            raise MacroError("O resumo mudou. Revise o pedido e confirme a nova versão.")
        created = not s.order
        if created:
            given = payload.review if payload.review and not payload.review.empty else None
            s.order = OrderRecord(
                id=f"demo-order-{uuid4()}",
                cart_id=s.summary.cart_id,
                status="submitted",
                simulated=True,
                review=given and OrderReview(
                    rating=given.rating, comment=given.comment,
                    # Só há o que interpretar quando o usuário escreveu algo.
                    interpretation_state="pending" if given.comment and llm_available(settings) else "none",
                ),
            )
            s.messages = (s.messages + [Message(role='user', text='Confirmar pedido.'),
                          Message(role='assistant', text='Pedido de demonstração confirmado. Nenhuma cobrança foi realizada. Você pode avaliar sua experiência aqui na conversa.')])[-40:]
            db.save(s, connection)
    # Fora da transação: save_review abre a sua. Só a primeira confirmação grava a avaliação.
    if created and s.order.review:
        # A nota escolhida já vale; a interpretação completa aspectos (e a nota, se faltou) depois.
        sync_taste_review(db, s)
        if s.order.review.interpretation_state == "pending":
            schedule_interpretation(db, s.id, settings)
    return s


@router.get("/checkout/order", response_model=Session)
def order_status(session: Session = Depends(current_session)):
    """Consulta leve para acompanhar a interpretação em segundo plano."""
    return session


@router.put("/checkout/order/review", response_model=Session)
def edit_order_review(
    payload: OrderReviewEdit,
    request: Request,
    session: Session = Depends(current_session),
):
    if not session.order or not session.order.review:
        raise MacroError("Não há avaliação neste pedido para ajustar.", 422)
    if session.order.review.interpretation_state == "pending":
        raise MacroError("Ainda estamos interpretando sua avaliação. Tente de novo em instantes.", 409)

    def update(s: Session):
        s.order.review = s.order.review.model_copy(update={"rating": payload.rating, "aspects": payload.aspects})

    updated = mutate_session(request, session, update)
    sync_taste_review(request.app.state.db, updated)
    return updated


@router.post("/checkout/order/review", response_model=Session)
async def add_order_review(payload: OrderReviewInput, request: Request,
                           session: Session = Depends(current_session), settings: Settings = Depends(get_settings)):
    if not session.order or session.order.status != 'submitted':
        raise MacroError("Confirme o pedido antes de avaliá-lo.", 422)
    if payload.empty:
        raise MacroError("Informe uma nota ou um comentário para avaliar.", 422)
    if session.order.review and session.order.review.interpretation_state == 'pending':
        raise MacroError("Sua avaliação ainda está sendo interpretada.", 409)
    def update(s: Session):
        s.order.review = OrderReview(rating=payload.rating, comment=payload.comment,
                                    interpretation_state='pending' if payload.comment and llm_available(settings) else 'none')
        text = payload.comment or f'Nota do pedido: {payload.rating}/5.'
        s.messages = (s.messages + [Message(role='user', text=text),
                      Message(role='assistant', text='Avaliação salva. Ela será considerada nas próximas sugestões.')])[-40:]
    updated = mutate_session(request, session, update)
    sync_taste_review(request.app.state.db, updated)
    if updated.order.review.interpretation_state == 'pending':
        schedule_interpretation(request.app.state.db, updated.id, settings)
    return updated
