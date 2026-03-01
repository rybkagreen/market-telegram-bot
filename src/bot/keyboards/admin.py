"""
Клавиатуры для админ-панели.
"""

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.db.models.user import User


class AdminCB(CallbackData, prefix="admin"):
    """CallbackData для админ-панели."""

    action: str
    value: str = ""


def get_admin_main_kb() -> InlineKeyboardMarkup:
    """
    Главное меню администратора.

    Returns:
        InlineKeyboardMarkup с кнопками разделов админки.
    """
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Статистика", callback_data=AdminCB(action="stats"))
    builder.button(text="👥 Пользователи", callback_data=AdminCB(action="users"))
    builder.button(text="🤖 ИИ-генерация", callback_data=AdminCB(action="ai_generate"))
    builder.button(text="📣 Кампания без оплаты", callback_data=AdminCB(action="free_campaign"))
    builder.button(text="💰 Баланс пользователя", callback_data=AdminCB(action="balance_manage"))
    builder.button(text="🚫 Бан пользователя", callback_data=AdminCB(action="ban_user"))
    builder.button(text="📢 Broadcast", callback_data=AdminCB(action="broadcast"))
    builder.button(text="🔙 В меню", callback_data=AdminCB(action="back_to_main"))
    builder.adjust(2, 2, 2, 1)
    return builder.as_markup()


def get_admin_confirm_kb(action: str, value: str = "") -> InlineKeyboardMarkup:
    """
    Подтверждение опасного действия.

    Args:
        action: Действие для подтверждения.
        value: Значение (опционально).

    Returns:
        InlineKeyboardMarkup с кнопками подтвердить/отмена.
    """
    builder = InlineKeyboardBuilder()
    builder.button(
        text="✅ Подтвердить", callback_data=AdminCB(action=f"{action}_confirm", value=value)
    )
    builder.button(text="❌ Отмена", callback_data=AdminCB(action="cancel"))
    builder.adjust(2)
    return builder.as_markup()


def get_users_list_kb(
    users: list[User],
    page: int,
    total_pages: int,
) -> InlineKeyboardMarkup:
    """
    Список пользователей с пагинацией.

    Args:
        users: Список пользователей.
        page: Текущая страница.
        total_pages: Всего страниц.

    Returns:
        InlineKeyboardMarkup со списком пользователей.
    """
    builder = InlineKeyboardBuilder()
    for user in users:
        ban_emoji = "🚫 " if user.is_banned else ""
        username = f"@{user.username}" if user.username else f"ID:{user.telegram_id}"
        builder.button(
            text=f"{ban_emoji}{username}",
            callback_data=AdminCB(action="user_detail", value=str(user.id)),
        )
    builder.adjust(1)

    # Пагинация
    if page > 1:
        builder.button(
            text="◀ Пред", callback_data=AdminCB(action="users_page", value=str(page - 1))
        )
    builder.button(text=f"{page}/{total_pages}", callback_data=AdminCB(action="noop"))
    if page < total_pages:
        builder.button(
            text="След ▶", callback_data=AdminCB(action="users_page", value=str(page + 1))
        )
    builder.button(text="🔙 Назад", callback_data=AdminCB(action="main"))
    builder.adjust(3, 1)
    return builder.as_markup()


def get_user_actions_kb(user_id: int, is_banned: bool) -> InlineKeyboardMarkup:
    """
    Действия над конкретным пользователем.

    Args:
        user_id: ID пользователя в БД.
        is_banned: Забанен ли пользователь.

    Returns:
        InlineKeyboardMarkup с действиями.
    """
    builder = InlineKeyboardBuilder()
    ban_text = "🔓 Разбанить" if is_banned else "🚫 Забанить"
    builder.button(text=ban_text, callback_data=AdminCB(action="toggle_ban", value=str(user_id)))
    builder.button(
        text="💰 Изменить баланс", callback_data=AdminCB(action="edit_balance", value=str(user_id))
    )
    builder.button(
        text="📊 Кампании", callback_data=AdminCB(action="user_campaigns", value=str(user_id))
    )
    builder.button(text="🔙 К списку", callback_data=AdminCB(action="users"))
    builder.adjust(2, 2)
    return builder.as_markup()


def get_back_kb() -> InlineKeyboardMarkup:
    """
    Кнопка назад.

    Returns:
        InlineKeyboardMarkup с кнопкой назад.
    """
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Назад", callback_data=AdminCB(action="main"))
    builder.adjust(1)
    return builder.as_markup()
