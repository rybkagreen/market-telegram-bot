"""
Константы платёжной системы RekHarborBot.

Fee/percentage rates (placement commission, owner share, YooKassa fee,
service fee, cancel splits, NPD/USN tax rates) live in
`src.constants.fees` — single source of truth, enforced by AST lint
`tests/unit/test_no_hardcoded_fees.py`.

This module keeps non-fee operational constants:
- velocity checks, cooldowns
- minimum amounts (topup, budget, payout)
- referral bonus
- format multipliers, plan prices and limits
- payout-flow fee + helpers (вывод средств — separate from placement fees)
"""

from decimal import Decimal

# ══════════════════════════════════════════════════════════════
# PAYOUT FEE — комиссия за вывод средств с баланса owner на банк
# ══════════════════════════════════════════════════════════════
# 1.5% — фиксированная стоимость обработки вывода. Концептуально
# не относится к placement-flow fees (никак не связана с публикацией);
# взимается только при initiated payout request.
PAYOUT_FEE_RATE = Decimal("0.015")

# ══════════════════════════════════════════════════════════════
# VELOCITY CHECK — защита от обналичивания
# ══════════════════════════════════════════════════════════════
VELOCITY_MAX_RATIO = Decimal("0.80")  # Макс. соотношение вывод/пополнения
VELOCITY_WINDOW_DAYS = 30  # Период расчёта velocity (дней)
COOLDOWN_HOURS = 24  # Мин. интервал между выводами

# ══════════════════════════════════════════════════════════════
# МИНИМАЛЬНЫЕ СУММЫ (в рублях)
# ══════════════════════════════════════════════════════════════
MIN_TOPUP = Decimal("500")  # Минимальное пополнение
MAX_TOPUP = Decimal("300000")  # Максимальное пополнение
MIN_CAMPAIGN_BUDGET = Decimal("2000")  # Минимальный бюджет кампании
MIN_PRICE_PER_POST = Decimal("1000")  # Минимальная цена за пост
MIN_PAYOUT = Decimal("1000")  # Минимальная выплата владельцу

# ══════════════════════════════════════════════════════════════
# РЕФЕРАЛЬНАЯ ПРОГРАММА — выплата при первом пополнении
# ══════════════════════════════════════════════════════════════
REFERRAL_MIN_QUALIFYING_TOPUP = Decimal("500")  # Мин. пополнение для выплаты рефереру
REFERRAL_BONUS_PERCENT = Decimal("0.10")  # 10% от суммы пополнения

# ══════════════════════════════════════════════════════════════
# БЫСТРОЕ ПОПОЛНЕНИЕ (ЮKassa)
# ══════════════════════════════════════════════════════════════
QUICK_TOPUP_AMOUNTS: list[int] = [500, 1000, 2000, 5000, 10000, 20000]

# ══════════════════════════════════════════════════════════════
# ФОРМАТЫ ПУБЛИКАЦИЙ — коэффициенты цены
# ══════════════════════════════════════════════════════════════
FORMAT_MULTIPLIERS: dict[str, Decimal] = {
    "post_24h": Decimal("1.0"),  # Обычный пост на 24 часа (база)
    "post_48h": Decimal("1.4"),  # Обычный пост на 48 часов (+40%)
    "post_7d": Decimal("2.0"),  # Обычный пост на 7 дней (+100%)
    "pin_24h": Decimal("3.0"),  # Закреплённый пост на 24 часа (+200%)
    "pin_48h": Decimal("4.0"),  # Закреплённый пост на 48 часов (+300%)
}

FORMAT_DURATIONS_SECONDS: dict[str, int] = {
    "post_24h": 86400,  # 24 часа
    "post_48h": 172800,  # 48 часов
    "post_7d": 604800,  # 7 дней
    "pin_24h": 86400,  # 24 часа
    "pin_48h": 172800,  # 48 часов
}

# ══════════════════════════════════════════════════════════════
# ТАРИФНЫЕ ПЛАНЫ — стоимость и лимиты
# ══════════════════════════════════════════════════════════════
PLAN_PRICES: dict[str, Decimal] = {
    "free": Decimal("0"),  # Бесплатный
    "starter": Decimal("490"),  # Стартовый
    "pro": Decimal("1490"),  # Профессиональный
    "business": Decimal("4990"),  # Агентский (UserPlan.business)
}

PLAN_LIMITS: dict[str, dict] = {
    "free": {
        "active_campaigns": 1,
        "ai_per_month": 0,
        "formats": ["post_24h"],
    },
    "starter": {
        "active_campaigns": 5,
        "ai_per_month": 3,
        "formats": ["post_24h", "post_48h"],
    },
    "pro": {
        "active_campaigns": 20,
        "ai_per_month": 20,
        "formats": ["post_24h", "post_48h", "post_7d"],
    },
    "business": {
        "active_campaigns": -1,  # Безлимит
        "ai_per_month": -1,  # Безлимит
        "formats": ["post_24h", "post_48h", "post_7d", "pin_24h", "pin_48h"],
    },
}


# ══════════════════════════════════════════════════════════════
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ══════════════════════════════════════════════════════════════
def calculate_topup_payment(desired: Decimal) -> dict:
    """
    Рассчитать сумму пополнения с комиссией ЮKassa.

    Args:
        desired: Желаемая сумма к зачислению (desired_balance).

    Returns:
        dict с ключами:
            - desired_balance: сумма к зачислению на баланс
            - fee_amount: комиссия ЮKassa (3.5%)
            - gross_amount: итоговая сумма к оплате
    """
    from src.constants.fees import YOOKASSA_FEE_RATE

    desired = Decimal(str(desired))
    fee_amount = (desired * YOOKASSA_FEE_RATE).quantize(Decimal("0.01"))
    gross_amount = desired + fee_amount
    return {
        "desired_balance": desired,
        "fee_amount": fee_amount,
        "gross_amount": gross_amount,
    }


def calculate_payout(gross: Decimal) -> dict:
    """
    Рассчитать выплату с комиссией платформы.

    Args:
        gross: Сумма запроса на выплату.

    Returns:
        dict с ключами:
            - gross: запрошенная сумма
            - fee: комиссия платформы (1.5%)
            - net: сумма к перечислению
    """
    gross = Decimal(str(gross))
    fee = (gross * PAYOUT_FEE_RATE).quantize(Decimal("0.01"))
    net = gross - fee
    return {
        "gross": gross,
        "fee": fee,
        "net": net,
    }


def get_format_price(base_price: Decimal, fmt: str) -> Decimal:
    """
    Рассчитать цену публикации с учётом формата.

    Args:
        base_price: Базовая цена за пост (price_per_post из канала).
        fmt: Формат публикации (post_24h, pin_48h, etc).

    Returns:
        Итоговая цена с учётом мультипликатора формата.
    """
    base_price = Decimal(str(base_price))
    multiplier = FORMAT_MULTIPLIERS.get(fmt, Decimal("1.0"))
    return (base_price * multiplier).quantize(Decimal("0.01"))


def is_format_allowed_for_plan(plan: str, fmt: str) -> bool:
    """
    Проверить доступность формата для тарифа.

    Args:
        plan: Название тарифа (free, starter, pro, business).
        fmt: Формат публикации.

    Returns:
        True если формат доступен для тарифа.
    """
    plan_limits = PLAN_LIMITS.get(plan, {})
    allowed_formats = plan_limits.get("formats", [])
    return fmt in allowed_formats
