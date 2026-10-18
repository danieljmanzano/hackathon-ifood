from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Hackathon iFood API"
    version: str = "0.1.0"
    environment: str = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = ["*"]

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


@lru_cache
def get_settings() -> Settings:
    return Settings()
