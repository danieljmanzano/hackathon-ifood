"""Preferências por refeição: interpretação local e comparação com dados nutricionais."""
import re
from dataclasses import dataclass

from app.schemas.macro import MealIntent, NutritionPreferences, NutritionResult, Recommendation, UserProfile
from app.services.review_processing import normalized

LABELS = {
    "high_protein": "mais proteína", "low_carb": "menos carboidratos",
    "low_fat": "menos gordura", "low_calorie": "menos calorias",
}
PATTERNS = {
    "high_protein": r"(?:mais|bastante|muita) proteina[s]?|ric[oa] em proteina[s]?|alt[oa] (?:em |teor de )?proteina[s]?|hiperproteic[oa]|proteic[oa]",
    "low_carb": r"low[ -]?carb|(?:menos|pouc[oa]s?|baix[oa]s?) carboidratos?|baix[oa] (?:em |teor de )carboidratos?",
    "low_fat": r"(?:menos|pouc[oa]|baix[oa]) gordura|baix[oa] (?:em |teor de )gordura",
    "low_calorie": r"(?:menos|poucas|baixas) calorias|baix[oa] (?:em |teor de )calorias|hipocaloric[oa]",
}
NUMBER = r"(\d+(?:[.,]\d+)?)"
LIMITS = {
    "max_calories": rf"(?:ate|no maximo|menos de|abaixo de|limite de)\s*{NUMBER}\s*(?:kcal|calorias)",
    "min_protein_g": rf"(?:pelo menos|no minimo|minimo de|mais de|acima de)\s*{NUMBER}\s*g(?:ramas)?\s*(?:de\s+)?proteina[s]?",
    "max_carbs_g": rf"(?:ate|no maximo|menos de|abaixo de|limite de)\s*{NUMBER}\s*g(?:ramas)?\s*(?:de\s+)?carboidratos?",
    "max_fat_g": rf"(?:ate|no maximo|menos de|abaixo de|limite de)\s*{NUMBER}\s*g(?:ramas)?\s*(?:de\s+)?gordura[s]?",
}


def without_daily_targets(text: str) -> str:
    working = normalized(text)
    # Metas diárias pertencem ao acompanhamento, não ao limite de um prato.
    working = re.sub(r"\b(?:minha )?meta (?:diaria|do dia)(?: de)?\s*(?:ate\s*)?\d+(?:[.,]\d+)?\s*(?:kcal|calorias)\b", " ", working)
    working = re.sub(r"\b(?:ate\s*)?\d+(?:[.,]\d+)?\s*(?:kcal|calorias)\s*(?:por dia|diarias|/\s*dia)\b", " ", working)
    return working


def extract_preferences(text: str) -> tuple[str, NutritionPreferences]:
    """Retira metas do texto antes de interpretar orçamento ou alimentos."""
    working = without_daily_targets(text)
    fields, goals = {}, []
    for field, pattern in LIMITS.items():
        def limit(match):
            prefix = working[:match.start()]
            if not re.search(r"\bnao (?:quero |preciso |seja )?$", prefix):
                fields[field] = float(match[1].replace(",", "."))
            return " "
        working = re.sub(r"\b(?:" + pattern + r")\b", limit, working)
    for goal, pattern in PATTERNS.items():
        def preference(match):
            if not re.search(r"\b(?:nao|sem)(?:\s+\w+){0,2}\s+$", working[:match.start()]):
                if goal not in goals:
                    goals.append(goal)
            return " "
        working = re.sub(r"\b(?:" + pattern + r")\b", preference, working)
    return working, NutritionPreferences(goals=goals, **fields)


def merge_preferences(base: NutritionPreferences, override: NutritionPreferences) -> NutritionPreferences:
    fields = base.model_dump()
    for key, value in override.model_dump().items():
        if key == "goals":
            fields[key] = list(dict.fromkeys(fields[key] + value))
        elif value is not None:
            fields[key] = value
    return NutritionPreferences(**fields)


def preference_labels(preferences: NutritionPreferences) -> list[str]:
    labels = [LABELS[g] for g in dict.fromkeys(preferences.goals)]
    for field, template in (
        ("max_calories", "até {:g} kcal por prato"),
        ("min_protein_g", "pelo menos {:g} g de proteína por prato"),
        ("max_carbs_g", "até {:g} g de carboidratos por prato"),
        ("max_fat_g", "até {:g} g de gordura por prato"),
    ):
        value = getattr(preferences, field)
        if value is not None:
            labels.append(template.format(value))
    return labels


