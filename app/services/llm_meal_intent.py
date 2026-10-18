"""Interpretação contextual via LLM de texto (NUTRITION_PROVIDER), validada e com fallback local limitado por tempo."""
import asyncio
from collections import OrderedDict
import json
import re
import time
from typing import Annotated, Literal

from pydantic import Field, ValidationError

from app.core import logs
from app.core.config import Settings
from app.core.exceptions import AppError
from app.core.search_logs import elapsed_ms, event
from app.schemas.macro import Cents, DietContext, MealIntent, MealRequest, Model, NutritionPreferences
from app.services.meal_intent import LABELS, parse_intent
from app.services import horario
from app.services.llm_texto import chat_completion_fallback as chat_completion
from app.services.openrouter import OpenRouterError
from app.services.review_processing import digest, normalized
from app.services.nutrition_preferences import merge_preferences, preference_labels, without_daily_targets
from app.skills import busca_intencao

VERSION = 'context-intent-v6-variedade'
Goal = Literal['large_portion', 'small_portion', 'light', 'cheap', 'fast', 'protein', 'comfort', 'indulgent', 'vegetarian']


class LLMIntent(Model):
    goals: list[Goal] = Field(max_length=9)
    food_query: str = Field(default='', max_length=200, pattern=r'^[\w\s,\-]*$')
    search_queries: list[Annotated[str, Field(min_length=2, max_length=60, pattern=r'^[\w\s\-]+$')]] = Field(
        default_factory=list, max_length=4)
    cuisine: str = Field(default='', max_length=40, pattern=r'^[\w\s\-]*$')
    avoid_repeats: bool = False
    pesquisar_na_web: str = Field(default='', max_length=80, pattern=r'^[\w\s\-]*$')
    montar_pedido: bool = False
    alvo_item_id: str = Field(default='', max_length=80)
    motivo_da_decisao: str = Field(default='', max_length=300)
    context_summary: str = Field(min_length=1, max_length=400)
    inferences: list[str] = Field(default_factory=list, max_length=5)
    budget_cents: Cents | None = None
    party_size: int | None = Field(default=None, ge=1, le=20, strict=True)
    max_delivery_minutes: int | None = Field(default=None, ge=1, le=240, strict=True)
    nutrition_preferences: NutritionPreferences = Field(default_factory=NutritionPreferences)


NUTRITION_GOALS = {"high_protein", "low_carb", "low_fat", "low_calorie"}
APPETITE_GOALS = {"large_portion", "small_portion", "light", "cheap", "fast", "protein", "comfort", "indulgent", "vegetarian"}


def sanear_objetivos(cleaned: str) -> str:
    """O modelo às vezes põe "low_calorie" (objetivo nutricional) em `goals`. Em vez de recusar a resposta inteira
    (e perder o resto: montar_pedido, orçamento, consultas), move para nutrition_preferences.goals e descarta o desconhecido."""
    try:
        dados = json.loads(cleaned)
        goals = dados.get("goals")
        if not isinstance(goals, list):
            return cleaned
    except (ValueError, AttributeError):
        return cleaned
    validos = [g for g in goals if g in APPETITE_GOALS]
    nutri = dados.get("nutrition_preferences")
    if not isinstance(nutri, dict):
        return cleaned
    movidos = [g for g in goals if g in NUTRITION_GOALS and g not in (nutri.get("goals") or [])]
    if len(validos) == len(goals) and not movidos:
        return cleaned
    logs.info("intent", f"resposta do modelo corrigida: objetivos {[g for g in goals if g not in APPETITE_GOALS]} "
                        f"fora de `goals` (nutricionais vão para nutrition_preferences.goals; o resto é descartado)")
    nutri["goals"] = [*(nutri.get("goals") or []), *movidos][:4]
    dados["goals"], dados["nutrition_preferences"] = validos, nutri
    return json.dumps(dados, ensure_ascii=False)


# O texto fica em app/skills/busca_intencao.py; aqui só se anexa o schema do LLMIntent.
SYSTEM_PROMPT = busca_intencao.system(json.dumps(LLMIntent.model_json_schema(), ensure_ascii=False))

# Cache só da interpretação: ranking e rotação são calculados novamente a cada busca.
_cache: OrderedDict[str, tuple[float, LLMIntent]] = OrderedDict()
CACHE_SECONDS = 300
CACHE_SIZE = 128


