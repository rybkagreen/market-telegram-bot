from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


class CampaignCB(CallbackData, prefix="campaign"):
    """CallbackData для кампаний."""
    action: str
    step: str | None = None


class TopicCB(CallbackData, prefix="topic"):
    """CallbackData для тематик."""
    topic_name: str


class MemberCountCB(CallbackData, prefix="members"):
    """CallbackData для размера аудитории."""
    count_range: str


def get_campaign_step_kb(back: bool = True) -> InlineKeyboardMarkup:
    """Клавиатура для шагов создания кампании."""
    builder = InlineKeyboardBuilder()
    
    if back:
        builder.button(
            text="← Назад",
            callback_data=CampaignCB(action="back", step="prev").pack()
        )
    
    builder.button(
        text="✖ Отмена",
        callback_data=CampaignCB(action="cancel", step=None).pack()
    )
    
    builder.adjust(2)
    
    return builder.as_markup()


def get_campaign_confirm_kb() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения кампании."""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="✅ Запустить", callback_data=CampaignCB(action="launch", step=None).pack()),
        InlineKeyboardButton(text="📝 Изменить", callback_data=CampaignCB(action="edit", step=None).pack()),
    )
    builder.row(
        InlineKeyboardButton(text="💾 Черновик", callback_data=CampaignCB(action="draft", step=None).pack()),
        InlineKeyboardButton(text="✖ Отмена", callback_data=CampaignCB(action="cancel", step=None).pack()),
    )
    
    return builder.as_markup()


def get_topics_kb() -> InlineKeyboardMarkup:
    """Клавиатура выбора тематики."""
    topics = [
        ("IT", "it"),
        ("Бизнес", "business"),
        ("Новости", "news"),
        ("Маркетинг", "marketing"),
        ("Финансы", "finance"),
        ("Крипта", "crypto"),
        ("Недвижимость", "realty"),
        ("Услуги", "services"),
        ("Другое", "other"),
    ]
    
    builder = InlineKeyboardBuilder()
    
    for topic_name, topic_id in topics:
        builder.button(
            text=topic_name,
            callback_data=TopicCB(topic_name=topic_id).pack()
        )
    
    builder.adjust(3)
    
    return builder.as_markup()


def get_member_count_kb() -> InlineKeyboardMarkup:
    """Клавиатура выбора размера аудитории."""
    builder = InlineKeyboardBuilder()
    
    ranges = [
        ("100-1К", "100_1k"),
        ("1К-10К", "1k_10k"),
        ("10К-100К", "10k_100k"),
        ("Любой", "any"),
    ]
    
    for label, value in ranges:
        builder.button(
            text=label,
            callback_data=MemberCountCB(count_range=value).pack()
        )
    
    builder.adjust(2)
    
    return builder.as_markup()
