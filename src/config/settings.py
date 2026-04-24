"""
Настройки приложения через Pydantic Settings.
Читает переменные окружения из .env файла.
"""

from functools import lru_cache

from pydantic import Field, PostgresDsn, RedisDsn, field_validator
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

    # Telegram Proxy (SOCKS5/HTTP proxy для обхода ограничений)
    telegram_proxy: str | None = Field(
        None,
        alias="TELEGRAM_PROXY",
        description=(
            "Proxy for Telegram API. Accepted schemes: socks5://, http://, https://. "
            "Examples: socks5://host:1080, http://user:pass@host:3128."
        ),
    )

    @field_validator("telegram_proxy")
    @classmethod
    def _validate_telegram_proxy(cls, value: str | None) -> str | None:
        if value is None or value == "":
            return None
        allowed = ("socks5://", "socks4://", "http://", "https://")
        if not value.startswith(allowed):
            raise ValueError(
                f"TELEGRAM_PROXY must start with one of {allowed}, got {value!r}"
            )
        return value

    # PostgreSQL
    postgres_user: str = Field("market_bot", alias="POSTGRES_USER")
    postgres_password: str = Field("market_bot_pass", alias="POSTGRES_PASSWORD")
    postgres_db: str = Field("market_bot_db", alias="POSTGRES_DB")
    postgres_port: int = Field(5432, alias="POSTGRES_PORT")
    database_url: PostgresDsn = Field(..., alias="DATABASE_URL")
    test_database_url: PostgresDsn | None = Field(default=None, alias="TEST_DATABASE_URL")

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
    debug: bool = Field(False, alias="DEBUG")

    # E2E-only auth endpoint flag (mounts /api/auth/e2e-login when True).
    # Replaces the old ENVIRONMENT=="testing" check — feature-flag, not env-label.
    enable_e2e_auth: bool = Field(False, alias="ENABLE_E2E_AUTH")

    # ══════════════════════════════════════════════════════════════
    # Mistral AI — единственный AI провайдер (официальный SDK)
    # Получить ключ: https://console.mistral.ai/api-keys
    # Модель: mistral-medium-latest (баланс качества и скорости)
    # ══════════════════════════════════════════════════════════════
    mistral_api_key: str | None = Field(None, alias="MISTRAL_API_KEY")
    ai_model: str = Field("mistral-medium-latest", alias="AI_MODEL")

    # ══════════════════════════════════════════════════════════════
    # FIELD-LEVEL ENCRYPTION (S6A)
    # FIELD_ENCRYPTION_KEY — Fernet:
    #   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    # SEARCH_HASH_KEY — random 32-byte hex:
    #   python -c "import secrets; print(secrets.token_hex(32))"
    # ══════════════════════════════════════════════════════════════
    field_encryption_key: str = Field(
        ...,
        alias="FIELD_ENCRYPTION_KEY",
        description="Fernet key for field-level encryption of PII columns",
    )
    search_hash_key: str = Field(
        ...,
        alias="SEARCH_HASH_KEY",
        description="HMAC-SHA256 key for searchable hash of INN (hex string)",
    )

    # ══════════════════════════════════════════════════════════════
    # JWT для Mini App аутентификации
    # Генерировать: python -c "import secrets; print(secrets.token_hex(32))"
    # ══════════════════════════════════════════════════════════════
    jwt_secret: str = Field(
        ..., alias="JWT_SECRET", description="Секрет для подписи JWT токенов Mini App"
    )
    jwt_algorithm: str = Field("HS256", alias="JWT_ALGORITHM", description="Алгоритм подписи JWT")
    jwt_expire_hours: int = Field(
        24, alias="JWT_EXPIRE_HOURS", description="Время жизни JWT токена (часы)"
    )

    # S9: Persistent storage for generated PDF contracts
    contracts_storage_path: str = Field(
        "/data/contracts",
        alias="CONTRACTS_STORAGE_PATH",
        description="Persistent volume path for generated PDF contracts",
    )

    # Параметры генерации
    ai_timeout: int = Field(60, alias="AI_TIMEOUT")
    ai_max_tokens: int = Field(1500, alias="AI_MAX_TOKENS")
    ai_temperature: float = Field(0.7, alias="AI_TEMPERATURE")

    # ═══════════════════════════════════════════════════════════════
    # PAYMENT SYSTEM v4.2 — ТОЛЬКО ЮKassa (RUB)
    # ═══════════════════════════════════════════════════════════════
    # ЮKassa
    yookassa_shop_id: str = Field("", alias="YOOKASSA_SHOP_ID")
    yookassa_secret_key: str = Field("", alias="YOOKASSA_SECRET_KEY")
    yookassa_return_url: str = Field("https://t.me/YOUR_BOT", alias="YOOKASSA_RETURN_URL")
    yookassa_webhook_path: str = Field("/webhooks/yookassa", alias="YOOKASSA_WEBHOOK_PATH")

    # ═══════════════════════════════════════════════════════════════
    # КУРСЫ КРИПТОВАЛЮТ → РУБЛИ (для пополнения balance_rub)
    # ═══════════════════════════════════════════════════════════════
    rub_per_usdt: int = Field(90, alias="RUB_PER_USDT")
    rub_per_ton: int = Field(400, alias="RUB_PER_TON")
    rub_per_btc: int = Field(9_000_000, alias="RUB_PER_BTC")
    rub_per_eth: int = Field(300_000, alias="RUB_PER_ETH")
    rub_per_ltc: int = Field(7_000, alias="RUB_PER_LTC")

    # ═══════════════════════════════════════════════════════════════
    # Payout settings (v4.2)
    min_payout_rub: float = Field(
        1000.0, alias="MIN_PAYOUT_RUB", description="Минимальная сумма выплаты в рублях"
    )

    # Content Filter settings
    content_filter_l3_enabled: bool = Field(
        True, alias="CONTENT_FILTER_L3_ENABLED", description="Включить L3 (LLM) проверку контента"
    )
    content_filter_l3_timeout: float = Field(
        3.0, alias="CONTENT_FILTER_L3_TIMEOUT", description="Таймаут L3 проверки в секундах"
    )

    # ══════════════════════════════════════════════════════════════
    # GitHub Integration
    # ══════════════════════════════════════════════════════════════
    github_token: str | None = Field(None, alias="GITHUB_TOKEN", description="GitHub PAT токен")
    github_repo_owner: str = Field("", alias="GITHUB_REPO_OWNER", description="GitHub репо владелец")
    github_repo_name: str = Field("", alias="GITHUB_REPO_NAME", description="GitHub репо название")

    # ══════════════════════════════════════════════════════════════
    # V4.3 — Диспуты и мониторинг постов
    # ══════════════════════════════════════════════════════════════
    dispute_check_interval_minutes: int = Field(
        5, alias="DISPUTE_CHECK_INTERVAL_MINUTES", description="Интервал проверки диспутов (мин)"
    )
    post_monitoring_min_life_ratio: float = Field(
        0.80,
        alias="POST_MONITORING_MIN_LIFE_RATIO",
        description="Мин. доля жизни поста для авто-диспута (0.80 = 80%)",
    )

    # Analytics settings
    analytics_estimated_cpm_rub: float = Field(
        100.0,
        alias="ANALYTICS_ESTIMATED_CPM_RUB",
        description="Оценочный CPM (руб за 1000 просмотров)",
    )
    analytics_estimated_cpc_rub: float = Field(
        25.0, alias="ANALYTICS_ESTIMATED_CPC_RUB", description="Оценочный CPC (руб за клик)"
    )

    # ═══════════════════════════════════════════════════════════════
    # Тарифные планы (Спринт 4 — перенесено из api/constants/tariffs.py)
    # ═══════════════════════════════════════════════════════════════
    # Ограничения по подписчикам
    tariff_subscriber_limits_free: int = Field(10_000, alias="TARIFF_SUBSCRIBER_LIMIT_FREE")
    tariff_subscriber_limits_starter: int = Field(50_000, alias="TARIFF_SUBSCRIBER_LIMIT_STARTER")
    tariff_subscriber_limits_pro: int = Field(200_000, alias="TARIFF_SUBSCRIBER_LIMIT_PRO")
    tariff_subscriber_limits_business: int = Field(-1, alias="TARIFF_SUBSCRIBER_LIMIT_BUSINESS")
    tariff_subscriber_limits_admin: int = Field(-1, alias="TARIFF_SUBSCRIBER_LIMIT_ADMIN")

    # Минимальный рейтинг канала
    tariff_min_rating_free: float = Field(0.0, alias="TARIFF_MIN_RATING_FREE")
    tariff_min_rating_starter: float = Field(5.0, alias="TARIFF_MIN_RATING_STARTER")
    tariff_min_rating_pro: float = Field(7.0, alias="TARIFF_MIN_RATING_PRO")
    tariff_min_rating_business: float = Field(0.0, alias="TARIFF_MIN_RATING_BUSINESS")
    tariff_min_rating_admin: float = Field(0.0, alias="TARIFF_MIN_RATING_ADMIN")

    # Стоимость тарифов в кредитах (v4.2)
    tariff_cost_free: int = Field(0, alias="TARIFF_COST_FREE")
    tariff_cost_starter: int = Field(490, alias="TARIFF_COST_STARTER")
    tariff_cost_pro: int = Field(1490, alias="TARIFF_COST_PRO")
    tariff_cost_business: int = Field(4990, alias="TARIFF_COST_BUSINESS")
    tariff_cost_admin: int = Field(0, alias="TARIFF_COST_ADMIN")

    # Лимиты кампаний в месяц
    tariff_campaign_limits_free: int = Field(0, alias="TARIFF_CAMPAIGN_LIMIT_FREE")
    tariff_campaign_limits_starter: int = Field(5, alias="TARIFF_CAMPAIGN_LIMIT_STARTER")
    tariff_campaign_limits_pro: int = Field(20, alias="TARIFF_CAMPAIGN_LIMIT_PRO")
    tariff_campaign_limits_business: int = Field(100, alias="TARIFF_CAMPAIGN_LIMIT_BUSINESS")
    tariff_campaign_limits_admin: int = Field(-1, alias="TARIFF_CAMPAIGN_LIMIT_ADMIN")

    # Лимиты чатов на кампанию
    tariff_chat_limits_free: int = Field(0, alias="TARIFF_CHAT_LIMIT_FREE")
    tariff_chat_limits_starter: int = Field(50, alias="TARIFF_CHAT_LIMIT_STARTER")
    tariff_chat_limits_pro: int = Field(200, alias="TARIFF_CHAT_LIMIT_PRO")
    tariff_chat_limits_business: int = Field(1000, alias="TARIFF_CHAT_LIMIT_BUSINESS")
    tariff_chat_limits_admin: int = Field(10000, alias="TARIFF_CHAT_LIMIT_ADMIN")

    # Лимиты ИИ-генераций в месяц
    tariff_ai_limits_free: int = Field(0, alias="TARIFF_AI_LIMIT_FREE")
    tariff_ai_limits_starter: int = Field(0, alias="TARIFF_AI_LIMIT_STARTER")
    tariff_ai_limits_pro: int = Field(5, alias="TARIFF_AI_LIMIT_PRO")
    tariff_ai_limits_business: int = Field(20, alias="TARIFF_AI_LIMIT_BUSINESS")
    tariff_ai_limits_admin: int = Field(-1, alias="TARIFF_AI_LIMIT_ADMIN")

    # Порог premium каналов
    premium_subscriber_threshold: int = Field(
        1_000_000,
        alias="PREMIUM_SUBSCRIBER_THRESHOLD",
        description="Порог premium каналов (подписчиков)",
    )

    # Package bonuses
    bonus_credits_standard: int = Field(100, alias="BONUS_CREDITS_STANDARD")
    bonus_credits_business: int = Field(500, alias="BONUS_CREDITS_BUSINESS")

    # Plan renewal
    plan_renewal_check_hour: int = Field(3, alias="PLAN_RENEWAL_CHECK_HOUR")

    # Mailing rate limits
    mailing_max_per_minute: int = Field(10, alias="MAILING_MAX_PER_MINUTE")
    mailing_max_per_hour: int = Field(300, alias="MAILING_MAX_PER_HOUR")
    mailing_max_per_day: int = Field(2000, alias="MAILING_MAX_PER_DAY")
    mailing_flood_wait_threshold: int = Field(300, alias="MAILING_FLOOD_WAIT_THRESHOLD")

    # ═══════════════════════════════════════════════════════════════
    # ORD (Operator of Advertising Data) — маркировка рекламы
    # ═══════════════════════════════════════════════════════════════
    ord_provider: str = Field(
        "stub",
        alias="ORD_PROVIDER",
        description="ORD провайдер: 'stub' | 'yandex' | 'vk' | 'ozon'",
    )
    ord_api_key: str | None = Field(None, alias="ORD_API_KEY")
    ord_api_url: str | None = Field(None, alias="ORD_API_URL")
    ord_block_publication_without_erid: bool = Field(
        False,
        alias="ORD_BLOCK_WITHOUT_ERID",
        description="Блокировать публикацию без erid (включить после настройки провайдера)",
    )
    ord_rekharbor_org_id: str = Field(
        "",
        alias="ORD_REKHARBOR_ORG_ID",
        description="ID RekHarbor как организации в Яндекс ОРД (регистрируется вручную)",
    )
    ord_rekharbor_inn: str = Field(
        "",
        alias="ORD_REKHARBOR_INN",
        description="ИНН РекХарбора для регистрации org в Яндекс ОРД",
    )
    ord_default_kktu_code: str = Field(
        "30.10.1",
        alias="ORD_DEFAULT_KKTU_CODE",
        description="ККТУ код по умолчанию (30.10.1 — размещение рекламы)",
    )

    # Admin IDs
    admin_ids_raw: str = Field("", alias="ADMIN_IDS")

    # Webhook & Mini App
    webhook_url: str | None = Field(None, alias="WEBHOOK_URL")

    # Public URLs — single source of truth for frontend endpoints.
    # Do NOT hardcode rekharbor.ru anywhere in src/ or mini_app/src/.
    mini_app_url: str = Field("https://app.rekharbor.ru/", alias="MINI_APP_URL")
    web_portal_url: str = Field("https://rekharbor.ru/portal", alias="WEB_PORTAL_URL")
    landing_url: str = Field("https://rekharbor.ru", alias="LANDING_URL")
    api_public_url: str = Field("https://api.rekharbor.ru", alias="API_PUBLIC_URL")
    tracking_base_url: str = Field("https://rekharbor.ru/t", alias="TRACKING_BASE_URL")
    terms_url: str = Field("https://rekharbor.ru/terms", alias="TERMS_URL")

    # Mini_app → web_portal JWT bridge (Phase 0)
    ticket_jwt_ttl_seconds: int = Field(300, alias="TICKET_JWT_TTL_SECONDS")

    # Optional sandbox Telegram channel id for test-mode routing (Phase 5).
    sandbox_telegram_channel_id: int | None = Field(None, alias="SANDBOX_TELEGRAM_CHANNEL_ID")

    # Sentry / GlitchTip
    sentry_dsn: str | None = Field(None, alias="SENTRY_DSN")
    sentry_environment: str = Field("production", alias="SENTRY_ENVIRONMENT")
    sentry_traces_sample_rate: float = Field(0.1, alias="SENTRY_TRACES_SAMPLE_RATE")
    glitchtip_webhook_secret: str = Field("", alias="GLITCHTIP_WEBHOOK_SECRET")

    # Error report storage
    error_reports_dir: str = Field(
        "/opt/market-telegram-bot/reports/monitoring/error_reports",
        alias="ERROR_REPORTS_DIR",
    )
    error_reports_max_mb: int = Field(100, alias="ERROR_REPORTS_MAX_MB")
    dir_snapshot_dir: str = Field(
        "/opt/market-telegram-bot/reports/monitoring/dir_snapshot",
        alias="DIR_SNAPSHOT_DIR",
    )
    dir_snapshot_max_count: int = Field(10, alias="DIR_SNAPSHOT_MAX_COUNT")

    # Admin Telegram (error notifications)
    admin_telegram_id: int = Field(0, alias="ADMIN_TELEGRAM_ID")
    admin_telegram_bot_token: str = Field("", alias="ADMIN_TELEGRAM_BOT_TOKEN")

    @property
    def admin_ids(self) -> list[int]:
        """Парсит ADMIN_IDS из строки в список целых чисел."""
        if not self.admin_ids_raw:
            return []
        return [int(x.strip()) for x in self.admin_ids_raw.split(",") if x.strip().isdigit()]

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
        """Словарь курсов конвертации валют в рубли (для пополнения balance_rub)."""
        return {
            "USDT": self.rub_per_usdt,
            "TON": self.rub_per_ton,
            "BTC": self.rub_per_btc,
            "ETH": self.rub_per_eth,
            "LTC": self.rub_per_ltc,
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
    def ai_base_url(self) -> str:
        """Базовый URL для Mistral AI API."""
        return "https://api.mistral.ai/v1"

    def get_model_for_plan(self, plan: str) -> str:
        """
        Вернуть модель Mistral для указанного тарифа.
        Все тарифы используют единую модель из settings.ai_model.

        Args:
            plan: Название тарифа (free, starter, pro, business, admin).

        Returns:
            ID модели Mistral.
        """
        return self.ai_model


@lru_cache
def get_settings() -> Settings:
    """
    Возвращает кэшированный экземпляр настроек.
    Используется lru_cache для производительности.
    """
    return Settings()


# Глобальный экземпляр настроек
settings = get_settings()
