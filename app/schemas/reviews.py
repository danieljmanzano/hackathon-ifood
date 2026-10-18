"""Contratos dos dados fictícios para experimentos de recomendação por reviews."""

from datetime import datetime

from pydantic import Field

from app.schemas.macro import Cents, Model, Text


class ReviewAspects(Model):
    taste: int = Field(ge=1, le=5)
    delivery: int = Field(ge=1, le=5)
    value_for_money: int = Field(ge=1, le=5)
    portion_size: int = Field(ge=1, le=5)


class ReviewInput(Model):
    merchant_id: str = Field(min_length=1, max_length=200)
    item_id: str = Field(min_length=1, max_length=200)
    rating: int = Field(ge=1, le=5, strict=True)
    comment: Text
    aspects: ReviewAspects


class Review(Model):
    id: str
    merchant_id: str
    item_id: str
    user_id: str
    merchant_name: str | None = None
    item_name: str | None = None
    rating: int = Field(ge=1, le=5)
    comment: str
    created_at: datetime
    aspects: ReviewAspects
    simulated: bool = True


class Establishment(Model):
    merchant_id: str
    name: str
    cuisines: list[str]
    average_price_cents: Cents
    delivery_fee_cents: Cents
    eta_min: int = Field(ge=0)
    eta_max: int = Field(ge=0)
    item_ids: list[str]
    rating: float = Field(ge=1, le=5)
    rating_count: int = Field(ge=0)
    simulated: bool = True


class ReviewDataset(Model):
    simulated: bool = True
    default_user_id: str
    establishments: list[Establishment]
    reviews: list[Review]


class ProcessedReview(Model):
    fingerprint: str
    pipeline_version: str
    normalized_comment: str
    centered_rating: float
    aspect_scores: dict[str, float]
    traits: dict[str, float]


class UserTastes(Model):
    user_id: str
    simulated: bool
    preferences: list[str]
    dislikes: list[str]
    restrictions: list[str]
    cuisine_affinities: dict[str, float]
    trait_interests: dict[str, float]
    aspect_importance: dict[str, float]
    history_count: int
    source_hash: str
    pipeline_version: str
    updated_at: datetime
