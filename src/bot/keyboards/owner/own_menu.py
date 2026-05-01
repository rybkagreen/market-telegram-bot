"""Owner menu keyboard."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def own_menu_kb(
    pending_count: int = 0,
    *,
    payout_url: str | None = None,
) -> InlineKeyboardMarkup:
    """Меню владельца.

    ``payout_url`` is the pre-minted portal-login URL (BL-055). Caller
    awaits ``build_portal_deeplink`` once and feeds the result here.
    Falsy → the payout button is omitted (surface failures softly so
    the rest of the menu still renders).
    """
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📊 Статистика", callback_data="main:owner_analytics"))
    builder.row(InlineKeyboardButton(text="📺 Мои каналы", callback_data="main:my_channels"))

    badge = f" 🔴{pending_count}" if pending_count > 0 else ""
    builder.row(InlineKeyboardButton(text=f"📋 Заявки{badge}", callback_data="main:my_requests"))

    if payout_url:
        builder.row(InlineKeyboardButton(text="💸 Выплаты", url=payout_url))
    builder.row(InlineKeyboardButton(text="🔙 Главное меню", callback_data="main:main_menu"))
    return builder.as_markup()
