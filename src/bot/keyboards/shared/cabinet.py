"""Cabinet keyboard."""

from decimal import Decimal

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def cabinet_kb(
    earned_rub: Decimal,
    *,
    payout_url: str | None = None,
    topup_url: str | None = None,
) -> InlineKeyboardMarkup:
    """Клавиатура кабинета — без role gating.

    ``payout_url`` and ``topup_url`` are pre-minted portal-login URLs
    (BL-055 / T1.2.5f). Each button appears only when its URL was minted —
    a falsy URL silently hides the button so the rest of the cabinet still
    renders even if the API is briefly unreachable.
    """
    builder = InlineKeyboardBuilder()

    if topup_url:
        builder.row(InlineKeyboardButton(text="💳 Пополнить баланс", url=topup_url))

    if earned_rub >= Decimal("1000") and payout_url:
        builder.row(InlineKeyboardButton(text="💸 Запросить вывод", url=payout_url))

    builder.row(InlineKeyboardButton(text="⭐ Изменить тариф", callback_data="billing:plans"))
    builder.row(
        InlineKeyboardButton(text="🎁 Реферальная программа", callback_data="cabinet:referral")
    )
    builder.row(InlineKeyboardButton(text="🏆 Геймификация", callback_data="cabinet:gamification"))
    builder.row(InlineKeyboardButton(text="🔙 Главное меню", callback_data="main:main_menu"))

    return builder.as_markup()


def referral_kb() -> InlineKeyboardMarkup:
    """Клавиатура реферальной программы."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📋 Скопировать ссылку", callback_data="cabinet:referral:copy")
    )
    builder.row(InlineKeyboardButton(text="🔙 Кабинет", callback_data="main:cabinet"))
    return builder.as_markup()


def gamification_kb() -> InlineKeyboardMarkup:
    """Клавиатура геймификации."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 Кабинет", callback_data="main:cabinet"))
    return builder.as_markup()
