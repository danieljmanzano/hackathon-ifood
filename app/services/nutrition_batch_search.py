"""Busca nutricional retomável: lotes de 3, até 3 aprovados ou 15 avaliações."""

import asyncio
import logging

from app.core.nutrition_budget import Budget, current_budget
from app.domain import rank
from app.schemas.macro import MealCandidate, MealRequest, NutritionResult
from app.services.catalog_enrichment import job_key
from app.services.nutrition_preferences import LABELS, meets_explicit_limits
from app.storage.catalog import CatalogStore
from app.storage.database import Database

log = logging.getLogger(__name__)
BATCH_SIZE = 3
MAX_CANDIDATES = 15
# Referências de comparação do motor, não metas prescritas ao usuário.
QUALITATIVE = {
    "high_protein": ("protein_g", 30, 20, True),
    "low_carb": ("carbs_g", 40, 65, False),
    "low_fat": ("fat_g", 20, 30, False),
    "low_calorie": ("calories", 500, 700, False),
}


def identity(candidate):
    return f"{candidate.merchant_id}:{candidate.item_id}"


def qualifies(nutrition, preferences):
    if nutrition.state != "ready" or meets_explicit_limits(nutrition, preferences) is not True:
        return False
    for goal in preferences.goals:
        metric, reference, broad, higher = QUALITATIVE[goal]
        value = getattr(nutrition, metric)
        if value is None or (value < broad if higher else value > broad):
            return False
    return True


def enqueue(session, payload, candidates, pool, queries, paging, settings):
    progress = session.nutrition_search
    CatalogStore(settings.database_path).enqueue_search(
        progress.id,
        {
            "id": progress.id,
            "session_id": session.id,
            "request": payload.model_dump(mode="json"),
            "pool": [r.candidate.model_dump(mode="json") for r in pool],
            "seen": [identity(c) for c in candidates],
            "queries": queries,
            "cursor": paging.get("cursor"),
            "has_more": paging.get("cursor") is not None,
            "refinements": paging.get("refinements"),
            "results": [],
            "in_flight": [],
            "pages": 1,
            "assistant_index": len(session.messages) - 1,
        },
    )


def context_for(session, candidates, settings, db):
    from app.services.catalog_reviews import attach_reviews
    from app.services.review_recommendations import review_context

    ctx = review_context(db, session.profile.id, session.mode == "mock", session.profile)
    if session.mode == "live" and settings.live_mock_reviews:
        attach_reviews(ctx, candidates, settings, db, session.profile)
    return ctx


def ordered(session, payload, candidates, settings, db, *, nutrition=None, ignore=True, limit=15):
    return rank(
        candidates,
        payload,
        session.profile,
        session.budget_cents,
        context_for(session, candidates, settings, db),
        session.recent_recommendations,
        intent=session.request_intent,
        nutrition_by_item=nutrition,
        limit=limit,
        strict_nutrition=not ignore,
        ignore_nutrition=ignore,
    )


def message(tested, accepted, complete, reason, approximate=0):
    endings = {
        "limit_reached": "Atingi o limite de 15 candidatos.",
        "catalog_exhausted": "Não há mais opções disponíveis com os outros filtros.",
        "usage_limit": "O limite diário de uso da estimativa nutricional foi atingido.",
        "unavailable": "O estimador nutricional não está configurado.",
        "source_error": "Não consegui consultar mais opções no catálogo agora.",
        "error": "Não consegui concluir a avaliação nutricional agora.",
    }
    if approximate:
        return (
            f"Avaliei {tested} de até 15 candidatos e não encontrei correspondência nutricional verificada. "
            f"{endings.get(reason, '')} Trouxe {approximate} alternativas mais próximas: a certeza da adequação é baixa. "
            "Elas podem não satisfazer seus termos subjetivos; confira as estimativas e as limitações de cada opção. "
            "Limites numéricos explícitos foram mantidos."
        )
    progress = (
        f"Avaliei {tested} de até 15 candidatos; {accepted} atendem aos critérios nutricionais."
    )
    if not complete:
        return progress + " Estou avaliando mais opções em lotes de três."
    if reason == "target_reached":
        return (
            progress
            + " Escolha uma das três opções abaixo. Os valores nutricionais são estimativas."
        )
    return (
        progress
        + " "
        + endings.get(reason, "")
        + (
            " Estas são as opções aprovadas; seus limites foram mantidos."
            if accepted
            else " Não encontrei alternativas compatíveis com os limites numéricos e os demais filtros. Você pode ajustar os critérios e buscar novamente."
        )
    )


