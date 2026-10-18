from functools import lru_cache
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Macro · Hackathon iFood API"
    version: str = "0.1.0"
    environment: str = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = ["*"]

    # Modo e persistência
    ifood_mode: Literal["mock", "live"] = "mock"
    database_path: Path = Path("data/macro.sqlite3")
    timezone: str = "America/Sao_Paulo"

    # OpenRouter
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "google/gemma-4-31b-it:free"
    openrouter_fallback_models: list[str] = [
        "nvidia/nemotron-3-super-120b-a12b:free",
        "google/gemma-4-26b-a4b-it:free",
        "openrouter/free",
    ]
    openrouter_timeout: float = 60.0

    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.8-flash"
    gemini_fallback_models: list[str] = ["gemini-flash-latest"]
    gemini_retries: int = 3
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    gemini_timeout: float = 60.0

    ifood_mcp_url: str = "https://consumer-mcp.ifood.com.br/marketplace"
    ifood_client_id: str = ""
    ifood_client_secret: str = ""
    ifood_redirect_uri: str = "http://localhost:4000"
    ifood_scopes: str = "openid discovery:read"
    ifood_token_file: str = ".ifood_tokens.json"
    mcp_timeout_seconds: float = Field(default=20, gt=0, le=120)

    # Pipeline nutricional (Gemini para imagem, OpenRouter para texto). Sem chaves, a nutrição fica
    # "unavailable" e o resto funciona.
    nutrition_timeout_seconds: float = Field(default=60, gt=0, le=300)
    # O frontend aborta requisições em 30 s; o que passar disso volta "pending" e termina em segundo plano.
    nutrition_response_budget_seconds: float = Field(default=20, gt=0, le=28)
    nutrition_concurrency: int = Field(default=3, ge=1, le=10)

    # Cascata de calorias (ver pipeline_calorias_v2.dot).
    calorias_estimar_sempre: bool = True  # False: só estima se bases e web não acharem (poupa cota)
    calorias_buscar_bases: bool = True
    calorias_busca_web: bool = True  # Gemini com Google Search; só roda se as bases não acharem
    calorias_amostras: int = Field(default=1, ge=1, le=5)
    calorias_limiar_confianca: float = Field(default=0.55, ge=0, le=1)
    calorias_base_path: Path = Path("app/services/nutrition/dados/produtos.json")
    calorias_dados_dir: Path = Path("app/services/nutrition/dados")

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except Exception:
            return "America/Sao_Paulo"
        return value

    def public_status(self) -> dict:
        return {
            "mode": self.ifood_mode,
            "simulated": self.ifood_mode == "mock",
            "live_orders_enabled": False,
            "nutrition": "enabled" if (self.gemini_api_key or self.openrouter_api_key) else "unavailable",
            "timezone": self.timezone,
            "issues": (
                ["Demonstração com catálogo, endereço, preços e pedidos fictícios."]
                if self.ifood_mode == "mock"
                else (
                    ["Configure IFOOD_CLIENT_ID e IFOOD_CLIENT_SECRET no backend."]
                    if not self.ifood_client_id
                    else ["Credenciais configuradas; acesso depende de autorização OAuth."]
                )
            )
            + ["Checkout real bloqueado até validar contratos e ambiente autorizado."],
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()
