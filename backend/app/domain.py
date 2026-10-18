import re
import unicodedata

from .errors import MacroError
from .schemas import MealCandidate, MealRequest, Recommendation, SelectedItem, SelectionInput, UserProfile


def normalized(value: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", value.lower()) if not unicodedata.combining(c))


def search_terms(request: MealRequest) -> tuple[str, int | None]:
    """Deterministic bootstrap, not an LLM. The UI explicitly identifies this limit."""
    text = normalized(request.text)
    budget = request.budget_cents
    match = re.search(r"(?:ate\s*(?:r\$\s*)?|r\$\s*)(\d+)(?:[,.](\d{1,2}))?", text)
    if match:
        if budget is None:
            budget = int(match[1]) * 100 + int((match[2] or "0").ljust(2, "0"))
        text = text[:match.start()] + " " + text[match.end():]
    text = re.sub(r"\b(quero|pedir|uma?|prato|refeicao|para|pos|treino|hoje|barato|barata|rapido|rapida|perto de mim|reais)\b", " ", text)
    query = " ".join(text.split()).strip(" ,.;")
    return query or "refeição", budget


def rank(candidates: list[MealCandidate], request: MealRequest, profile: UserProfile, budget: int | None):
    query, _ = search_terms(request)
    words = [w for w in normalized(query).split() if len(w) > 2]
    ranked = []
    for candidate in candidates:
        if not candidate.available:
            continue
        text = normalized(candidate.name + " " + candidate.description)
        if any(normalized(d) in text for d in profile.dislikes if d.strip()):
            continue
        restrictions = profile.restrictions + request.restrictions
        if any(normalized(r) in text for r in restrictions if r.strip()):
            continue
        reasons, score = [], 0
        matches = [p for p in profile.preferences if p.strip() and normalized(p) in text]
        if matches:
            reasons.append("Combina com suas preferências: " + ", ".join(matches))
            score += len(matches) * 3
        if any(w in text for w in words):
            reasons.append("Combina com os termos da sua busca.")
            score += 2
        if budget is not None and candidate.price_cents <= budget:
            reasons.append("Preço do prato dentro do orçamento; entrega e adicionais à parte.")
            score += 1
        elif budget is not None:
            continue
        limitations = ["Informação nutricional indisponível. Calorias e macros não foram calculados."]
        if restrictions:
            limitations.append("Não foi possível verificar as restrições: " + ", ".join(restrictions) + ". Confirme com o restaurante.")
        ranked.append((score, Recommendation(candidate=candidate, reasons=reasons or ["Opção disponível no catálogo consultado."],
                                              limitations=limitations)))
    return [r for _, r in sorted(ranked, key=lambda pair: -pair[0])[:3]]


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
        option = next((o for o in group.options if o.id == choice.option_id), None) if group else None
        if option is None or choice.quantity > option.max_quantity:
            raise MacroError("Complemento ou quantidade inválida.", 422)
        quantities[group.id] += choice.quantity
        extra += option.price_cents * choice.quantity
        labels.append(f"{choice.quantity} × {option.name}")
    for group in candidate.option_groups:
        if not group.min_selections <= quantities[group.id] <= group.max_selections:
            raise MacroError(f"{group.name}: escolha de {group.min_selections} a {group.max_selections} opções.", 422)
    return SelectedItem(candidate=candidate, quantity=selection.quantity, options=selection.options,
                        option_labels=labels, unit_total_cents=candidate.price_cents + extra)
