import re
import unicodedata
import logging
import time
from collections import Counter

from app.core import logs
from app.core.config import get_settings
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
from app.services.nutrition_preferences import apply_profile_preferences, assess_nutrition, meets_explicit_limits


def normalized(value: str) -> str:
    return "".join(
        c
        for c in unicodedata.normalize("NFKD", value.lower())
        if not unicodedata.combining(c)
    )


def search_terms(request: MealRequest) -> tuple[str, int | None]:
    intent = parse_intent(request)
    return intent.provider_query, intent.budget_cents


# Palavras que descrevem o formato do prato, não o sabor/tipo: ficam de fora ao comparar os pratos.
_DESCRITIVAS = {"com", "para", "sem", "dos", "das", "caseiro", "caseira", "caseiros", "caseiras", "inteiro", "inteira",
                "inteiros", "inteiras", "artesanal", "artesanais", "tradicional", "especial", "grande", "pequeno",
                "pequena", "fatia", "fatias", "pedaco", "pedacos", "unidade", "unidades", "combo", "porcao"}


def _singular(palavra: str) -> str:
    return palavra[:-1] if len(palavra) > 3 and palavra.endswith("s") else palavra


def tipo_do_prato(nome: str, comida_pedida: str = "") -> str:
    """Sabor/tipo principal do prato: a primeira palavra que o distingue ("Bolo de Cenoura com Ganache" -> "cenoura").

    Ignora a própria comida pedida ("bolo"), conectivos e palavras de formato. Vazio se não houver como distinguir.
    """
    pedida = {_singular(w) for w in normalized(comida_pedida).split()}
    for palavra in normalized(nome).split():
        if len(palavra) > 2 and palavra not in _DESCRITIVAS and _singular(palavra) not in pedida:
            return _singular(palavra)
    return ""


def _escolher_variados(ordered: list[Recommendation], limit: int, comida_pedida: str) -> list[Recommendation]:
    """Segue a ordem do ranking, mas pula quem repete o tipo (e, na 1ª passada, o restaurante) de quem já entrou."""
    escolhidos: list[Recommendation] = []
    tipos: set[str] = set()
    restaurantes: set[str] = set()
    for exigir_restaurante_novo in (True, False):
        for rec in ordered:
            if len(escolhidos) == limit:
                return escolhidos
            tipo = tipo_do_prato(rec.candidate.name, comida_pedida)
            if rec in escolhidos or (tipo and tipo in tipos):
                continue
            if exigir_restaurante_novo and rec.candidate.merchant_id in restaurantes:
                continue
            escolhidos.append(rec)
            tipos.add(tipo)
            restaurantes.add(rec.candidate.merchant_id)
    return (escolhidos + [r for r in ordered if r not in escolhidos])[:limit]  # faltou variedade: completa pela ordem


def _motivos_em_portugues(excluded: Counter, budget: int | None) -> dict[str, int]:
    """Descartes do ranking com rótulos legíveis (vão no diagnóstico que o planejador de busca lê)."""
    rotulos = {"unavailable": "restaurante fechado/indisponível", "vegetarian": "não vegetariano",
               "dislike": "contém algo que você não gosta", "restriction": "bate com uma restrição",
               "search_mismatch": "sem relação com a busca", "already_shown": "já mostrado antes nesta conversa",
               "budget": f"acima do orçamento de R$ {budget / 100:.2f}" if budget is not None else "acima do orçamento"}
    return {rotulos.get(motivo, motivo): n for motivo, n in excluded.items()}


_ROTULO_CURTO = {"unavailable": "restaurante fechado", "vegetarian": "não vegetariano", "dislike": "algo que não gosta",
                 "restriction": "restrição", "search_mismatch": "nenhuma palavra da busca", "already_shown": "já mostrado",
                 "budget": "acima do orçamento"}


