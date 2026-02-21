from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_campaign_step_kb(back: bool = True) -> InlineKeyboardMarkup:
    """Клавиатура для шагов создания кампании."""
    builder = InlineKeyboardBuilder()
    
    if back:
        builder.row(InlineKeyboardButton(text="← Назад", callback_data="campaign_back"))
    
    builder.row(InlineKeyboardButton(text="✖ Отмена", callback_data="campaign_cancel"))
    
    return builder.as_markup()


def get_campaign_confirm_kb() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения кампании."""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="✅ Запустить", callback_data="campaign_launch"),
        InlineKeyboardButton(text="📝 Изменить", callback_data="campaign_edit"),
    )
    builder.row(
        InlineKeyboardButton(text="💾 Черновик", callback_data="campaign_draft"),
        InlineKeyboardButton(text="✖ Отмена", callback_data="campaign_cancel"),
    )
    
    return builder.as_markup()


def get_topics_kb() -> InlineKeyboardMarkup:
    """Клавиатура выбора тематики."""
    topics = [
        "IT", "Бизнес", "Новости",
        "Маркетинг", "Финансы", "Крипта",
        "Недвижимость", "Услуги", "Другое"
    ]
    
    builder = InlineKeyboardBuilder()
    
    for topic in topics:
        builder.button(text=topic, callback_data=f"topic_{topic.lower()}")
    
    builder.adjust(3)
    
    return builder.as_markup()


def get_member_count_kb() -> InlineKeyboardMarkup:
    """Клавиатура выбора размера аудитории."""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="100-1К", callback_data="members_100_1k"),
        InlineKeyboardButton(text="1К-10К", callback_data="members_1k_10k"),
    )
    builder.row(
        InlineKeyboardButton(text="10К-100К", callback_data="members_10k_100k"),
        InlineKeyboardButton(text="Любой", callback_data="members_any"),
    )
    
    return builder.as_markup()
