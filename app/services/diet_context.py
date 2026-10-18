"""Objetivos e consumo informado no dia orientam preferências, sem prescrever metas."""
import re
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from app.schemas.macro import (ConsumptionRecord, DailyNutrients, DietContext, DietGoal,
                               FoodDiaryEntry, MealIntent, NutritionPreferences, UserProfile)
from app.services.nutrition_preferences import merge_preferences, preference_labels
from app.services.review_processing import normalized

GOAL_LABELS = {
    'gain_muscle': 'ganhar massa muscular', 'lose_weight': 'perder peso',
    'maintain_weight': 'manter o peso', 'performance': 'desempenho nos treinos',
    'balanced': 'alimentação equilibrada',
}
GOAL_PATTERNS = {
    'gain_muscle': r'ganhar massa(?: muscular)?|ganho de massa(?: muscular)?|hipertrofia',
    'lose_weight': r'emagrecer|perder (?:peso|gordura)|perda de peso',
    'maintain_weight': r'manter (?:o )?peso|manutencao de peso',
    'performance': r'melhorar (?:o )?desempenho|desempenho nos treinos',
    'balanced': r'alimentacao equilibrada|comer de forma equilibrada',
}


def local_date(value: datetime, timezone_name: str) -> date:
    return value.astimezone(ZoneInfo(timezone_name)).date()


def split_daily_message(message: str) -> tuple[str, list[str], DietGoal | None]:
    """Não deixa alimentos já consumidos virarem o alimento procurado na busca."""
    working = normalized(message)
    goal = None
    for value, pattern in GOAL_PATTERNS.items():
        for match in re.finditer(r'\b(?:' + pattern + r')\b', working):
            if not re.search(r'\bnao(?:\s+\w+){0,2}\s+$', working[:match.start()]):
                goal = value
        working = re.sub(r'\b(?:' + pattern + r')\b', ' ', working)
    working = re.sub(r'\b(?:meu objetivo (?:e|eh)|tenho (?:o )?objetivo de|objetivo de|quero focar em)\b', ' ', working)
    foods = []
    pattern = (r'\b(?:(?:hoje|ontem|anteontem|ja|so|apenas|somente|ate agora)\s+)*'
               r'(?:comi|consumi|tomei|almocei|jantei|tenho comido)\s+'
               r'.*?(?=(?:[,;.!]\s*(?:e\s+)?(?:agora|quero|gostaria|preciso|recomende|sugira|me recomende|estou|to|vou treinar)\b)'
               r'|\b(?:mas|e agora|e quero|e estou|e to|e vou|estou|vou treinar|quero|gostaria|recomende|sugira)\b|$)')
    def consumed(match):
        if (not re.search(r'\bnao\s+$', working[:match.start()])
                and not re.search(r'\b(?:ontem|anteontem|semana passada|outro dia)\b', match[0])):
            foods.append(match[0].strip())
        return ' '
    working = re.sub(pattern, consumed, working)
    working = re.sub(r'\bnao\s*(?=[,;.!])', ' ', working)
    return working.strip(' ,;.!') or 'refeição', foods, goal


def _fruit_report(text: str) -> bool:
    text = normalized(text)
    fruit = r'frutas?|bananas?|macas?|peras?|mamao|melancia|melao|uvas?|laranjas?|morangos?|abacaxi|manga|kiwi'
    if not re.search(r'\b(?:' + fruit + r')\b', text):
        return False
    if re.search(r'\b(?:nao|nem) (?:comi |consumi )?(?:' + fruit + r')\b', text):
        return False
    # Conservador: ingredientes/descritivos desconhecidos deixam a interpretação ao LLM.
    allowed = set(re.findall(r'\w+', re.sub(r'\b(?:' + fruit + r')\b', ' ', text)))
    return all(word.isdigit() or word in {
        'so', 'apenas', 'somente', 'comi', 'consumi', 'hoje', 'ate', 'agora', 'no', 'dia',
        'de', 'do', 'da', 'na', 'manha', 'cafe', 'lanche', 'almoço', 'almoco', 'e', 'uma', 'um',
        'duas', 'dois', 'tres', 'ja', 'g', 'gramas', 'unidades', 'unidade',
    } for word in allowed)


