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
    # Quando a busca não acha nada, um modelo replaneja (outras consultas, relaxar o orçamento padrão) ou explica.
    busca_replanejar: bool = True
    busca_web_timeout_seconds: float = Field(default=10, gt=0, le=20)
    busca_web_identificar: bool = True  # pesquisar na web o que é um produto/nome que o pedido cita e o sistema não conhece
    busca_max_replanejamentos: int = Field(default=1, ge=0, le=2)
    busca_prazo_total_segundos: float = Field(default=28, gt=0, le=29)  # o frontend desiste aos 30 s
    busca_replanejar_timeout_seconds: float = Field(default=10, gt=0, le=20)
    # No modo live o planejador pode explorar o iFood com tools de LEITURA do MCP (categorias, restaurantes, cardápio).
    busca_mcp_ferramentas: bool = True
    busca_max_passos_planejador: int = Field(default=2, ge=1, le=3)  # perguntas ao modelo por rodada (1 pode ser exploração)
    # Por privacidade os logs da busca só têm contagens. Ligue para ver consultas e respostas dos modelos (depuração).
    busca_log_conteudo: bool = False
    # Quanto da conversa o agente de busca lê (0 desliga): últimas N mensagens, cortadas em M caracteres cada.
    busca_historico_mensagens: int = Field(default=6, ge=0, le=20)
    busca_historico_max_caracteres: int = Field(default=300, ge=50, le=1000)
    intent_llm_enabled: bool = True
    intent_llm_timeout_seconds: float = Field(default=18, gt=0, le=20)
    # Interpretação da avaliação livre do pedido; roda em segundo plano, então tolera mais tempo.
    review_llm_enabled: bool = True
    review_llm_timeout_seconds: float = Field(default=30, gt=0, le=60)

    # Se o provedor de texto falhar (cota, 429, fora do ar), tenta o outro, desde que a chave dele exista:
    # OpenRouter -> OpenAI (pago) e OpenAI -> OpenRouter. Vale para a busca, o agente e o pipeline de calorias.
    # Desligado por padrão: tudo vai só para o provedor escolhido (OpenAI, NUTRITION_MODEL).
    llm_fallback: bool = False
    # Quanto o provedor principal pode demorar antes de a reserva assumir. Sem isso, a cadeia de modelos
    # gratuitos do OpenRouter pode gastar todo o prazo da chamada e a reserva nunca chega a rodar.
    llm_fallback_apos_segundos: float = Field(default=20, gt=0, le=120)

    # OpenAI (usada quando NUTRITION_PROVIDER=openai; a chave e o modelo ficam na seção de nutrição abaixo)
    openai_base_url: str = "https://api.openai.com/v1"
    openai_timeout: float = 60.0
    # Raciocínio dos modelos GPT-5: é cobrado como saída e o padrão da OpenAI (medium) gasta muito.
    # "minimal" não aceita web_search, então a busca na web usa OPENAI_REASONING_EFFORT_WEB.
    openai_reasoning_effort: Literal["minimal", "low", "medium", "high"] = "minimal"
    openai_reasoning_effort_web: Literal["low", "medium", "high"] = "low"

    ifood_mcp_url: str = "https://consumer-mcp.ifood.com.br/marketplace"
    ifood_client_id: str = ""
    ifood_client_secret: str = ""
    ifood_redirect_uri: str = "http://localhost:4000"
    ifood_scopes: str = "openid discovery:read"
    ifood_token_file: str = ".ifood_tokens.json"
    mcp_timeout_seconds: float = Field(default=20, gt=0, le=120)

    # Pipeline nutricional. Sem a chave do provedor escolhido, a nutrição fica "unavailable" e o resto funciona.
    # openai: GPT pago (texto, imagens e busca na web nativa). openrouter: modelos gratuitos só para o texto
    # (sem busca na web e sem leitura das imagens). Escolha ao subir: python -m app.run --llm openai|openrouter
    nutrition_provider: Literal["openai", "openrouter"] = "openai"
    openai_api_key: SecretStr = SecretStr("")
    nutrition_model: str = "gpt-5-mini"
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
    nutrition_timeout_seconds: float = Field(default=60, gt=0, le=300)
    # O frontend aborta requisições em 30 s; o que passar disso volta "pending" e termina em segundo plano.
    nutrition_response_budget_seconds: float = Field(default=20, gt=0, le=28)
    # A busca responde sem esperar as calorias (os cards mostram "Calculando…" e a tela atualiza sozinha).
    # Um prazo curto ainda entrega na hora o que já está em cache ou é muito rápido.
    nutrition_search_budget_seconds: float = Field(default=1, ge=0, le=28)
    nutrition_concurrency: int = Field(default=3, ge=1, le=10)
    # Catálogo real: enriquecimento incremental e orçamento persistido (independente da busca).
    catalog_enrichment_enabled: bool = True
    catalog_products_per_search: int = Field(default=3, ge=0, le=10)
    catalog_products_per_day: int = Field(default=20, ge=0)
    catalog_calls_per_product: int = Field(default=8, ge=0, le=30)
    catalog_calls_per_day: int = Field(default=60, ge=0)
    catalog_max_output_tokens: int = Field(default=1800, ge=256, le=8000)
    catalog_max_input_chars: int = Field(default=24000, ge=1000, le=100000)
    catalog_retry_seconds: int = Field(default=900, ge=1)
    catalog_max_attempts: int = Field(default=2, ge=1, le=5)
    live_mock_reviews: bool = True

    # Cascata de calorias (ver pipeline_calorias_v2.dot).
    calorias_estimar_sempre: bool = False  # True: estima mesmo se bases ou web acharem (mede divergência, gasta mais)
    calorias_buscar_bases: bool = True
    calorias_classificar: bool = True  # produto de marca: tabela oficial na web ANTES das bases genéricas
    calorias_busca_web: bool = True  # OpenAI web_search ou Gemini+Google Search; só roda se as bases não acharem
    calorias_log: Literal["off", "resumo", "detalhe"] = "resumo"  # ver app/core/logs.py
    calorias_amostras: int = Field(default=1, ge=1, le=5)
    calorias_limiar_confianca: float = Field(default=0.55, ge=0, le=1)
    calorias_base_path: Path = Path("app/services/nutrition/dados/produtos.json")
    calorias_dados_dir: Path = Path("app/services/nutrition/dados")

    @property
    def llm_api_key(self) -> str:
        """Chave do provedor de texto escolhido (ou a do outro, se faltar e o fallback estiver ligado)."""
        openai, openrouter = self.openai_api_key.get_secret_value(), self.openrouter_api_key
        principal, outro = (openai, openrouter) if self.nutrition_provider == "openai" else (openrouter, openai)
        return principal or (outro if self.llm_fallback else "")

    @property
    def web_api_key(self) -> str:
        """Chave da busca na web e da leitura das imagens: só a OpenAI faz as duas (vazio com openrouter)."""
        return self.openai_api_key.get_secret_value() if self.nutrition_provider == "openai" else ""

    @property
    def nutrition_enabled(self) -> bool:
        return bool(self.llm_api_key)

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
            "reviews_simulated": self.ifood_mode == "mock" or self.live_mock_reviews,
            "nutrition": "enabled" if self.nutrition_enabled else "unavailable",
            "intent_interpretation": "llm_configured" if self.intent_llm_enabled and self.llm_api_key else "rules",
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
