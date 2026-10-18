import re
import unicodedata
import logging
import time
from collections import Counter

from app.core.exceptions import MacroError
from app.core.search_logs import elapsed_ms, event
from app.schemas.macro import (
    MealCandidate,
    MealRequest,
    MealIntent,
    Recommendation,
    SelectedItem,
    SelectionInput,
    UserProfile,
    NutritionResult,
)
from app.services.review_recommendations import ReviewContext, review_signal
from app.services.meal_intent import assess_intent, parse_intent
from app.services.nutrition_preferences import apply_profile_preferences, assess_nutrition


def normalized(value: str) -> str:
    return "".join(
        c
        for c in unicodedata.normalize("NFKD", value.lower())
        if not unicodedata.combining(c)
    )


def search_terms(request: MealRequest) -> tuple[str, int | None]:
    intent = parse_intent(request)
    return intent.provider_query, intent.budget_cents


def rank(
    candidates: list[MealCandidate],
    request: MealRequest,
    profile: UserProfile,
    budget: int | None,
    review_context: ReviewContext | None = None,
    recently_shown: list[tuple[str, str]] | None = None,
    intent: MealIntent | None = None,
    nutrition_by_item: dict[tuple[str, str], NutritionResult] | None = None,
    limit: int = 3,
) -> list[Recommendation]:
    started = time.perf_counter()
    excluded = Counter()
    details = {}
    event("ranking.started", candidate_count=len(candidates), preference_count=len(profile.preferences),
          restriction_count=len(profile.restrictions) + len(request.restrictions))

    def reject(candidate, reason):
        excluded[reason] += 1
        event("ranking.rejected", level=logging.DEBUG, merchant_id=candidate.merchant_id,
              item_id=candidate.item_id, reason=reason)

    intent = apply_profile_preferences(intent or parse_intent(request), profile)
    nutrition_by_item = nutrition_by_item or {}
    query = intent.food_query
    generic = {"almoco", "jantar", "comida", "comer", "algo", "opcao", "opcoes", "refeicao", "com", "por", "favor", "uma", "que", "tem"}
    words = [w for w in normalized(query).split() if len(w) > 2 and w not in generic]
    recently_shown = recently_shown or []
    ranked = []
    has_search_matches = False
    for candidate in candidates:
        text = normalized(candidate.name + " " + candidate.description)
        search_text = text + " " + normalized(" ".join(
            review_context.cuisines.get(candidate.merchant_id, []) if review_context else []
        ))
        relevance = sum(bool(re.search(r"\b" + re.escape(w) + r"s?\b", search_text)) for w in set(words))
        has_search_matches = has_search_matches or relevance > 0
        if not candidate.available:
            reject(candidate, "unavailable")
            continue
        if "vegetarian" in intent.goals and candidate.simulated and "vegetarian" not in candidate.features.tags:
            reject(candidate, "vegetarian")
            continue
        if any(normalized(d) in text for d in profile.dislikes if d.strip()):
            reject(candidate, "dislike")
            continue
        restrictions = profile.restrictions + request.restrictions
        if any(normalized(r) in text for r in restrictions if r.strip()):
            reject(candidate, "restriction")
            continue
        reasons, score = [], 0
        matches = [
            p for p in profile.preferences if p.strip() and normalized(p) in text
        ]
        if matches:
            reasons.append("Este prato inclui algo que você gosta: " + ", ".join(matches) + ".")
            score += len(matches) * 3
        if relevance:
            reasons.append("Combina com os termos da sua busca.")
            score += 2
        if budget is not None and candidate.price_cents <= budget:
            reasons.append(
                "Preço do prato dentro do orçamento; entrega e adicionais à parte."
            )
            score += 1
        elif budget is not None:
            reject(candidate, "budget")
            continue
        nutrition = nutrition_by_item.get((candidate.merchant_id, candidate.item_id), NutritionResult())
        limitations = ([] if nutrition.state == "ready" else [
            "Informação nutricional indisponível. Calorias e macros não foram calculados."
        ])
        if restrictions:
            limitations.append(
                "Não foi possível verificar as restrições: "
                + ", ".join(restrictions)
                + ". Confirme com o restaurante."
            )
        signal = None
        if review_context is not None:
            signal, review_reasons = review_signal(candidate, review_context)
            score += signal.score
            preference_reasons = reasons[:1] if matches else []
            reasons = preference_reasons + review_reasons + reasons[len(preference_reasons):]
            if review_context.simulated:
                limitations.append("Personalização de demonstração baseada em avaliações fictícias.")
        fit = assess_intent(candidate, intent)
        nutrition_fit = assess_nutrition(nutrition, intent.nutrition_preferences)
        nutrition_points = 4 * nutrition_fit.score
        score += nutrition_points
        reasons = nutrition_fit.reasons + fit.reasons + reasons
        limitations += fit.limitations + nutrition_fit.limitations
        if intent.diet_context:
            reasons = intent.diet_context.reasons + reasons
            limitations += intent.diet_context.limitations
        exposure = recently_shown.count((candidate.merchant_id, candidate.item_id))
        merchant_exposure = sum(mid == candidate.merchant_id for mid, _ in recently_shown)
        rotation_penalty = 2 * exposure + 0.5 * merchant_exposure
        score -= rotation_penalty
        recommendation = Recommendation(
            candidate=candidate,
            nutrition=nutrition,
            reasons=reasons or ["Opção disponível no catálogo consultado."],
            limitations=limitations,
            review_signal=signal,
        )
        components = dict(merchant_id=candidate.merchant_id, item_id=candidate.item_id,
                          relevance=relevance, intent_score=fit.score,
                          nutrition_score=nutrition_fit.score, nutrition_state=nutrition.state,
                          nutrition_points=nutrition_points,
                          preference_score=len(matches) * 3,
                          query_score=2 if relevance else 0,
                          budget_score=1 if budget is not None else 0,
                          reviews_score=signal.score if signal else 0,
                          rotation_penalty=rotation_penalty, score=round(score, 4))
        details[id(recommendation)] = components
        event("ranking.scored", level=logging.DEBUG, **components)
        ranked.append(
            (
                relevance,
                fit.score,
                score,
                recommendation,
            )
        )
    if words and has_search_matches:
        for entry in ranked:
            if entry[0] == 0:
                reject(entry[3].candidate, "search_mismatch")
        ranked = [entry for entry in ranked if entry[0] > 0]
    ordered = [r for _, _, _, r in sorted(ranked, key=lambda entry: (
        -entry[0], -entry[1], -entry[2], entry[3].candidate.merchant_id, entry[3].candidate.item_id
    ))]
    # Mostra alternativas de restaurantes diferentes antes de repetir uma cozinha.
    chosen, merchants = [], set()
    for recommendation in ordered:
        if recommendation.candidate.merchant_id not in merchants:
            chosen.append(recommendation)
            merchants.add(recommendation.candidate.merchant_id)
        if len(chosen) == limit:
            break
    chosen = (chosen + [r for r in ordered if r not in chosen])[:limit]
    event("ranking.completed", candidate_count=len(candidates), eligible_count=len(ordered),
          excluded=dict(excluded), result_count=len(chosen),
          selected=[dict(position=i + 1, **details[id(rec)]) for i, rec in enumerate(chosen)],
          sort_order=["relevance", "intent_score", "score"],
          duration_ms=elapsed_ms(started))
    return chosen