def _consultas(result: LLMIntent, food_query: str, provider_query: str) -> list[str]:
    """Consultas ao iFood: as concretas do modelo primeiro, depois o alimento pedido e a consulta de reserva."""
    candidatas = [*result.search_queries, food_query, provider_query]
    vistas, lista = set(), []
    for q in candidatas:
        q = q.strip()
        chave = normalized(q)
        if len(q) >= 2 and chave not in vistas:
            vistas.add(chave)
            lista.append(q)
    return lista[:5]


def merge_intent(base: MealIntent, result: LLMIntent, message: str = "", *, ground_food_query: bool = False) -> MealIntent:
    if 'large_portion' in result.goals and 'small_portion' in result.goals:
        raise ValueError('Objetivos de apetite contraditórios')
    explicit_goals = [g for g in base.goals if g not in base.inferred_goals]
    appetite = next((g for g in explicit_goals if g in ('large_portion', 'small_portion')), None)
    if appetite and any(g in ('large_portion', 'small_portion') and g != appetite for g in result.goals):
        raise ValueError('Inferência contradiz o apetite explícito')
    blocked = {
        'fast': r'\b(?:sem pressa|nao (?:estou|to) com pressa)\b',
        'light': r'\bnao quero (?:algo |comida |refeicao )?leve\b',
    }
    if any(goal in result.goals and re.search(pattern, normalized(message)) for goal, pattern in blocked.items()):
        raise ValueError('Inferência contradiz uma negação explícita')
    goals = list(dict.fromkeys(explicit_goals + [g for g in result.goals
                         if not appetite or g not in ('large_portion', 'small_portion') or g == appetite]))
    inferred = [g for g in goals if g not in explicit_goals]
    query = result.food_query.strip()
    if ground_food_query:
        # O modelo não pode transformar os alimentos do diário no pedido atual.
        requested_words = set(re.findall(r'\w+', normalized(message)))
        if any(word not in requested_words for word in re.findall(r'\w+', normalized(query))):
            query = base.food_query
    party = base.party_size or result.party_size
    delivery = base.max_delivery_minutes or result.max_delivery_minutes
    # As regras e campos estruturados prevalecem. Números do LLM exigem unidade
    # correspondente na mensagem para não transformar contexto em metas inventadas.
    nutritional = result.nutrition_preferences.model_copy(deep=True)
    units = {'max_calories': r'(?:kcal|calorias)', 'min_protein_g': r'g(?:ramas)?\s*(?:de\s+)?proteina[s]?',
             'max_carbs_g': r'g(?:ramas)?\s*(?:de\s+)?carboidratos?',
             'max_fat_g': r'g(?:ramas)?\s*(?:de\s+)?gordura[s]?'}
    # Remove metas diárias também da validação das unidades citadas pelo modelo.
    grounding = without_daily_targets(message)
    for field, unit in units.items():
        value = getattr(nutritional, field)
        if value is not None:
            number = re.escape(f'{value:g}').replace(r'\.', '[.,]')
            if not re.search(r'(?<![\d.,])' + number + r'\s*' + unit + r'\b', grounding):
                setattr(nutritional, field, None)
    nutritional = merge_preferences(nutritional, base.nutrition_preferences)
    llm_budget = result.budget_cents
    if (re.search(r'\b(?:kcal|calorias|proteina|carboidrato|gordura)', normalized(message))
            and not re.search(r'r\$|\breais\b|\borcamento\b|\bgastar\b', normalized(message))):
        llm_budget = None
    labels = [LABELS[g] for g in goals] + preference_labels(nutritional)
    if party:
        labels.append(f'comida para {party} pessoas')
    if delivery:
        labels.append(f'previsão de entrega de até {delivery} minutos')
    # Sem alimento explícito, traduzir objetivos para termos úteis ao provedor MCP.
    provider_query = query or ('refeição porção grande' if 'large_portion' in goals else
                               'lanche leve' if 'small_portion' in goals else
                               'salada grelhado' if 'light' in goals else
                               'frango grelhado' if 'protein' in goals else base.provider_query)
    return base.model_copy(update={
        'goals': goals, 'food_query': query, 'provider_query': provider_query,
        'budget_cents': base.budget_cents if base.budget_cents is not None else llm_budget,
        'party_size': party, 'max_delivery_minutes': delivery, 'labels': labels,
        'interpretation_source': 'llm', 'context_summary': result.context_summary,
        'inferences': result.inferences, 'inferred_goals': inferred, 'fallback_reason': None,
        'nutrition_preferences': nutritional,
        'search_queries': _consultas(result, query, provider_query), 'cuisine': result.cuisine.strip() or None,
        'avoid_repeats': base.avoid_repeats or result.avoid_repeats,
        'pesquisar_na_web': result.pesquisar_na_web.strip(),
        'montar_pedido': result.montar_pedido,
        'alvo_item_id': result.alvo_item_id.strip(), 'motivo_da_decisao': result.motivo_da_decisao.strip(),
    })


