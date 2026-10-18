from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MACRO_", env_file=".env", extra="ignore")

    ifood_mode: Literal["mock", "live"] = "mock"
    database_path: Path = Path("data/macro.sqlite3")
    timezone: str = "America/Sao_Paulo"
    ifood_endpoint: str = "https://consumer-mcp.ifood.com.br/marketplace"
    ifood_access_token: SecretStr = SecretStr("")
    mcp_timeout_seconds: float = Field(default=20, gt=0, le=120)

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value: str) -> str:
        ZoneInfo(value)
        return value

    @field_validator("ifood_endpoint")
    @classmethod
    def valid_endpoint(cls, value: str) -> str:
        if value != "https://consumer-mcp.ifood.com.br/marketplace":
            raise ValueError("Use o endpoint documentado; outros ambientes exigem validação prévia.")
        return value

    def public_status(self) -> dict:
        return {
            "mode": self.ifood_mode,
            "simulated": self.ifood_mode == "mock",
            "live_orders_enabled": False,
            "nutrition": "unavailable",
            "timezone": self.timezone,
            "issues": (["Demonstração com catálogo, endereço, preços e pedidos fictícios."]
                       if self.ifood_mode == "mock" else
                       (["Configure MACRO_IFOOD_ACCESS_TOKEN no backend."]
                        if not self.ifood_access_token.get_secret_value() else
                        ["Token configurado; acesso ainda depende de diagnóstico autenticado."]) +
                       ["Checkout real bloqueado até validar contratos e ambiente autorizado."]),
        }
