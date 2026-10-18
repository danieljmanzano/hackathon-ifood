import re
import unicodedata

from app.core.exceptions import MacroError
from app.schemas.macro import (
    MealCandidate,
    MealRequest,
    MealIntent,
    Recommendation,
    SelectedItem,
    SelectionInput,
    UserProfile,
)
from app.services.review_recommendations import ReviewContext, review_signal
from app.services.meal_intent import assess_intent, parse_intent


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
) -> list[Recommendation]:
    intent = intent or parse_intent(request)
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
            continue
        if "vegetarian" in intent.goals and candidate.simulated and "vegetarian" not in candidate.features.tags:
            continue
        if any(normalized(d) in text for d in profile.dislikes if d.strip()):
            continue
        restrictions = profile.restrictions + request.restrictions
        if any(normalized(r) in text for r in restrictions if r.strip()):
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
            continue
        limitations = [
            "Informação nutricional indisponível. Calorias e macros não foram calculados."
        ]
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
        reasons = fit.reasons + reasons
        limitations += fit.limitations
        exposure = recently_shown.count((candidate.merchant_id, candidate.item_id))
        merchant_exposure = sum(mid == candidate.merchant_id for mid, _ in recently_shown)
        score -= 2 * exposure + 0.5 * merchant_exposure
        ranked.append(
            (
                relevance,
                fit.score,
                score,
                Recommendation(
                    candidate=candidate,
                    reasons=reasons or ["Opção disponível no catálogo consultado."],
                    limitations=limitations,
                    review_signal=signal,
                ),
            )
        )
    if words and has_search_matches:
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
        if len(chosen) == 3:
            return chosen
    return (chosen + [r for r in ordered if r not in chosen])[:3]


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
