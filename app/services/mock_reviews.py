"""Fixtures determinísticas, independentes de sessão e do modo do iFood."""
from pathlib import Path

from app.schemas.reviews import ReviewDataset

DATASET_PATH = Path(__file__).resolve().parents[2] / 'data' / 'mocks' / 'reviews.json'


def review_dataset() -> ReviewDataset:
    # Cada chamada devolve uma cópia validada, sem estado compartilhado mutável.
    return ReviewDataset.model_validate_json(DATASET_PATH.read_text(encoding='utf-8'))
