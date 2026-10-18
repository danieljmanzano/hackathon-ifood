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

    # iFood MCP (live)
    ifood_mcp_url: str = "https://consumer-mcp.ifood.com.br/marketplace"
    ifood_client_id: str = ""
    ifood_client_secret: str = ""
    ifood_redirect_uri: str = "http://localhost:4000"
    ifood_scopes: str = "openid discovery:read"
    ifood_token_file: str = ".ifood_tokens.json"

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
            "nutrition": "unavailable",
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
