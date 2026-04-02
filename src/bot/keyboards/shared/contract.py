"""Contract keyboards."""

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def contract_sign_keyboard(contract_id: int) -> InlineKeyboardMarkup:
    """Клавиатура просмотра и подписания договора."""
    builder = InlineKeyboardBuilder()
    builder.button(text="📄 Посмотреть договор", callback_data=f"contract:view:{contract_id}")
    builder.button(text="✍️ Подписать", callback_data=f"contract:sign:{contract_id}")
    builder.adjust(1)
    return builder.as_markup()


def accept_rules_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура принятия правил платформы."""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Принимаю правила и политику", callback_data="contract:accept_rules")
    builder.adjust(1)
    return builder.as_markup()
