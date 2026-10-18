from fastapi import APIRouter, HTTPException

from app.schemas.reviews import Establishment, Review, ReviewDataset
from app.services.mock_reviews import review_dataset

router = APIRouter(prefix="/mock", tags=["Mocks de reviews"])


@router.get("/review-dataset", response_model=ReviewDataset)
def dataset():
    return review_dataset()


@router.get("/establishments", response_model=list[Establishment])
def establishments():
    return review_dataset().establishments


@router.get("/establishments/{merchant_id}/reviews", response_model=list[Review])
def merchant_reviews(merchant_id: str):
    data = review_dataset()
    if not any(m.merchant_id == merchant_id for m in data.establishments):
        raise HTTPException(status_code=404, detail="Estabelecimento fictício não encontrado.")
    return [r for r in data.reviews if r.merchant_id == merchant_id]


@router.get("/users/{user_id}/reviews", response_model=list[Review])
def user_reviews(user_id: str):
    return [r for r in review_dataset().reviews if r.user_id == user_id]