def _logar_filtro(candidates, words, achou, veredito, ranked, mostrar_termos) -> None:
    """Mostra o que o ranking viu, o que cortou e por quê (uma linha por item), para conferir se a busca faz sentido."""
    termos = ", ".join(sorted(set(words))) if mostrar_termos else f"{len(set(words))} palavras (oculto: BUSCA_LOG_CONTEUDO=false)"
    logs.info("ranking", f"{len(candidates)} itens do iFood · palavras da busca: {termos}")
    logs.info("ranking", "regras, nesta ordem: fechado → já mostrado (se pediu variedade) → vegetariano → não gosta → restrição "
                         "→ acima do orçamento → [se algum item casa com as palavras] sem nenhuma palavra = descartado "
                         "→ ordena por nº de palavras casadas, depois intenção, depois pontos")
    mantidos = {(r.candidate.merchant_id, r.candidate.item_id) for _, _, _, r in ranked}
    for c in candidates[:60]:
        chave = (c.merchant_id, c.item_id)
        palavras = achou.get(chave, [])
        casou = f"casou {len(palavras)}" + (f" [{', '.join(palavras)}]" if mostrar_termos and palavras else "")
        if chave in mantidos:
            destino = "ok"
        else:
            motivo = veredito.get(chave, "?")
            destino = "descartado: " + (_ROTULO_CURTO.get(motivo) or motivo)
        logs.info("ranking", f"  {destino:<40.40} · {logs.curto(c.name, 38)} @ {logs.curto(c.merchant_name, 28)} · "
                             f"R$ {c.price_cents / 100:.2f} · {casou}")
    if len(candidates) > 60:
        logs.info("ranking", f"  … e mais {len(candidates) - 60} itens")


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
    diagnostico: dict | None = None,
    strict_nutrition: bool = False,
    ignore_nutrition: bool = False,
) -> list[Recommendation]:
    """`diagnostico` (opcional) recebe quantos candidatos cada filtro descartou, em português, para o planejador."""
    started = time.perf_counter()
    excluded = Counter()
    details = {}
    event("ranking.started", candidate_count=len(candidates), preference_count=len(profile.preferences),
          restriction_count=len(profile.restrictions) + len(request.restrictions))

    veredito: dict[tuple[str, str], str] = {}  # (restaurante, item) -> motivo do descarte, para o log legível

    def reject(candidate, reason):
        excluded[reason] += 1
        veredito[(candidate.merchant_id, candidate.item_id)] = reason
        event("ranking.rejected", level=logging.DEBUG, merchant_id=candidate.merchant_id,
              item_id=candidate.item_id, reason=reason)

    intent = apply_profile_preferences(intent or parse_intent(request), profile)
    if ignore_nutrition:
        from app.schemas.macro import NutritionPreferences
        intent = intent.model_copy(update={"nutrition_preferences": NutritionPreferences()})
    nutrition_by_item = nutrition_by_item or {}
    query = " ".join([intent.food_query, *intent.search_queries])  # o modelo pode ter proposto vários termos
    generic = {"almoco", "jantar", "comida", "comer", "algo", "opcao", "opcoes", "refeicao", "com", "por", "favor", "uma", "que", "tem"}
    words = [w for w in normalized(query).split() if len(w) > 2 and w not in generic]
    recently_shown = recently_shown or []
    ranked = []
    has_search_matches = False
    achou: dict[tuple[str, str], list[str]] = {}  # palavras da busca encontradas em cada item
    mostrar_termos = get_settings().busca_log_conteudo  # os termos vêm do pedido do usuário

    for candidate in candidates:
        text = normalized(candidate.name + " " + candidate.description)
        search_text = text + " " + normalized(" ".join(
            review_context.cuisines.get(candidate.merchant_id, []) if review_context else []
        ))
        achadas = sorted(w for w in set(words) if re.search(r"\b" + re.escape(w) + r"s?\b", search_text))
        achou[(candidate.merchant_id, candidate.item_id)] = achadas
        relevance = len(achadas)
        has_search_matches = has_search_matches or relevance > 0
        if not candidate.available:
            reject(candidate, "unavailable")
            continue
        if intent.avoid_repeats and (candidate.merchant_id, candidate.item_id) in recently_shown:
            reject(candidate, "already_shown")  # pediu "diferente/outro/variado": o que já viu não volta
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
        if strict_nutrition and meets_explicit_limits(nutrition, intent.nutrition_preferences) is False:
            reject(candidate, "fora dos limites nutricionais informados")
            continue
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
            if review_context.simulated or review_context.synthetic_catalog:
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
    if diagnostico is not None:
        diagnostico.update(_motivos_em_portugues(excluded, budget))
    _logar_filtro(candidates, words, achou, veredito, ranked, mostrar_termos)
    ordered = [r for _, _, _, r in sorted(ranked, key=lambda entry: (
        -entry[0],
        -(int(meets_explicit_limits(entry[3].nutrition, intent.nutrition_preferences) is True) if strict_nutrition else 0),
        -entry[1], -entry[2], entry[3].candidate.merchant_id, entry[3].candidate.item_id
    ))]
    if intent.avoid_repeats:
        # Pediu variedade: um prato de cada tipo ("cenoura", "chocolate"...), de restaurantes diferentes quando der.
        chosen = _escolher_variados(ordered, limit, intent.food_query)
    else:
        # Mostra alternativas de restaurantes diferentes antes de repetir uma cozinha.
        chosen, merchants = [], set()
        for recommendation in ordered:
            if recommendation.candidate.merchant_id not in merchants:
                chosen.append(recommendation)
                merchants.add(recommendation.candidate.merchant_id)
            if len(chosen) == limit:
                break
        chosen = (chosen + [r for r in ordered if r not in chosen])[:limit]
    logs.info("ranking", f"escolhidos ({'variedade: 1 por tipo e restaurante' if intent.avoid_repeats else 'restaurantes diferentes primeiro'}): "
              + " | ".join(f"{i + 1}. {rec.candidate.name} @ {rec.candidate.merchant_name} (relev. {details[id(rec)]['relevance']}, "
                           f"pontos {details[id(rec)]['score']})" for i, rec in enumerate(chosen)))
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
