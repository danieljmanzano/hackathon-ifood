from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.endpoints.macro import router as macro_router
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logs import configurar_logs
from app.storage.database import Database


def create_app() -> FastAPI:
    settings = get_settings()
    configurar_logs(settings.calorias_log)
    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        debug=settings.debug,
    )

    # Inicializar banco de dados SQLite da sessão
    app.state.settings = settings
    app.state.db = Database(settings.database_path)

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
