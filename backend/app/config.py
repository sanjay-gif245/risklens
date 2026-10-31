"""Application settings, read from environment variables (or a local .env file)."""

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://localhost:5432/risklens"
    cors_origins: str = "http://localhost:5173"
    log_level: str = "INFO"

    # Annual risk-free rates used for the Sharpe ratio. These are assumptions,
    # not live data: set them to current short-term government bill yields.
    risk_free_rate_usd: float = 0.04
    risk_free_rate_inr: float = 0.065

    history_years: int = 3
    max_holdings: int = 50
    max_upload_bytes: int = 1_000_000

    provider_attempts: int = 3
    provider_backoff_seconds: float = 1.0

    @field_validator("database_url")
    @classmethod
    def use_psycopg_driver(cls, url: str) -> str:
        """Hosting providers hand out postgres:// URLs; SQLAlchemy needs the driver named."""
        for prefix in ("postgres://", "postgresql://"):
            if url.startswith(prefix):
                return "postgresql+psycopg://" + url.removeprefix(prefix)
        return url

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def risk_free_rate(self, currency: str) -> float:
        return self.risk_free_rate_inr if currency == "INR" else self.risk_free_rate_usd


@lru_cache
def get_settings() -> Settings:
    return Settings()
