"""
Клавиатуры для FSM wizard'а создания кампании.
"""

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.bot.keyboards.shared.main_menu import MainMenuCB


class CampaignCB(CallbackData, prefix="campaign"):
    """CallbackData для навигации wizard'а кампании."""

    action: str
    value: str = ""


# Список тематик
TOPICS = [
    "IT",
    "Бизнес",
    "Новости",
    "Услуги",
    "Товары",
    "Крипта",
    "Курсы",
    "Недвижимость",
    "Другое",
]


def get_campaign_step_kb(back: bool = True) -> InlineKeyboardMarkup:
    """
    Клавиатура навигации шага wizard'а.

    Args:
        back: Показывать ли кнопку "Назад".

    Returns:
        InlineKeyboardMarkup с кнопками навигации.
    """
    builder = InlineKeyboardBuilder()
    if back:
        builder.button(text="← Назад", callback_data=CampaignCB(action="back"))
    builder.button(text="✖ Отмена", callback_data=CampaignCB(action="cancel"))
    builder.adjust(2 if back else 1)
    return builder.as_markup()


def get_text_type_kb(user_plan: str = "free") -> InlineKeyboardMarkup:
    """
    Клавиатура выбора типа ввода текста.

    Args:
        user_plan: Тариф пользователя. FREE скрывает кнопку ИИ.

    Returns:
        InlineKeyboardMarkup с выбором: вручную или ИИ.
    """
    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Ввести текст", callback_data=CampaignCB(action="manual_text"))
    if user_plan != "free":
        builder.button(
            text="🤖 Сгенерировать через ИИ (+10₽)", callback_data=CampaignCB(action="ai_text")
        )
    else:
        builder.button(
            text="🤖 ИИ — доступно от STARTER", callback_data=CampaignCB(action="ai_locked")
        )
    builder.button(text="👁 Предпросмотр", callback_data=CampaignCB(action="preview_post"))
    builder.button(text="← Назад", callback_data=CampaignCB(action="back"))
    builder.button(text="✖ Отмена", callback_data=CampaignCB(action="cancel"))
    builder.adjust(2, 2, 2)
    return builder.as_markup()


def get_topics_kb() -> InlineKeyboardMarkup:
    """
    Клавиатура выбора тематики кампании.

    Returns:
        InlineKeyboardMarkup с 9 тематиками.
    """
    builder = InlineKeyboardBuilder()
    for topic in TOPICS:
        builder.button(text=topic, callback_data=CampaignCB(action="topic", value=topic))
    builder.button(text="← Назад", callback_data=CampaignCB(action="back"))
    builder.button(text="✖ Отмена", callback_data=CampaignCB(action="cancel"))
    builder.adjust(3, 3, 3, 2)
    return builder.as_markup()


def get_member_count_kb() -> InlineKeyboardMarkup:
    """
    Клавиатура выбора размера аудитории.

    Returns:
        InlineKeyboardMarkup с вариантами размера чатов.
    """
    builder = InlineKeyboardBuilder()
    options = [
        ("100–1К", "100_1000"),
        ("1К–10К", "1000_10000"),
        ("10К–100К", "10000_100000"),
        ("Любой", "any"),
    ]
    for label, value in options:
        builder.button(text=label, callback_data=CampaignCB(action="members", value=value))
    builder.button(text="← Назад", callback_data=CampaignCB(action="back"))
    builder.button(text="✖ Отмена", callback_data=CampaignCB(action="cancel"))
    builder.adjust(2, 2, 2)
    return builder.as_markup()


def get_schedule_kb() -> InlineKeyboardMarkup:
    """
    Клавиатура выбора расписания запуска.

    Returns:
        InlineKeyboardMarkup с выбором: сейчас или позже.
    """
    builder = InlineKeyboardBuilder()
    builder.button(text="▶️ Сейчас", callback_data=CampaignCB(action="schedule_now"))
    builder.button(text="⏰ Запланировать", callback_data=CampaignCB(action="schedule_later"))
    builder.button(text="← Назад", callback_data=CampaignCB(action="back"))
    builder.button(text="✖ Отмена", callback_data=CampaignCB(action="cancel"))
    builder.adjust(2, 2)
    return builder.as_markup()


def get_campaign_confirm_kb() -> InlineKeyboardMarkup:
    """
    Клавиатура подтверждения кампании.

    Returns:
        InlineKeyboardMarkup с вариантами: запустить, изменить, черновик, отмена.
    """
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Запустить", callback_data=CampaignCB(action="confirm_launch"))
    builder.button(text="📝 Изменить", callback_data=CampaignCB(action="confirm_edit"))
    builder.button(text="💾 Черновик", callback_data=CampaignCB(action="confirm_draft"))
    builder.button(text="✖ Отмена", callback_data=CampaignCB(action="cancel"))
    builder.adjust(2, 2)
    return builder.as_markup()


def get_image_upload_kb() -> InlineKeyboardMarkup:
    """
    Клавиатура для загрузки изображения.

    Returns:
        InlineKeyboardMarkup с вариантами: загрузить, пропустить.
    """
    builder = InlineKeyboardBuilder()
    builder.button(text="📷 Загрузить фото", callback_data=CampaignCB(action="image_upload"))
    builder.button(text="⏭ Пропустить", callback_data=CampaignCB(action="image_skip"))
    builder.button(text="← Назад", callback_data=CampaignCB(action="back"))
    builder.adjust(2, 1)
    return builder.as_markup()


def get_campaign_detail_kb(campaign_id: int, status: str) -> InlineKeyboardMarkup:
    """
    Клавиатура действий в зависимости от статуса кампании.

    Args:
        campaign_id: ID кампании.
        status: Статус кампании (draft, queued, running, paused, completed, cancelled, done, error).

    Returns:
        InlineKeyboardMarkup с кнопками управления.
    """
    builder = InlineKeyboardBuilder()

    if status == "draft":
        builder.button(
            text="▶️ Запустить",
            callback_data=CampaignCB(action="launch", value=str(campaign_id)),
        )
        builder.button(
            text="🗑 Удалить",
            callback_data=CampaignCB(action="delete", value=str(campaign_id)),
        )
    elif status == "queued":
        builder.button(
            text="❌ Отменить",
            callback_data=CampaignCB(action="cancel_campaign", value=str(campaign_id)),
        )
    elif status == "running":
        builder.button(
            text="⏸ Пауза",
            callback_data=CampaignCB(action="pause", value=str(campaign_id)),
        )
        builder.button(
            text="❌ Отменить",
            callback_data=CampaignCB(action="cancel_campaign", value=str(campaign_id)),
        )
    elif status == "paused":
        builder.button(
            text="▶️ Продолжить",
            callback_data=CampaignCB(action="resume", value=str(campaign_id)),
        )
        builder.button(
            text="❌ Отменить",
            callback_data=CampaignCB(action="cancel_campaign", value=str(campaign_id)),
        )
    elif status in ("completed", "done"):
        builder.button(
            text="📊 Аналитика",
            callback_data=CampaignCB(action="analytics", value=str(campaign_id)),
        )
        builder.button(
            text="📋 Дублировать",
            callback_data=CampaignCB(action="duplicate", value=str(campaign_id)),
        )
    elif status == "error" or status == "cancelled":
        builder.button(
            text="📋 Дублировать",
            callback_data=CampaignCB(action="duplicate", value=str(campaign_id)),
        )

    builder.button(text="🔙 Назад", callback_data=MainMenuCB(action="my_campaigns"))
    builder.adjust(2, 1)
    return builder.as_markup()
