"""Rotas públicas da aplicação, agrupadas por responsabilidade."""

from fastapi import APIRouter

from app.api.endpoints import addresses, checkout, diary, macro, mock_reviews, reviews, sessions

router = APIRouter()
for endpoint in (sessions, addresses, diary, reviews, checkout, macro, mock_reviews):
    router.include_router(endpoint.router)
