from fastapi.testclient import TestClient

from fastapi import FastAPI

from app.api.endpoints.mock_reviews import router

app = FastAPI()
app.include_router(router, prefix="/api")
from app.services.mock_reviews import review_dataset


def test_dataset_relations_and_aggregates():
    data = review_dataset()
    assert len({r.id for r in data.reviews}) == len(data.reviews)
    merchants = {m.merchant_id: m for m in data.establishments}
    for review in data.reviews:
        assert review.item_id in merchants[review.merchant_id].item_ids
    for merchant in data.establishments:
        reviews = [r for r in data.reviews if r.merchant_id == merchant.merchant_id]
        assert merchant.rating_count == len(reviews)
        assert merchant.rating == round(sum(r.rating for r in reviews) / len(reviews), 2)
    history = [r for r in data.reviews if r.user_id == data.default_user_id]
    assert len(history) == 6
    assert any(r.rating <= 2 for r in history)
    assert any(r.rating >= 4 for r in history)


def test_mock_review_routes():
    with TestClient(app) as client:
        data = client.get('/api/mock/review-dataset').json()
        assert data['simulated'] is True
        assert len(client.get('/api/mock/establishments').json()) == 24
        history = client.get('/api/mock/users/demo-user/reviews').json()
        assert len(history) == 6
        assert all(r['user_id'] == 'demo-user' for r in history)
        merchant_id = history[0]['merchant_id']
        reviews = client.get(f'/api/mock/establishments/{merchant_id}/reviews').json()
        assert len(reviews) == 12
        assert all(r['merchant_id'] == merchant_id for r in reviews)
        assert client.get('/api/mock/establishments/inexistente/reviews').status_code == 404
        assert client.get('/api/mock/users/sem-historico/reviews').json() == []
