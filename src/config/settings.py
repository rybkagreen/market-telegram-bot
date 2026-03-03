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
    nginx_port: int = Field(8081, alias="NGINX_PORT")

    # Environment
    environment: Literal["development", "production", "testing"] = Field(
        "development", alias="ENVIRONMENT"
    )
    debug: bool = Field(False, alias="DEBUG")

    # ══════════════════════════════════════════════════════════════
    # OpenRouter — единственный AI провайдер
    # Получить ключ: https://openrouter.ai/keys
    # ══════════════════════════════════════════════════════════════
    openrouter_api_key: str | None = Field(None, alias="OPENROUTER_API_KEY")

    # ══════════════════════════════════════════════════════════════
    # JWT для Mini App аутентификации
    # Генерировать: python -c "import secrets; print(secrets.token_hex(32))"
    # ══════════════════════════════════════════════════════════════
    jwt_secret: str = Field(..., alias="JWT_SECRET", description="Секрет для подписи JWT токенов Mini App")
    jwt_algorithm: str = Field("HS256", alias="JWT_ALGORITHM", description="Алгоритм подписи JWT")
    jwt_expire_hours: int = Field(24, alias="JWT_EXPIRE_HOURS", description="Время жизни JWT токена (часы)")

    # Модели (менять не рекомендуется — они привязаны к тарифам)
    # FREE/STARTER → NousResearch Hermes 3 Llama 3.1 405B (бесплатная)
    # При rate limit fallback: stepfun/step-3.5-flash:free (всегда доступна)
    model_free: str = Field("nousresearch/hermes-3-llama-3.1-405b:free", alias="MODEL_FREE")
    model_free_fallback: str = Field("stepfun/step-3.5-flash:free", alias="MODEL_FREE_FALLBACK")
    # PRO/BUSINESS → Claude Sonnet 4.6
    model_paid: str = Field("anthropic/claude-sonnet-4-6", alias="MODEL_PAID")

    # Параметры генерации
    ai_timeout: int = Field(60, alias="AI_TIMEOUT")
    ai_max_tokens: int = Field(1500, alias="AI_MAX_TOKENS")
    ai_temperature: float = Field(0.7, alias="AI_TEMPERATURE")

    # ========== CREDIT SYSTEM ==========
    # CryptoBot
    cryptobot_token: str | None = Field(None, alias="CRYPTOBOT_TOKEN")
    stars_enabled: bool = Field(True, alias="STARS_ENABLED")

    # Credit rates (кредитов за 1 единицу валюты)
    credits_per_usdt: int = Field(90, alias="CREDITS_PER_USDT")
    credits_per_ton: int = Field(400, alias="CREDITS_PER_TON")
    credits_per_btc: int = Field(9_000_000, alias="CREDITS_PER_BTC")
    credits_per_eth: int = Field(300_000, alias="CREDITS_PER_ETH")
    credits_per_ltc: int = Field(7_000, alias="CREDITS_PER_LTC")
    credits_per_star: int = Field(2, alias="CREDITS_PER_STAR")

    # Package bonuses
    bonus_credits_standard: int = Field(100, alias="BONUS_CREDITS_STANDARD")
    bonus_credits_business: int = Field(500, alias="BONUS_CREDITS_BUSINESS")

    # Plan renewal
    plan_renewal_check_hour: int = Field(3, alias="PLAN_RENEWAL_CHECK_HOUR")

    # Payments (legacy)
    yookassa_shop_id: str | None = Field(None, alias="YOOKASSA_SHOP_ID")
    yookassa_secret_key: str | None = Field(None, alias="YOOKASSA_SECRET_KEY")

    # Mailing rate limits
    mailing_max_per_minute: int = Field(10, alias="MAILING_MAX_PER_MINUTE")
    mailing_max_per_hour: int = Field(300, alias="MAILING_MAX_PER_HOUR")
    mailing_max_per_day: int = Field(2000, alias="MAILING_MAX_PER_DAY")
    mailing_flood_wait_threshold: int = Field(300, alias="MAILING_FLOOD_WAIT_THRESHOLD")

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

    @property
    def currency_rates(self) -> dict[str, int]:
        """Словарь курсов конвертации валют в кредиты."""
        return {
            "USDT": self.credits_per_usdt,
            "TON": self.credits_per_ton,
            "BTC": self.credits_per_btc,
            "ETH": self.credits_per_eth,
            "LTC": self.credits_per_ltc,
            "XUSDT": self.credits_per_usdt,  # alias для Stars
        }

    @property
    def mailing_settings(self) -> dict:
        """Настройки лимитов рассылок."""
        return {
            "max_per_minute": self.mailing_max_per_minute,
            "max_per_hour": self.mailing_max_per_hour,
            "max_per_day": self.mailing_max_per_day,
            "flood_wait_threshold": self.mailing_flood_wait_threshold,
        }

    @property
    def openrouter_base_url(self) -> str:
        """Базовый URL для OpenRouter API."""
        return "https://openrouter.ai/api/v1"

    def get_model_for_plan(self, plan: str) -> str:
        """
        Вернуть модель OpenRouter для указанного тарифа.

        FREE/STARTER/ADMIN → бесплатная модель
        PRO/BUSINESS → платная модель

        Args:
            plan: Название тарифа (free, starter, pro, business, admin).

        Returns:
            ID модели в формате OpenRouter.
        """
        # ADMIN тариф использует бесплатную модель
        paid_plans = {"pro", "business"}
        plan_value = plan.lower() if isinstance(plan, str) else plan.value.lower()

        if plan_value in paid_plans:
            return self.model_paid
        return self.model_free  # free, starter, admin


@lru_cache
def get_settings() -> Settings:
    """
    Возвращает кэшированный экземпляр настроек.
    Используется lru_cache для производительности.
    """
    return Settings()


# Глобальный экземпляр настроек
settings = get_settings()
