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

    ifood_mcp_url: str = "https://consumer-mcp.ifood.com.br/marketplace"
    ifood_client_id: str = ""
    ifood_client_secret: str = ""
    ifood_redirect_uri: str = "http://localhost:4000"
    ifood_scopes: str = "openid discovery:read"
    ifood_token_file: str = ".ifood_tokens.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()