def select(candidate: MealCandidate, selection: SelectionInput) -> SelectedItem:
    if not candidate.available:
        raise MacroError("Item indisponível. Escolha outro prato.")
    groups = {g.id: g for g in candidate.option_groups}
    quantities = {g.id: 0 for g in candidate.option_groups}
    seen, labels, extra = set(), [], 0
    for choice in selection.options:
        key = (choice.group_id, choice.option_id)
        if key in seen:
            raise MacroError("Opção repetida. Revise os complementos.", 422)
        seen.add(key)
        group = groups.get(choice.group_id)
        option = (
            next((o for o in group.options if o.id == choice.option_id), None)
            if group
            else None
        )
        if option is None or choice.quantity > option.max_quantity:
            raise MacroError("Complemento ou quantidade inválida.", 422)
        quantities[group.id] += choice.quantity
        extra += option.price_cents * choice.quantity
        labels.append(f"{choice.quantity} × {option.name}")
    for group in candidate.option_groups:
        if not group.min_selections <= quantities[group.id] <= group.max_selections:
            raise MacroError(
                f"{group.name}: escolha de {group.min_selections} a {group.max_selections} opções.",
                422,
            )
    return SelectedItem(
        candidate=candidate,
        quantity=selection.quantity,
        options=selection.options,
        option_labels=labels,
        unit_total_cents=candidate.price_cents + extra,
    )
