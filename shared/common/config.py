"""Application settings loaded from environment variables.

Each microservice gets its own Settings instance. Common values
(DATABASE_URL, REDIS_URL, JWT_SECRET) are shared via env.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Service configuration loaded from environment.

    All values have safe defaults for local development. In production
    these are injected via env / Docker secrets.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Service identity
    service_name: str = Field(default="service")
    service_version: str = Field(default="0.1.0")
    environment: str = Field(default="development")
    log_level: str = Field(default="INFO")

    # Network
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    cors_origins: List[str] = Field(default_factory=lambda: ["*"])

    # Persistence
    database_url: str = Field(
        default="postgresql+asyncpg://kman:kman@localhost:5432/kman"
    )
    redis_url: str = Field(default="redis://localhost:6379/0")

    # Auth
    jwt_secret: str = Field(default="dev-secret-change-me")
    jwt_algorithm: str = Field(default="HS256")
    jwt_expire_minutes: int = Field(default=60 * 24)

    # AI (hosted first, swap-ready)
    openai_api_key: Optional[str] = Field(default=None)
    anthropic_api_key: Optional[str] = Field(default=None)
    ai_default_model: str = Field(default="gpt-4o-mini")
    ai_request_timeout_seconds: int = Field(default=30)
    ai_max_retries: int = Field(default=3)

    # WhatsApp workspace contract
    whatsapp_webhook_url: Optional[str] = Field(default=None)
    whatsapp_webhook_secret: Optional[str] = Field(default=None)

    # Reporting
    report_output_dir: str = Field(default="/tmp/kman-reports")
    report_schedule_cron: str = Field(default="0 8 * * *")  # 08:00 daily

    # Data pipeline
    pipeline_batch_size: int = Field(default=5_000)
    pipeline_chunk_size_mb: int = Field(default=64)

    # Observability
    enable_metrics: bool = Field(default=True)
    sentry_dsn: Optional[str] = Field(default=None)


@lru_cache
def get_settings() -> Settings:
    """Return cached Settings instance."""
    return Settings()


def get_env_or(name: str, default: str = "") -> str:
    """Read an env var or return default."""
    return os.environ.get(name, default)
