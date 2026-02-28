"""
Настройки приложения через Pydantic Settings.
Читает переменные окружения из .env файла.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Основные настройки приложения."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Telegram Bot
    bot_token: str = Field(..., alias="BOT_TOKEN", description="Токен Telegram бота")
    api_id: int = Field(..., alias="API_ID", description="Telegram API ID для парсера")
    api_hash: str = Field(..., alias="API_HASH", description="Telegram API Hash для парсера")

    # Telethon StringSession
    telethon_session_string: str = Field(
        "",
        alias="TELETHON_SESSION_STRING",
        description="Telethon StringSession для парсера",
    )

    # PostgreSQL
    postgres_user: str = Field("market_bot", alias="POSTGRES_USER")
    postgres_password: str = Field("market_bot_pass", alias="POSTGRES_PASSWORD")
    postgres_db: str = Field("market_bot_db", alias="POSTGRES_DB")
    postgres_port: int = Field(5432, alias="POSTGRES_PORT")
    database_url: PostgresDsn = Field(..., alias="DATABASE_URL")

    # Redis
    redis_port: int = Field(6379, alias="REDIS_PORT")
    redis_url: RedisDsn = Field(..., alias="REDIS_URL")

    # Celery
    celery_broker_url: str = Field(..., alias="CELERY_BROKER_URL")
    celery_result_backend: str = Field(..., alias="CELERY_RESULT_BACKEND")

    # Ports
    api_port: int = Field(8001, alias="API_PORT")
    flower_port: int = Field(5555, alias="FLOWER_PORT")
    nginx_port: int = Field(8080, alias="NGINX_PORT")

    # Environment
    environment: Literal["development", "production", "testing"] = Field(
        "development", alias="ENVIRONMENT"
    )
    debug: bool = Field(False, alias="DEBUG")

    # AI Services
    anthropic_api_key: str | None = Field(None, alias="ANTHROPIC_API_KEY")
    openai_api_key: str | None = Field(None, alias="OPENAI_API_KEY")
    groq_api_key: str | None = Field(None, alias="GROQ_API_KEY")
    openrouter_api_key: str | None = Field(None, alias="OPENROUTER_API_KEY")

    # AI Provider настройки
    ai_provider: str = Field("groq", alias="AI_PROVIDER")  # groq | openai | openrouter | mock
    ai_model: str = Field("llama-3.3-70b-versatile", alias="AI_MODEL")

    # OpenRouter модель (для админов — Claude Sonnet)
    openrouter_model: str = Field("anthropic/claude-sonnet-4-20250514", alias="OPENROUTER_MODEL")

    # AI параметры генерации
    ai_max_tokens: int = Field(1024, alias="AI_MAX_TOKENS")
    ai_temperature: float = Field(0.7, alias="AI_TEMPERATURE")

    # AI Cost
    ai_cost_per_generation: float = Field(10.0, alias="AI_COST_PER_GENERATION")

    # Payments
    yookassa_shop_id: str | None = Field(None, alias="YOOKASSA_SHOP_ID")
    yookassa_secret_key: str | None = Field(None, alias="YOOKASSA_SECRET_KEY")

    # Admin IDs
    admin_ids_raw: str = Field("", alias="ADMIN_IDS")

    # Webhook & Mini App
    webhook_url: str | None = Field(None, alias="WEBHOOK_URL")
    mini_app_url: str | None = Field(None, alias="MINI_APP_URL")

    # Sentry
    sentry_dsn: str | None = Field(None, alias="SENTRY_DSN")

    @property
    def admin_ids(self) -> list[int]:
        """Парсит ADMIN_IDS из строки в список целых чисел."""
        if not self.admin_ids_raw:
            return []
        return [int(x.strip()) for x in self.admin_ids_raw.split(",") if x.strip().isdigit()]

    @property
    def is_development(self) -> bool:
        """Проверка на development окружение."""
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        """Проверка на production окружение."""
        return self.environment == "production"

    @property
    def is_testing(self) -> bool:
        """Проверка на testing окружение."""
        return self.environment == "testing"

    @property
    def database_url_sync(self) -> str:
        """Синхронная версия DATABASE_URL для psycopg2."""
        # Преобразуем postgresql+asyncpg:// в postgresql://
        url_str = str(self.database_url)
        return url_str.replace("postgresql+asyncpg://", "postgresql://")

    @property
    def redis_url_sync(self) -> str:
        """Синхронная версия REDIS_URL."""
        return str(self.redis_url).replace("redis://", "redis://")


@lru_cache
def get_settings() -> Settings:
    """
    Возвращает кэшированный экземпляр настроек.
    Используется lru_cache для производительности.
    """
    return Settings()


# Глобальный экземпляр настроек
settings = get_settings()
