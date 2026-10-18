"""Personalização determinística por avaliações, sem chamadas externas.

Notas são centradas em 3. Afinidade por cozinha usa prior neutro de duas
avaliações. A comunidade exclui o próprio usuário e usa prior 3,5 com peso 3.
Reviews simuladas nunca entram no contexto live.
"""
from dataclasses import dataclass, field

from app.schemas.macro import MealCandidate, ReviewSignal, UserProfile
from app.schemas.reviews import ProcessedReview, Review, UserTastes
from app.services.review_processing import TRAIT_LABELS, processed_reviews, user_tastes
from app.services.mock_reviews import review_dataset
from app.storage.database import Database


@dataclass
class ReviewContext:
    history: list[Review] = field(default_factory=list)
    community: list[Review] = field(default_factory=list)
    cuisines: dict[str, list[str]] = field(default_factory=dict)
    simulated: bool = False
    processed: dict[str, ProcessedReview] = field(default_factory=dict)
    tastes: UserTastes | None = None


def review_context(db: Database, user_id: str, simulated: bool, profile: UserProfile | None = None) -> ReviewContext:
    saved = db.reviews(simulated)
    context = ReviewContext(simulated=simulated)
    if simulated:
        data = review_dataset()
        context.cuisines = {m.merchant_id: m.cuisines for m in data.establishments}
        names = {m.merchant_id: m.name for m in data.establishments}
        context.history = [r.model_copy(update={'user_id': user_id, 'merchant_name': names[r.merchant_id]}) for r in data.reviews
                           if r.user_id == data.default_user_id]
        context.community = [r for r in data.reviews if r.user_id != data.default_user_id]
    # Uma nova nota substitui a anterior do mesmo usuário/item, inclusive a seed.
    own = {(r.merchant_id, r.item_id): r for r in context.history}
    for review in saved:
        if review.user_id == user_id:
            own[review.merchant_id, review.item_id] = review
        else:
            context.community.append(review)
    context.history = sorted(own.values(), key=lambda r: (r.created_at, r.id), reverse=True)
    context.processed = processed_reviews(db, context.history + context.community, simulated)
    if profile is None:
        session = db.get(user_id)
        profile = session.profile if session and (session.mode == 'mock') == simulated else UserProfile(id=user_id)
    context.tastes = user_tastes(db, profile, context.history, context.cuisines, context.processed, simulated)
    return context


def review_signal(candidate: MealCandidate, context: ReviewContext) -> tuple[ReviewSignal, list[str]]:
    # Evita aplicar avaliações fictícias a candidatos reais, mesmo com IDs iguais.
    if candidate.simulated != context.simulated:
        return ReviewSignal(source='unavailable', score=0, history_count=0, review_count=0), []
    public = [r for r in context.community if r.merchant_id == candidate.merchant_id]
    own = [r for r in context.history if r.merchant_id == candidate.merchant_id]
    exact = [r for r in own if r.item_id == candidate.item_id]
    latest = max(exact or own, key=lambda r: (r.created_at, r.id), default=None)
    # Afinidade transferida para outros restaurantes com as mesmas cozinhas.
    affinities = []
    cuisine_evidence = []
    for cuisine in context.cuisines.get(candidate.merchant_id, []):
        relevant = [r for r in context.history if cuisine in context.cuisines.get(r.merchant_id, [])]
        if relevant:
            cuisine_affinity = (context.tastes.cuisine_affinities.get(cuisine, 0) if context.tastes else
                               sum((r.rating - 3) / 2 for r in relevant) / (len(relevant) + 2))
            affinities.append(cuisine_affinity)
            liked = [r for r in relevant if r.rating >= 4]
            if cuisine_affinity > 0 and liked:
                evidence = max(liked, key=lambda r: (r.created_at, r.id))
                cuisine_evidence.append((cuisine, evidence))
    affinity = sum(affinities) / len(affinities) if affinities else 0
    average = sum(r.rating for r in public) / len(public) if public else None
    community_score = ((sum(r.rating for r in public) + 3 * 3.5) / (len(public) + 3) - 3.5) / 1.5
    direct = (latest.rating - 3) / 2 if latest else 0
    # A evidência direta tem mais peso que a afinidade inferida; sem dados, score zero.
    text_affinity, aspect_score = 0, 0
    trait_evidence = []
    if context.tastes and public:
        for trait, interest in context.tastes.trait_interests.items():
            values = [context.processed[r.id].traits[trait] for r in public
                      if r.id in context.processed and trait in context.processed[r.id].traits]
            if values:
                quality = sum(values) / (len(values) + 2)
                text_affinity += interest * quality
                if quality:
                    trait_evidence.append((abs(interest * quality), trait, quality))
        weights = context.tastes.aspect_importance
        aspect_score = sum(
            weight * sum(context.processed[r.id].aspect_scores[aspect] for r in public) / (len(public) + 3)
            for aspect, weight in weights.items()
        ) / sum(weights.values())
    score = (community_score if public else 0) + 2 * affinity + 3 * direct + text_affinity + 0.5 * aspect_score
    personalized = bool(latest or affinities or trait_evidence)
    reasons = []
    if latest:
        target = 'este prato' if exact else 'este restaurante'
        if latest.rating >= 4:
            reasons.append(
                f'Você já gostou deste prato e deu nota {latest.rating}/5. É uma opção para repetir algo que aprovou.'
                if exact else
                f'Este prato é do {candidate.merchant_name}, onde você já avaliou outra opção com {latest.rating}/5.'
            )
        elif latest.rating <= 2:
            reasons.append(f'Vale considerar sua experiência anterior: você deu {latest.rating}/5 para {target}.')
        else:
            reasons.append(f'Sua avaliação anterior de {target} foi 3/5; ela não indica uma preferência forte.')
    if affinity > 0 and cuisine_evidence:
        for cuisine, evidence in cuisine_evidence[:2]:
            reference = f' no {evidence.merchant_name}' if evidence.merchant_name else ''
            reasons.append(
                f'A cozinha {cuisine} deste restaurante combina com seu histórico: '
                f'você deu {evidence.rating}/5 a uma opção dessa cozinha{reference}.'
            )
    elif affinity < 0:
        cuisines = ', '.join(context.cuisines.get(candidate.merchant_id, []))
        reasons.append(f'Suas avaliações anteriores indicam menor afinidade com as cozinhas: {cuisines}.')
    for _, trait, quality in sorted(trait_evidence, reverse=True)[:1]:
        observation = 'elogiam' if quality > 0 else 'apontam problemas com'
        reasons.append(
            f'Você mencionou {TRAIT_LABELS[trait]} nas suas avaliações; '
            f'outras pessoas {observation} esse aspecto neste restaurante.'
        )
    if average is not None:
        reasons.append(f'Nota {average:.1f}/5 em {len(public)} avaliações de outras pessoas.')
    if not personalized:
        reasons.append('Sem histórico relacionado a esta opção; usamos as avaliações disponíveis.'
                       if public else 'Sem avaliações relacionadas; usamos sua busca e preferências.')
    return ReviewSignal(
        source='personalized' if personalized else 'community' if public else 'unavailable',
        score=round(score, 4), history_count=len(context.history), review_count=len(public),
        community_rating=round(average, 2) if average is not None else None,
        cuisine_affinity=round(affinity, 4), personal_rating=latest.rating if latest else None,
        text_affinity=round(text_affinity, 4), aspect_score=round(aspect_score, 4),
        pipeline_version=context.tastes.pipeline_version if context.tastes else None,
    ), reasons