def publish(db, job, recommendations, *, done, reason=None):
    with db.transaction() as connection:
        session = db.get(job["session_id"], connection)
        if not active(session, job):
            return False
        progress = session.nutrition_search
        progress.tested = len(job["results"])
        progress.accepted = sum(not r.approximate_match for r in recommendations)
        progress.approximate = sum(r.approximate_match for r in recommendations)
        progress.batches = (progress.tested + 2) // 3
        progress.state = "complete" if done else "pending"
        progress.reason = reason
        session.recommendations = recommendations
        index = job["assistant_index"]
        if index < len(session.messages) and session.messages[index].role == "assistant":
            session.messages[index].text = message(
                progress.tested, progress.accepted, done, reason, progress.approximate
            )
        if done:
            session.recent_recommendations = (
                session.recent_recommendations
                + [(r.candidate.merchant_id, r.candidate.item_id) for r in recommendations]
            )[-18:]
        db.save(session, connection)
    return True


def active(session, job):
    return (
        session is not None
        and session.nutrition_search is not None
        and session.nutrition_search.id == job["id"]
        and session.nutrition_search.state == "pending"
        and session.selected is None
    )


async def evaluate(candidate, session, payload, settings, provider, db):
    from app.services.nutrition.service import estimate_nutrition

    c = candidate
    try:
        # Antes de estimar, obtenha composição/porção atuais e valide novamente preço e restrições.
        if hasattr(provider, "item") and not c.simulated:
            c = await asyncio.wait_for(
                provider.item(c.merchant_id, c.item_id, session.address),
                timeout=2 * settings.mcp_timeout_seconds + 2,
            )
        if not ordered(session, payload, [c], settings, db):
            return {
                "candidate": c.model_dump(mode="json"),
                "nutrition": NutritionResult().model_dump(mode="json"),
                "reason": "other_filters",
            }
        store = CatalogStore(settings.database_path)
        store.observe(c, job_key(c))
        budget = Budget(store, settings, job_key(c))
        token = current_budget.set(budget)
        try:
            economical = settings.model_copy(
                update={"calorias_estimar_sempre": False, "calorias_amostras": 1}
            )
            nutrition = await estimate_nutrition(c, economical)
        finally:
            current_budget.reset(token)
        return {
            "candidate": c.model_dump(mode="json"),
            "nutrition": nutrition.model_dump(mode="json"),
            "reason": budget.reason,
        }
    except asyncio.CancelledError:
        raise
    except Exception:
        log.exception("nutrition_batch.candidate_failed")
        return {
            "candidate": c.model_dump(mode="json"),
            "nutrition": NutritionResult(state="error").model_dump(mode="json"),
            "reason": "unavailable",
        }


def approved_results(job, session, payload, settings, db):
    tested = [MealCandidate.model_validate(r["candidate"]) for r in job["results"]]
    nutrition = {
        (c.merchant_id, c.item_id): NutritionResult.model_validate(r["nutrition"])
        for c, r in zip(tested, job["results"])
    }
    approved = [
        c
        for c in tested
        if qualifies(
            nutrition[c.merchant_id, c.item_id], session.request_intent.nutrition_preferences
        )
    ]
    return ordered(
        session, payload, approved, settings, db, nutrition=nutrition, ignore=False, limit=3
    )


def approximate_results(job, session, payload, settings, db):
    """Aproximações apenas quando não há aprovados, sem relaxar limites numéricos ou outros filtros."""
    preferences = session.request_intent.nutrition_preferences
    eligible, nutrition = [], {}
    for result in job["results"]:
        if result.get("reason") in ("other_filters", "unavailable"):
            continue  # detalhes atuais indisponíveis ou candidato inelegível
        c = MealCandidate.model_validate(result["candidate"])
        n = NutritionResult.model_validate(result["nutrition"])
        if meets_explicit_limits(n, preferences) is not True:
            continue
        eligible.append(c)
        nutrition[c.merchant_id, c.item_id] = n
    ranked = ordered(
        session, payload, eligible, settings, db, nutrition=nutrition, ignore=False, limit=15
    )

    def proximity(rec):
        n = rec.nutrition
        scores = []
        for goal in preferences.goals:
            metric, reference, broad, higher = QUALITATIVE[goal]
            value = getattr(n, metric) if n.state == "ready" else None
            if value is not None:
                scores.append(
                    min(value / reference, 1) if higher else reference / max(value, reference)
                )
        # Evidência nutricional pesa antes da afinidade inferida pelo texto/reviews.
        return (len(scores), sum(scores) / len(scores) if scores else 0)

    ranked.sort(key=proximity, reverse=True)  # empates mantêm a ordenação pelos demais critérios
    results = []
    for rec in ranked[:3]:
        limitations = list(rec.limitations)
        n = rec.nutrition
        for goal in preferences.goals:
            metric, reference, broad, higher = QUALITATIVE[goal]
            value = getattr(n, metric) if n.state == "ready" else None
            metric_label = {
                "protein_g": "proteína",
                "carbs_g": "carboidratos",
                "fat_g": "gordura",
                "calories": "calorias",
            }[metric]
            if value is None:
                limitations.append(
                    f"Sem dados de {metric_label} para verificar sua preferência por {LABELS[goal]}."
                )
            elif value < broad if higher else value > broad:
                amount = (
                    f"{value:g} kcal" if metric == "calories" else f"{value:g} g de {metric_label}"
                )
                limitations.append(
                    f"A estimativa de {amount} pode não corresponder ao que você espera ao pedir {LABELS[goal]}."
                )
        warning = (
            "Alternativa aproximada — baixa certeza de adequação ao seu pedido. "
            "Não foi encontrada correspondência verificada; esta opção pode não atender à preferência subjetiva."
        )
        results.append(
            rec.model_copy(
                update={
                    "approximate_match": True,
                    "match_confidence": "low",
                    "reasons": [warning, *rec.reasons],
                    "limitations": [warning, *limitations],
                }
            )
        )
    return results