def build_diet_context(profile: UserProfile, diary: list[FoodDiaryEntry],
                       consumption: list[ConsumptionRecord], timezone_name: str,
                       *, on_date: date | None = None, message: str = '') -> tuple[DietContext, str]:
    day = on_date or local_date(datetime.now(timezone.utc), timezone_name)
    diary = [e for e in diary if local_date(e.consumed_at, timezone_name) == day]
    consumption = [e for e in consumption if local_date(e.consumed_at, timezone_name) == day]
    clean, inline_foods, goal_override = split_daily_message(message)
    foods = [e.description for e in diary] + [e.name for e in consumption] + inline_foods
    totals, counts, remaining = {}, {}, {}
    targets = DailyNutrients(calories=profile.daily_calorie_goal,
                            protein_g=profile.diet_plan.daily_protein_g,
                            carbs_g=profile.diet_plan.daily_carbs_g, fat_g=profile.diet_plan.daily_fat_g)
    for metric in DailyNutrients.model_fields:
        values = [getattr(e.nutrition, metric) for e in diary if getattr(e.nutrition, metric) is not None]
        values += [getattr(e.nutrition, metric) * e.quantity * e.fraction for e in consumption
                   if e.nutrition and e.nutrition.state == 'ready' and getattr(e.nutrition, metric) is not None]
        counts[metric] = len(values)
        totals[metric] = round(sum(values), 3) if values else None
        target = getattr(targets, metric)
        # Registro ausente/incompleto nunca vira ingestão zero nem saldo exato.
        remaining[metric] = (round(max(0, target - totals[metric]), 3)
                             if target is not None and foods and len(values) == len(foods) else None)
    goal = goal_override or profile.diet_plan.goal
    signals, reasons, limitations = [], [], []
    if goal:
        reasons.append(f'Seu objetivo informado é {GOAL_LABELS[goal]}; ele foi considerado junto ao consumo registrado de hoje.')
    if foods and all(_fruit_report(food) for food in foods):
        signals.append('fruit_only_records')
        reasons.append('Nos registros de hoje aparecem apenas frutas; favorecemos uma refeição com mais variedade.')
    protein_target = targets.protein_g
    if protein_target is not None and totals['protein_g'] is not None:
        if totals['protein_g'] >= protein_target:
            signals.append('protein_target_reached')
            reasons.append(f'Os registros com dados somam {totals["protein_g"]:g} g de proteína, atingindo a meta diária de {protein_target:g} g que você cadastrou.')
        elif remaining['protein_g'] is not None:
            signals.append('protein_target_remaining')
            reasons.append(f'Os registros somam {totals["protein_g"]:g} g de proteína, abaixo da sua meta diária informada de {protein_target:g} g; demos mais peso a fontes de proteína nesta busca.')
    if targets.calories is not None and totals['calories'] is not None and totals['calories'] >= targets.calories:
        signals.append('calorie_target_reached')
        reasons.append('Os registros com calorias já alcançam a meta diária que você informou; opções leves podem combinar com sua próxima escolha, respeitando a fome descrita.')
    if foods and any(count < len(foods) for count in counts.values()):
        limitations.append('Há alimentos sem quantidades ou macros informados; o consumo diário conhecido é parcial e não permite calcular um saldo completo.')
    if not foods and goal:
        limitations.append('Você ainda não registrou o que comeu hoje; não presumimos que esteja em jejum.')
    if foods:
        limitations.append('O contexto usa apenas os alimentos que você informou; pode haver outras refeições não registradas.')
    context = DietContext(date=day, goal=goal, details=profile.diet_plan.details,
                          meal_count=len(foods), foods=[f[:200] for f in foods[-12:]],
                          known_intake=DailyNutrients(**totals), known_counts=counts,
                          targets=targets, remaining=DailyNutrients(**remaining), signals=signals,
                          reasons=reasons, limitations=limitations)
    return context, clean


def apply_diet_context(intent: MealIntent, context: DietContext, message: str) -> MealIntent:
    if not (context.goal or context.details or context.meal_count or any(v is not None for v in context.targets.model_dump().values())):
        return intent
    goals, inferred = list(intent.goals), list(intent.inferred_goals)
    nutritional = intent.nutrition_preferences
    suggestions = []
    protein_reached = 'protein_target_reached' in context.signals
    if (not protein_reached and (context.goal in ('gain_muscle', 'performance')
            or 'fruit_only_records' in context.signals or 'protein_target_remaining' in context.signals)):
        if not re.search(r'\b(?:pouca proteina|sem proteina|nao quero (?:mais |muita )?proteina)\b', normalized(message)):
            suggestions.append('protein')
            nutritional = merge_preferences(NutritionPreferences(goals=['high_protein']), nutritional)
    if (context.goal == 'gain_muscle' and 'fruit_only_records' in context.signals
            and not protein_reached and 'calorie_target_reached' not in context.signals):
        if (not any(g in goals for g in ('large_portion', 'small_portion', 'light'))
                and nutritional.max_calories is None and 'low_calorie' not in nutritional.goals):
            suggestions.append('large_portion')
    if ((context.goal == 'lose_weight' or 'calorie_target_reached' in context.signals)
            and not re.search(r'\bnao quero (?:algo |comida |refeicao )?leve\b', normalized(message))):
        suggestions.append('light')
        # Evita transformar o objetivo em prescrição de porção pequena ou de jejum.
        nutritional = merge_preferences(NutritionPreferences(goals=['low_calorie']), nutritional)
    labels = {'protein': 'opções com fontes de proteína', 'large_portion': 'refeição mais reforçada',
              'light': 'refeição leve'}
    added = []
    for goal in suggestions:
        if goal not in goals:
            goals.append(goal)
            inferred.append(goal)
            added.append(labels[goal])
    provider_query = intent.provider_query
    if not intent.food_query and 'large_portion' in suggestions:
        provider_query = 'refeição porção grande'
    return intent.model_copy(update={
        'goals': goals, 'inferred_goals': inferred, 'nutrition_preferences': nutritional,
        'labels': list(dict.fromkeys(intent.labels + added + preference_labels(nutritional))),
        'diet_context': context, 'provider_query': provider_query,
        'inferences': (intent.inferences + context.reasons)[:5],
    })
