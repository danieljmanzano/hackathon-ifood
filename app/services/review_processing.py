"""Pré-processamento local e versionado; regras limitadas de português, sem LLM."""
import hashlib
import json
import re
import unicodedata

from app.schemas.macro import UserProfile, now
from app.schemas.reviews import ProcessedReview, Review, UserTastes
from app.storage.database import Database

PIPELINE_VERSION = 'reviews-v1'
TRAIT_LABELS = {
    'freshness': 'frescor dos ingredientes',
    'lightness': 'comida com pouco óleo',
    'portion': 'tamanho da porção',
    'delivery': 'rapidez da entrega',
    'value': 'custo-benefício',
}
# Cada par contém expressões favoráveis e desfavoráveis. Só extraímos menções explícitas.
TRAIT_PATTERNS = {
    'freshness': (r'fresc[oa]s?|crocantes?', r'murch[oa]s?|ressecad[oa]s?'),
    'lightness': (r'pouco oleo|leves?', r'gorduros[oa]s?|oleos[oa]s?|pesad[oa]s?'),
    'portion': (r'porcao generosa|porcoes generosas|boa porcao', r'porcao pequena|pouca comida'),
    'delivery': (r'entrega rapida|no prazo|entregou rapido', r'atras[oa]s?|demorou|entrega lenta'),
    'value': (r'bom preco|bom custo.beneficio|preco justo', r'car[oa]s?|preco alto'),
}


def normalized(text: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFKD', text.lower())
                   if not unicodedata.combining(c))


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def review_fingerprint(review: Review) -> str:
    return digest([PIPELINE_VERSION, review.comment, review.rating, review.aspects.model_dump()])


def preprocess_review(review: Review) -> ProcessedReview:
    text = normalized(review.comment)
    traits = {}
    for trait, patterns in TRAIT_PATTERNS.items():
        evidence = []
        for polarity, pattern in zip((1, -1), patterns):
            for match in re.finditer(r'\b(?:' + pattern + r')\b', text):
                prefix = re.split(r'[.,;!?]', text[:match.start()])[-1]
                # "nada oleoso" e "sem atraso" invertem a expressão desfavorável.
                negated = re.search(r'\b(?:nao|nada|sem)(?:\s+\w+){0,2}\s+$', prefix)
                evidence.append(-polarity if negated else polarity)
        if evidence:
            traits[trait] = sum(evidence) / len(evidence)
    return ProcessedReview(
        fingerprint=review_fingerprint(review), pipeline_version=PIPELINE_VERSION,
        normalized_comment=text, centered_rating=(review.rating - 3) / 2,
        aspect_scores={key: (value - 3) / 2 for key, value in review.aspects.model_dump().items()},
        traits=traits,
    )


def processed_reviews(db: Database, reviews: list[Review], simulated: bool) -> dict[str, ProcessedReview]:
    cached = db.processed_reviews(simulated)
    changed = []
    result = {}
    for review in reviews:
        key = review_fingerprint(review)
        if key not in cached:
            cached[key] = preprocess_review(review)
            changed.append(cached[key])
        result[review.id] = cached[key]
    db.save_processed_reviews(changed, simulated)
    return result


def user_tastes(db: Database, profile: UserProfile, history: list[Review],
                cuisines: dict[str, list[str]], processed: dict[str, ProcessedReview],
                simulated: bool) -> UserTastes:
    # IDs, datas, associação a restaurantes e metadados também invalidam o perfil derivado.
    source_hash = digest([PIPELINE_VERSION, profile.model_dump(),
                          [r.model_dump(mode='json') for r in history], cuisines])
    cached = db.get_tastes(profile.id, simulated)
    if cached and cached.source_hash == source_hash:
        return cached
    affinities = {}
    for cuisine in sorted({c for values in cuisines.values() for c in values}):
        related = [r for r in history if cuisine in cuisines.get(r.merchant_id, [])]
        if related:
            affinities[cuisine] = sum(processed[r.id].centered_rating for r in related) / (len(related) + 2)
    # Menções indicam aspectos a considerar, não restrições nem preferências confirmadas.
    interests = {
        trait: sum(trait in processed[r.id].traits for r in history) / (len(history) + 2)
        for trait in TRAIT_LABELS
        if any(trait in processed[r.id].traits for r in history)
    }
    importance = {}
    for aspect in ('taste', 'delivery', 'value_for_money', 'portion_size'):
        # Uma avaliação ruim neste aspecto aumenta seu peso sem zerar os demais.
        importance[aspect] = 1 + sum(max(0, -processed[r.id].aspect_scores[aspect]) for r in history) / (len(history) + 2)
    tastes = UserTastes(
        user_id=profile.id, simulated=simulated, preferences=profile.preferences,
        dislikes=profile.dislikes, restrictions=profile.restrictions,
        cuisine_affinities=affinities, trait_interests=interests,
        aspect_importance=importance, history_count=len(history), source_hash=source_hash,
        pipeline_version=PIPELINE_VERSION, updated_at=now(),
    )
    db.save_tastes(tastes)
    return tastes
