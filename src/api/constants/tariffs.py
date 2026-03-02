"""
Константы тарифной системы Market Bot.
Используются в channels, billing, analytics роутерах.
"""

# Ограничения по подписчикам для каждого тарифа
# -1 = безлимит
TARIFF_SUBSCRIBER_LIMITS: dict[str, int] = {
    "free":     10_000,
    "starter":  50_000,
    "pro":      200_000,
    "business": -1,
}

# Минимальный рейтинг канала для тарифа
# Поле: TelegramChat.rating (Float 0-10)
TARIFF_MIN_RATING: dict[str, float] = {
    "free":     0.0,
    "starter":  5.0,
    "pro":      7.0,
    "business": 0.0,
}

# Доступные топики для каждого тарифа
# None = все топики
# Значения берутся из реального поля TelegramChat.topic
TARIFF_TOPICS: dict[str, list[str] | None] = {
    "free":     ["бизнес", "маркетинг"],
    "starter":  ["бизнес", "маркетинг", "it", "финансы", "крипто"],
    "pro":      None,       # все кроме premium (>1M)
    "business": None,       # все включая premium
}

# Порог "premium" каналов — только для business
PREMIUM_SUBSCRIBER_THRESHOLD = 1_000_000

# Стоимость тарифов в кредитах (уже реализовано в billing.py)
TARIFF_CREDIT_COST: dict[str, int] = {
    "free":     0,
    "starter":  299,
    "pro":      999,
    "business": 2999,
}

TARIFF_LABELS: dict[str, str] = {
    "free":     "FREE",
    "starter":  "STARTER",
    "pro":      "PRO",
    "business": "BUSINESS",
}
