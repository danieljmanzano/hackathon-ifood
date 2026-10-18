"""Reviews de demonstração persistidas, vinculadas somente a IDs observados no catálogo real."""
import hashlib
from datetime import datetime, timezone

from app.schemas.reviews import Review, ReviewAspects
from app.services.review_processing import processed_reviews, user_tastes
from app.storage.catalog import CatalogStore

COMMENTS = [
    'Avaliação simulada: sabor agradável e porção bem servida.',
    'Avaliação simulada: gostei do sabor, mas achei o preço alto.',
    'Avaliação simulada: boa apresentação, porção menor do que esperava.',
]


def attach_reviews(context, candidates, settings, db, profile):
    if settings.ifood_mode != 'live' or not settings.live_mock_reviews:
        return
    reviews = []
    for c in candidates:
        if c.simulated:
            continue
        identity = hashlib.sha256(f'{c.merchant_id}:{c.item_id}'.encode()).hexdigest()
        for i, comment in enumerate(COMMENTS):
            rating = 3 + ((int(identity[i], 16) + i) % 3)
            reviews.append(Review(id=f'catalog-demo-{identity}-{i}', merchant_id=c.merchant_id,
                                  item_id=c.item_id, merchant_name=c.merchant_name, item_name=c.name,
                                  user_id=f'catalog-demo-user-{i}', rating=rating, comment=comment,
                                  created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                                  aspects=ReviewAspects(taste=rating, delivery=3, value_for_money=3,
                                                       portion_size=4 if i == 0 else 2), simulated=True))
        # Histórico demonstrativo parcial: continuam existindo produtos sem review do usuário.
        if int(identity[:2], 16) % 4 == 0:
            reviews.append(Review(id=f'catalog-demo-own-{identity}-{profile.id}', merchant_id=c.merchant_id,
                                  item_id=c.item_id, merchant_name=c.merchant_name, item_name=c.name,
                                  user_id=profile.id, rating=4,
                                  comment='Avaliação simulada: gostei da porção e do sabor.',
                                  created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                                  aspects=ReviewAspects(taste=4, delivery=3, value_for_money=3, portion_size=4),
                                  simulated=True))
    store = CatalogStore(settings.database_path)
    store.synthetic_reviews(reviews)
    saved = store.saved_synthetic_reviews(profile.id)
    existing = {r.id for r in context.community + context.history}
    own = {(r.merchant_id, r.item_id) for r in context.history}
    for review in saved:
        if review.id in existing:
            continue
        if review.user_id == profile.id:
            if (review.merchant_id, review.item_id) not in own:
                context.history.append(review)
        else:
            context.community.append(review)
    context.synthetic_catalog = bool(saved)
    context.processed = processed_reviews(db, context.history + context.community, False)
    # Perfil de demonstração não sobrescreve o aprendizado real persistido.
    # user_tastes usa um namespace separado; desativar o overlay recompõe o perfil real.
    context.tastes = user_tastes(db, profile, context.history, context.cuisines, context.processed, True)