async def interpret_intent(request: MealRequest, settings: Settings, *, diet_context: DietContext | None = None,
                           conversa: dict | None = None, preferencias: str | None = None) -> MealIntent:
    started = time.perf_counter()
    base = parse_intent(request)
    if not settings.intent_llm_enabled:
        event('intent.fallback', reason='disabled', duration_ms=elapsed_ms(started))
        return base.model_copy(update={'fallback_reason': 'disabled'})
    if not settings.llm_api_key:
        event('intent.fallback', reason='not_configured', duration_ms=elapsed_ms(started))
        return base.model_copy(update={'fallback_reason': 'not_configured'})
    agora = horario.agora(settings)
    key = digest([VERSION, request.model_dump(), agora['dia_da_semana'], agora['periodo'], settings.openrouter_model,
                  settings.openrouter_base_url, settings.openrouter_fallback_models,
                  diet_context.model_dump(mode='json') if diet_context else None, conversa, preferencias])
    cached = _cache.get(key)
    if cached and cached[0] > time.monotonic():
        _cache.move_to_end(key)
        event('intent.cache_hit', duration_ms=elapsed_ms(started))
        return merge_intent(base, cached[1], request.text, ground_food_query=diet_context is not None)
    try:
        async def call():
            return await chat_completion(
                [{'role': 'system', 'content': SYSTEM_PROMPT},
                 {'role': 'user', 'content': busca_intencao.mensagem_usuario(
                     request.text, agora, diet_context.model_dump(mode='json') if diet_context else None, conversa, preferencias)}],
                temperature=0, max_tokens=850, log_content=False,
                prazo_primeiro=settings.intent_llm_timeout_seconds / 2,  # sobra metade para a reserva (GPT)
                settings=settings.model_copy(update={'openrouter_timeout': settings.intent_llm_timeout_seconds}),
            )
        raw = await asyncio.wait_for(call(), settings.intent_llm_timeout_seconds)
        # Aceitar fences apenas para compatibilidade; campos extras e tipos inválidos são recusados.
        cleaned = raw.strip()
        if cleaned.startswith('```') and cleaned.endswith('```'):
            cleaned = cleaned.split('\n', 1)[1].rsplit('```', 1)[0].strip()
        result = LLMIntent.model_validate_json(sanear_objetivos(cleaned))
        merged = merge_intent(base, result, request.text, ground_food_query=diet_context is not None)
        _cache[key] = (time.monotonic() + CACHE_SECONDS, result)
        _cache.move_to_end(key)
        while len(_cache) > CACHE_SIZE:
            _cache.popitem(last=False)
        event('intent.llm_completed', inferred_goals=merged.inferred_goals, duration_ms=elapsed_ms(started))
        return merged
    except asyncio.TimeoutError:
        reason = 'timeout'
    except (ValidationError, ValueError, TypeError, AttributeError, IndexError) as e:
        reason = 'invalid_response'
        # Só o formato do erro (campo e tipo), nunca o conteúdo do pedido: explica por que as regras assumiram.
        detalhe = ('; '.join(f"{'.'.join(map(str, x['loc']))}:{x['type']}" for x in e.errors()[:4])
                   if isinstance(e, ValidationError) else f"{type(e).__name__}: {str(e)[:100]}")
        logs.aviso('intent', f"resposta do modelo recusada ({detalhe}) → regras locais assumem")
    except (OpenRouterError, AppError):
        reason = 'unavailable'
    # Nunca registrar conteúdo do pedido, chave ou corpo do erro do provedor.
    event('intent.fallback', reason=reason, duration_ms=elapsed_ms(started))
    return base.model_copy(update={'fallback_reason': reason})
