"""A avaliação do pedido viaja dentro do payload da sessão; não há tabela de pedidos separada."""
import json

from app.schemas.macro import OrderRecord, OrderReview, OrderReviewInput, ReviewInterpretation, Session, UserProfile
from app.storage.database import Database


def test_order_review_round_trips_through_session_storage(tmp_path):
    db = Database(tmp_path / 'test.sqlite3')
    session = Session(mode='mock', profile=UserProfile(id='user'))
    session.order = OrderRecord(id='demo-order-1', cart_id='cart', status='submitted', simulated=True,
                                review=OrderReview(rating=4, comment='Boa porção'))
    db.save(session)
    assert db.get(session.id).order.review == OrderReview(rating=4, comment='Boa porção')


def test_order_review_is_trimmed_and_legacy_orders_load_without_it(tmp_path):
    assert OrderReviewInput(comment='  ' + 'a' * 250).comment == 'a' * 200
    assert OrderReviewInput().empty and not OrderReviewInput(comment='ok').empty
    db = Database(tmp_path / 'test.sqlite3')
    session = Session(mode='mock', profile=UserProfile(id='user'))
    # Payload gravado antes do campo existir.
    legacy = session.model_dump(mode='json')
    legacy['order'] = {'id': 'demo-order-0', 'cart_id': 'cart', 'status': 'submitted',
                       'simulated': True, 'created_at': '2026-01-01T00:00:00Z'}
    with db.transaction() as connection:
        connection.execute('INSERT INTO sessions VALUES (?, ?)', (session.id, json.dumps(legacy)))
    assert db.get(session.id).order.review is None


def test_effective_values_prefer_user_over_interpretation():
    review = OrderReview(comment='x', aspects={'taste': 5},
                         interpretation=ReviewInterpretation(rating=2, aspects={'taste': 1, 'delivery': 2}))
    assert review.effective_rating == 2
    assert review.effective_aspects == {'taste': 5, 'delivery': 2, 'value_for_money': None, 'portion_size': None}
    assert review.model_copy(update={'rating': 4}).effective_rating == 4
    assert OrderReview(comment='x').effective_rating is None
