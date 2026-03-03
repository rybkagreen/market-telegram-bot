"""
Константы тарифной системы Market Bot.
Используются в channels, billing, analytics роутерах.

ВАЖНО: ADMIN тариф скрыт от обычных пользователей и доступен только через
прямое назначение в БД или через админ-панель.
"""

# Ограничения по подписчикам для каждого тарифа
# -1 = безлимит
TARIFF_SUBSCRIBER_LIMITS: dict[str, int] = {
    "free": 10_000,
    "starter": 50_000,
    "pro": 200_000,
    "business": -1,
    "admin": -1,  # ADMIN — безлимит
}

# Минимальный рейтинг канала для тарифа
# Поле: TelegramChat.rating (Float 0-10)
TARIFF_MIN_RATING: dict[str, float] = {
    "free": 0.0,
    "starter": 5.0,
    "pro": 7.0,
    "business": 0.0,
    "admin": 0.0,  # ADMIN — без ограничений
}

# Доступные топики для каждого тарифа
# None = все топики
# Значения берутся из реального поля TelegramChat.topic
TARIFF_TOPICS: dict[str, list[str] | None] = {
    "free": ["бизнес", "маркетинг"],
    "starter": ["бизнес", "маркетинг", "it", "финансы", "крипто"],
    "pro": None,  # все кроме premium (>1M)
    "business": None,  # все включая premium
    "admin": None,  # ADMIN — все топики включая premium
}

# Порог "premium" каналов — только для business
PREMIUM_SUBSCRIBER_THRESHOLD = 1_000_000

# Стоимость тарифов в кредитах (уже реализовано в billing.py)
# ADMIN тариф недоступен для покупки — только через админ-панель
TARIFF_CREDIT_COST: dict[str, int] = {
    "free": 0,
    "starter": 299,
    "pro": 999,
    "business": 2999,
    "admin": 0,  # ADMIN — бесплатно (недоступен для покупки)
}

TARIFF_LABELS: dict[str, str] = {
    "free": "FREE",
    "starter": "STARTER",
    "pro": "PRO",
    "business": "BUSINESS",
    "admin": "ADMIN",  # Скрыт от обычных пользователей
}

# Лимиты кампаний в месяц по тарифам
TARIFF_CAMPAIGN_LIMITS: dict[str, int] = {
    "free": 0,
    "starter": 5,
    "pro": 20,
    "business": 100,
    "admin": -1,  # ADMIN — безлимит
}

# Лимиты чатов на кампанию по тарифам
TARIFF_CHAT_LIMITS: dict[str, int] = {
    "free": 0,
    "starter": 50,
    "pro": 200,
    "business": 1000,
    "admin": 10000,  # ADMIN — 10K чатов на кампанию
}

# Лимиты ИИ-генераций в месяц по тарифам
TARIFF_AI_LIMITS: dict[str, int] = {
    "free": 0,
    "starter": 0,
    "pro": 5,
    "business": 20,
    "admin": -1,  # ADMIN — безлимит
}
