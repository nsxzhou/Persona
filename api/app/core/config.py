from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = Field(
        default="postgresql+asyncpg://persona:persona@localhost:5432/persona",
        alias="PERSONA_DATABASE_URL",
    )
    encryption_key: str = Field(alias="PERSONA_ENCRYPTION_KEY")
    session_cookie_name: str = Field(default="persona_session", alias="PERSONA_SESSION_COOKIE_NAME")
    session_cookie_secure: bool = Field(default=True, alias="PERSONA_SESSION_COOKIE_SECURE")
    session_ttl_hours: int = Field(default=24 * 14, alias="PERSONA_SESSION_TTL_HOURS")
    session_secret: str | None = Field(default=None, alias="PERSONA_SESSION_SECRET")
    cors_allowed_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000"],
        alias="PERSONA_CORS_ALLOWED_ORIGINS",
    )
    llm_timeout_seconds: float = Field(default=15.0, alias="PERSONA_LLM_TIMEOUT_SECONDS")
    llm_max_retries: int = Field(default=2, alias="PERSONA_LLM_MAX_RETRIES")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

