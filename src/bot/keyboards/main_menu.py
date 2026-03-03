"""
Клавиатура главного меню бота.
"""

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.config.settings import settings


class MainMenuCB(CallbackData, prefix="main"):
    """CallbackData для главного меню."""

    action: str
    value: str = ""


class ModelCB(CallbackData, prefix="model"):
    """CallbackData для выбора модели ИИ."""

    provider: str


def _is_admin(user_id: int) -> bool:
    """Проверить, является ли пользователь админом."""
    return user_id in settings.admin_ids


def get_main_menu(credits: int, user_id: int | None = None) -> InlineKeyboardMarkup:
    """
    Главное меню бота.

    7 кнопок: Создать кампанию, Мои кампании, Аналитика, База каналов, Шаблоны, Кабинет, Обратная связь.
    Для админов: дополнительная кнопка Админ.

    Args:
        credits: Баланс пользователя в кредитах.
        user_id: ID пользователя (опционально, для определения админа).

    Returns:
        InlineKeyboardMarkup с кнопками меню.
    """
    builder = InlineKeyboardBuilder()

    # Кнопка Mini App отключена до настройки production домена
    # if settings.mini_app_url:
    #     builder.row(
    #         InlineKeyboardButton(
    #             text="📱 Открыть кабинет",
    #             web_app=WebAppInfo(url=settings.mini_app_url),
    #         )
    #     )

    # Объединённая кнопка создания — ведёт в sub-меню выбора способа
    builder.button(text="📣 Создать кампанию", callback_data=MainMenuCB(action="create_menu"))
    builder.button(text="📋 Мои кампании", callback_data=MainMenuCB(action="my_campaigns"))
    builder.button(text="📊 Аналитика", callback_data=MainMenuCB(action="analytics"))
    builder.button(text="📡 База каналов", callback_data=MainMenuCB(action="channels_db"))
    builder.button(text="📄 Шаблоны", callback_data=MainMenuCB(action="templates"))
    # Объединить кабинет и баланс — баланс видно прямо в кнопке
    builder.button(text=f"👤 Кабинет • {credits:,} кр", callback_data=MainMenuCB(action="cabinet"))
    builder.button(text="💬 Обратная связь", callback_data=MainMenuCB(action="feedback"))

    # Только для админов: панель управления
    if user_id and _is_admin(user_id):
        builder.button(text="🔐 Админ", callback_data=MainMenuCB(action="admin_panel"))
        builder.adjust(2, 2, 2, 1, 1)
    else:
        builder.adjust(2, 2, 2, 1)

    return builder.as_markup()
