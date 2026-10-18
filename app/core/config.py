from functools import lru_cache
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Macro · Hackathon iFood API"
    version: str = "0.1.0"
    environment: str = "development"
    debug: bool = False
    busca_log: Literal["off", "resumo", "detalhe"] = "resumo"
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
    intent_llm_enabled: bool = True
    intent_llm_timeout_seconds: float = Field(default=18, gt=0, le=20)
    # Interpretação da avaliação livre do pedido; roda em segundo plano, então tolera mais tempo.
    review_llm_enabled: bool = True
    review_llm_timeout_seconds: float = Field(default=30, gt=0, le=60)

    # OpenAI (usada quando NUTRITION_PROVIDER=openai; a chave e o modelo ficam na seção de nutrição abaixo)
    openai_base_url: str = "https://api.openai.com/v1"
    openai_timeout: float = 60.0

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

    # Pipeline nutricional. Sem a chave do provedor escolhido, a nutrição fica "unavailable" e o resto funciona.
    # openai: GPT pago (melhor qualidade, busca na web nativa). openrouter: modelos gratuitos
    # (e a busca na web passa a ser do Gemini + Google Search). O Gemini lê as imagens nos dois casos.
    # Escolha ao subir: python -m app.run --llm openai|openrouter
    nutrition_provider: Literal["openai", "openrouter"] = "openai"
    openai_api_key: SecretStr = SecretStr("")
    nutrition_model: str = "gpt-5.4-mini"
    # Modelo do OpenRouter e reservas, tentadas em ordem quando o anterior falha ou está no limite.
    # Para estimar com a foto, prefira modelos que aceitam imagem (gemma-4, nemotron-3.5-super-vl).
    nutrition_openrouter_model: str = "google/gemma-4-31b-it:free"
    nutrition_openrouter_fallback_models: list[str] = [
        "google/gemma-4-26b-a4b-it:free",
        "nvidia/nemotron-3.5-super-vl:free",
        "openrouter/free",
    ]
    # O plugin de busca na web do OpenRouter é cobrado por uso, mesmo com modelo gratuito.
    nutrition_openrouter_web_search: bool = False
    nutrition_web_search: bool = True
    # Pipeline nutricional (Gemini para imagem, OpenRouter para texto). Sem chaves, a nutrição fica
    # "unavailable" e o resto funciona.
    nutrition_timeout_seconds: float = Field(default=60, gt=0, le=300)
    # O frontend aborta requisições em 30 s; o que passar disso volta "pending" e termina em segundo plano.
    nutrition_response_budget_seconds: float = Field(default=20, gt=0, le=28)
    # A busca responde sem esperar as calorias (os cards mostram "Calculando…" e a tela atualiza sozinha).
    # Um prazo curto ainda entrega na hora o que já está em cache ou é muito rápido.
    nutrition_search_budget_seconds: float = Field(default=1, ge=0, le=28)
    nutrition_concurrency: int = Field(default=3, ge=1, le=10)

    # Cascata de calorias (ver pipeline_calorias_v2.dot).
    calorias_estimar_sempre: bool = True  # False: só estima se bases e web não acharem (poupa cota)
    calorias_buscar_bases: bool = True
    calorias_busca_web: bool = True  # Gemini com Google Search; só roda se as bases não acharem
    calorias_log: Literal["off", "resumo", "detalhe"] = "resumo"  # ver app/core/logs.py
    calorias_amostras: int = Field(default=1, ge=1, le=5)
    calorias_limiar_confianca: float = Field(default=0.55, ge=0, le=1)
    calorias_base_path: Path = Path("app/services/nutrition/dados/produtos.json")
    calorias_dados_dir: Path = Path("app/services/nutrition/dados")

    @property
    def llm_api_key(self) -> str:
        """Chave do provedor de texto escolhido."""
        return (self.openai_api_key.get_secret_value() if self.nutrition_provider == "openai"
                else self.openrouter_api_key)

    @property
    def web_api_key(self) -> str:
        """Chave de quem faz a busca na web: OpenAI (web_search) ou Gemini (Google Search)."""
        return (self.openai_api_key.get_secret_value() if self.nutrition_provider == "openai"
                else self.gemini_api_key)

    @property
    def nutrition_enabled(self) -> bool:
        return bool(self.llm_api_key or self.gemini_api_key)

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
            "nutrition": "enabled" if self.nutrition_enabled else "unavailable",
            "intent_interpretation": "llm_configured" if self.intent_llm_enabled and self.openrouter_api_key else "rules",
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
