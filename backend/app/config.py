"""Centralised configuration. All sensitive values come from environment / .env."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent  # backend/


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(BASE_DIR.parent / ".env", BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Nancy Investment Intelligence"
    database_url: str = f"sqlite:///{(BASE_DIR / 'data' / 'nii.db').as_posix()}"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Provider selection: "mock" works offline. Others need keys.
    trades_provider: str = "mock"          # mock | house_clerk
    market_data_provider: str = "mock"     # mock | fmp
    fundamentals_provider: str = "mock"    # mock | fmp
    news_provider: str = "mock"            # mock

    # Optional API keys
    fmp_api_key: str | None = None
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-5"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    ai_provider: str = "rules"             # rules | anthropic | openai

    # Polite fetching for official sources
    http_user_agent: str = "NancyInvestmentIntelligence/0.1 (personal research tool)"
    http_timeout_s: float = 20.0

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