def apply_profile_preferences(intent: MealIntent, profile: UserProfile) -> MealIntent:
    preferences = merge_preferences(profile.nutrition_preferences, intent.nutrition_preferences)
    if "protein" in intent.goals and "protein" not in intent.inferred_goals and "high_protein" not in preferences.goals:
        preferences = preferences.model_copy(update={"goals": preferences.goals + ["high_protein"]})
    return intent.model_copy(update={
        "nutrition_preferences": preferences,
        "labels": list(dict.fromkeys(intent.labels + preference_labels(preferences))),
    })


@dataclass
class NutritionFit:
    score: float
    reasons: list[str]
    limitations: list[str]


def assess_nutrition(nutrition: NutritionResult, preferences: NutritionPreferences) -> NutritionFit:
    if not preferences.active:
        return NutritionFit(0, [], [])
    scores, reasons, limitations = [], [], []
    if nutrition.state != "ready":
        return NutritionFit(0, [], ["Preferências nutricionais ainda não verificadas: faltam calorias ou macros deste prato."])
    # Escalas de ordenação relativas, não metas nutricionais prescritas.
    metrics = {
        "high_protein": ("protein_g", 30, "proteína", True),
        "low_carb": ("carbs_g", 40, "carboidratos", False),
        "low_fat": ("fat_g", 20, "gordura", False),
        "low_calorie": ("calories", 500, "calorias", False),
    }
    for goal in dict.fromkeys(preferences.goals):
        field, scale, label, higher = metrics[goal]
        value = getattr(nutrition, field)
        if value is None:
            scores.append(0)
            limitations.append(f"Sem dados de {label} para comparar sua preferência.")
            continue
        scores.append(value / (value + scale) if higher else scale / (scale + value))
        unit = "kcal" if field == "calories" else "g"
        reasons.append(f"Sua preferência por {LABELS[goal]} entrou na comparação: estimativa de {value:g} {unit}{'' if field == 'calories' else ' de ' + label} por prato.")
    for field, metric, label, minimum in (
        ("max_calories", "calories", "kcal", False),
        ("min_protein_g", "protein_g", "g de proteína", True),
        ("max_carbs_g", "carbs_g", "g de carboidratos", False),
        ("max_fat_g", "fat_g", "g de gordura", False),
    ):
        target = getattr(preferences, field)
        if target is None:
            continue
        value = getattr(nutrition, metric)
        if value is None:
            scores.append(0)
            limitations.append(f"Não foi possível verificar sua preferência de {'no mínimo' if minimum else 'até'} {target:g} {label} por prato.")
            continue
        matches = value >= target if minimum else value <= target
        scores.append(1 if matches else value / target if minimum else (target / value))
        statement = f"Estimativa de {value:g} {label} por prato; você pediu {'pelo menos' if minimum else 'até'} {target:g} {label}."
        (reasons if matches else limitations).append(statement)
    if nutrition.revisar:
        limitations.append("A estimativa nutricional está marcada para revisão; os valores podem mudar.")
    if any(getattr(preferences, k) is not None for k in LIMITS) or preferences.goals:
        limitations.append("A adequação nutricional usa estimativas por prato, antes dos adicionais; não garante os limites informados.")
    return NutritionFit(round(3 * sum(scores) / len(scores), 6) if scores else 0, reasons, limitations)


def update_explanation(before: Recommendation, after: Recommendation,
                       preferences: NutritionPreferences) -> Recommendation:
    """Atualiza a justificativa quando uma estimativa pendente chega, sem trocar os cards."""
    if not preferences.active:
        return after
    previous = assess_nutrition(before.nutrition, preferences)
    current = assess_nutrition(after.nutrition, preferences)
    return after.model_copy(update={
        "reasons": current.reasons + [r for r in after.reasons if r not in previous.reasons],
        "limitations": [l for l in after.limitations if l not in previous.limitations] + current.limitations,
    })


def meets_explicit_limits(nutrition: NutritionResult, preferences: NutritionPreferences) -> bool | None:
    """False: violação conhecida; None: não verificável; True: valores conhecidos atendem.

    Os valores podem ser estimados; True não transforma uma estimativa em garantia.
    """
    unknown = False
    for field, metric, minimum in (
        ('max_calories', 'calories', False), ('min_protein_g', 'protein_g', True),
        ('max_carbs_g', 'carbs_g', False), ('max_fat_g', 'fat_g', False),
    ):
        target = getattr(preferences, field)
        if target is None:
            continue
        value = getattr(nutrition, metric) if nutrition.state == 'ready' else None
        if value is None:
            unknown = True
        elif (value < target if minimum else value > target):
            return False
    return None if unknown else True
