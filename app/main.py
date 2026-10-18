import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import router as macro_router
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logs import configurar_logs
from app.core.search_logs import configurar_busca_logs
from app.services.mock_reviews import review_dataset
from app.services.review_processing import processed_reviews
from app.storage.database import Database


def create_app() -> FastAPI:
    settings = get_settings()
    configurar_logs(settings.calorias_log)
    configurar_busca_logs(settings.busca_log)

    @asynccontextmanager
    async def lifespan(app):
        task = None
        if settings.catalog_enrichment_enabled and settings.ifood_mode == "live":
            from app.services.catalog_enrichment import worker

            task = asyncio.create_task(worker(settings))
        yield
        if task:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

    app = FastAPI(
        lifespan=lifespan,
        title=settings.app_name,
        version=settings.version,
        debug=settings.debug,
    )

    # Inicializar banco de dados SQLite da sessão
    app.state.settings = settings
    app.state.db = Database(settings.database_path)
    initial_reviews = app.state.db.reviews(settings.ifood_mode == "mock")
    if settings.ifood_mode == "mock":
        initial_reviews += review_dataset().reviews
    processed_reviews(app.state.db, initial_reviews, settings.ifood_mode == "mock")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_exception_handlers(app)

    # Rotas consumidas pelo frontend (/api/session, /api/search, etc.)
    app.include_router(macro_router, prefix="/api")

    # Rotas versionadas da API (/api/v1/health, etc.)
    app.include_router(api_router, prefix=settings.api_v1_prefix)
    return app


app = create_app()