async def process_search(settings, provider=None):
    store = CatalogStore(settings.database_path)
    job = store.claim_search(settings.nutrition_timeout_seconds + 120)
    if job is None:
        return False
    db = Database(settings.database_path)
    if provider is None:
        from app.services.ifood_live import MCPIFood

        provider = MCPIFood(settings)
    payload = MealRequest.model_validate(job["request"])
    try:
        while True:
            session = db.get(job["session_id"])
            if not active(session, job):
                store.save_search(job["id"], job, done=True)
                return True
            # Um reinício pode ocorrer entre salvar o lote concluído e publicar os cards.
            # Verifique o snapshot antes de iniciar outro lote, para não ultrapassar a condição de parada.
            previous = approved_results(job, session, payload, settings, db)
            resumed_reason = (
                "target_reached"
                if len(previous) == 3
                else "limit_reached"
                if len(job["results"]) >= MAX_CANDIDATES
                else "usage_limit"
                if any(r.get("reason") == "daily_limit" for r in job["results"])
                else None
            )
            if resumed_reason:
                if not previous:
                    previous = approximate_results(job, session, payload, settings, db)
                publish(db, job, previous, done=True, reason=resumed_reason)
                store.save_search(job["id"], job, done=True)
                return True
            remaining = MAX_CANDIDATES - len(job["results"])
            while (
                not job["in_flight"]
                and len(job["pool"]) < min(BATCH_SIZE, remaining)
                and job["has_more"]
                and job["pages"] < 10
            ):
                old_cursor = job["cursor"]
                try:
                    page = await provider.search_page(
                        job["queries"],
                        session.address,
                        session.budget_cents,
                        session.request_intent.cuisine,
                        job["refinements"],
                        cursor=old_cursor,
                    )
                except Exception:
                    log.exception("nutrition_batch.page_failed")
                    job["has_more"] = False
                    job["source_error"] = True
                    break
                job["pages"] += 1
                job["cursor"] = page["cursor"]
                job["has_more"] = page["cursor"] is not None and page["cursor"] != old_cursor
                fresh = []
                for c in page["candidates"]:
                    if identity(c) not in job["seen"]:
                        job["seen"].append(identity(c))
                        fresh.append(c)
                pool = [MealCandidate.model_validate(c) for c in job["pool"]] + fresh
                job["pool"] = [
                    r.candidate.model_dump(mode="json")
                    for r in ordered(session, payload, pool, settings, db)
                ]
            if not job["in_flight"]:
                size = min(BATCH_SIZE, remaining)
                job["in_flight"], job["pool"] = job["pool"][:size], job["pool"][size:]
            store.save_search(
                job["id"], job, lease_seconds=settings.nutrition_timeout_seconds + 120
            )
            batch = [MealCandidate.model_validate(c) for c in job["in_flight"]]
            if batch:
                results = await asyncio.gather(
                    *(evaluate(c, session, payload, settings, provider, db) for c in batch)
                )
                job["results"].extend(results)
                job["in_flight"] = []
            recommendations = approved_results(job, session, payload, settings, db)
            reason = None
            if len(recommendations) == 3:
                reason = "target_reached"
            elif len(job["results"]) >= MAX_CANDIDATES:
                reason = "limit_reached"
            elif any(r.get("reason") == "daily_limit" for r in job["results"]):
                reason = "usage_limit"
            elif not settings.nutrition_enabled:
                reason = "unavailable"
            elif not batch or (not job["pool"] and not job["has_more"]):
                reason = "source_error" if job.get("source_error") else "catalog_exhausted"
            store.save_search(
                job["id"], job, lease_seconds=settings.nutrition_timeout_seconds + 120
            )
            if reason and not recommendations:
                recommendations = approximate_results(job, session, payload, settings, db)
            if not publish(db, job, recommendations, done=reason is not None, reason=reason):
                store.save_search(job["id"], job, done=True)
                return True
            log.info(
                "nutrition_batch.progress tested=%s accepted=%s reason=%s",
                len(job["results"]),
                len(recommendations),
                reason,
            )
            if reason:
                store.save_search(job["id"], job, done=True)
                return True
    except asyncio.CancelledError:
        # Snapshot contém o lote em andamento; cache e cotas persistidas são reaproveitados ao retomar.
        store.save_search(job["id"], job)
        raise
    except Exception:
        log.exception("nutrition_batch.search_failed")
        publish(db, job, [], done=True, reason="error")
        store.save_search(job["id"], job, done=True)
        return True
