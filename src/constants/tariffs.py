"""
Константы тарифной системы Market Bot.

Спринт 4: Перенесено в src/config/settings.py.
Этот файл — thin wrapper для обратной совместимости.
Будет удалён в следующем спринте.
"""

from src.config.settings import settings

# ══════════════════════════════════════════════════════════════
# ОТОБРАЖЕНИЕ ТАРИФОВ (v4.2)
# ══════════════════════════════════════════════════════════════
PLAN_DISPLAY_NAMES: dict[str, str] = {
    "free": "Free",
    "starter": "Starter",
    "pro": "Pro",
    "business": "Agency",  # UserPlan.business = "business", display name = "Agency"
}

PLAN_EMOJIS: dict[str, str] = {
    "free": "🆓",
    "starter": "🚀",
    "pro": "💎",
    "business": "🏢",
}

# Ограничения по подписчикам для каждого тарифа
TARIFF_SUBSCRIBER_LIMITS: dict[str, int] = {
    "free": settings.tariff_subscriber_limits_free,
    "starter": settings.tariff_subscriber_limits_starter,
    "pro": settings.tariff_subscriber_limits_pro,
    "business": settings.tariff_subscriber_limits_business,
    "admin": settings.tariff_subscriber_limits_admin,
}

# Минимальный рейтинг канала для тарифа
TARIFF_MIN_RATING: dict[str, float] = {
    "free": settings.tariff_min_rating_free,
    "starter": settings.tariff_min_rating_starter,
    "pro": settings.tariff_min_rating_pro,
    "business": settings.tariff_min_rating_business,
    "admin": settings.tariff_min_rating_admin,
}

# Доступные топики для каждого тарифа
TARIFF_TOPICS: dict[str, list[str] | None] = {
    "free": ["бизнес", "маркетинг"],
    "starter": ["бизнес", "маркетинг", "it", "финансы", "крипто"],
    "pro": None,
    "business": None,
    "admin": None,
}

# Порог "premium" каналов
PREMIUM_SUBSCRIBER_THRESHOLD = settings.premium_subscriber_threshold

TARIFF_LABELS: dict[str, str] = {
    "free": "FREE",
    "starter": "STARTER",
    "pro": "PRO",
    "business": "BUSINESS",
    "admin": "ADMIN",
}

# Лимиты кампаний в месяц по тарифам
TARIFF_CAMPAIGN_LIMITS: dict[str, int] = {
    "free": settings.tariff_campaign_limits_free,
    "starter": settings.tariff_campaign_limits_starter,
    "pro": settings.tariff_campaign_limits_pro,
    "business": settings.tariff_campaign_limits_business,
    "admin": settings.tariff_campaign_limits_admin,
}

# Лимиты чатов на кампанию по тарифам
TARIFF_CHAT_LIMITS: dict[str, int] = {
    "free": settings.tariff_chat_limits_free,
    "starter": settings.tariff_chat_limits_starter,
    "pro": settings.tariff_chat_limits_pro,
    "business": settings.tariff_chat_limits_business,
    "admin": settings.tariff_chat_limits_admin,
}

# Лимиты ИИ-генераций в месяц по тарифам
TARIFF_AI_LIMITS: dict[str, int] = {
    "free": settings.tariff_ai_limits_free,
    "starter": settings.tariff_ai_limits_starter,
    "pro": settings.tariff_ai_limits_pro,
    "business": settings.tariff_ai_limits_business,
    "admin": settings.tariff_ai_limits_admin,
}
