"""
Клавиатуры для создания кампании с AI.
"""

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


class AIVariantCB(CallbackData, prefix="ai_variant"):
    """Выбор варианта AI текста."""

    variant_index: int  # 0, 1, 2
    topic: str


class AIEditCB(CallbackData, prefix="ai_edit"):
    """Редактирование AI текста."""

    action: str  # "edit_text", "add_url", "add_image", "confirm"


class CampaignCreateCB(CallbackData, prefix="campaign_create"):
    """Создание кампании."""

    step: str  # "topic", "generate", "edit", "confirm"


def get_ai_topic_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура выбора тематики для AI генерации.
    """
    builder = InlineKeyboardBuilder()

    builder.button(
        text="🎓 Образование", callback_data=CampaignCreateCB(step="topic_education").pack()
    )
    builder.button(text="👗 Розница", callback_data=CampaignCreateCB(step="topic_retail").pack())
    builder.button(text="💰 Финансы", callback_data=CampaignCreateCB(step="topic_finance").pack())
    builder.button(text="☕ Другое", callback_data=CampaignCreateCB(step="topic_default").pack())

    builder.adjust(2, 2)

    builder.button(text="🔙 Назад", callback_data=CampaignCreateCB(step="back_to_menu").pack())
    builder.adjust(1)

    return builder.as_markup()


def get_ai_variants_keyboard(variants: list[str], topic: str) -> InlineKeyboardMarkup:
    """
    Клавиатура с вариантами AI текстов.

    Args:
        variants: Список сгенерированных текстов.
        topic: Тематика кампании.
    """
    builder = InlineKeyboardBuilder()

    # Кнопки выбора вариантов
    for i, variant in enumerate(variants[:3], 1):
        preview = variant[:100].replace("\n", " ") + "..." if len(variant) > 100 else variant
        builder.button(
            text=f"📝 Вариант {i}: {preview}",
            callback_data=AIVariantCB(variant_index=i - 1, topic=topic).pack(),
        )

    # Кнопки действий
    builder.button(
        text="🔄 Сгенерировать заново", callback_data=CampaignCreateCB(step="regenerate").pack()
    )
    builder.button(
        text="✏️ Написать свой текст", callback_data=CampaignCreateCB(step="manual_text").pack()
    )
    builder.button(text="🔙 Назад", callback_data=CampaignCreateCB(step="back_to_menu").pack())

    builder.adjust(1)

    return builder.as_markup()


def get_campaign_editor_keyboard(
    text: str,
    has_url: bool = False,
    has_image: bool = False,
) -> InlineKeyboardMarkup:
    """
    Клавиатура редактора кампании.

    Args:
        text: Текст кампании.
        has_url: Есть ли URL.
        has_image: Есть ли изображение.
    """
    builder = InlineKeyboardBuilder()

    # Редактирование текста
    builder.button(
        text="✏️ Изменить текст" + (" ✅" if len(text) < 100 else ""),
        callback_data=AIEditCB(action="edit_text").pack(),
    )

    # Добавление URL
    url_status = "✅" if has_url else "❌"
    builder.button(
        text=f"🔗 Добавить ссылку {url_status}", callback_data=AIEditCB(action="add_url").pack()
    )

    # Добавление изображения
    image_status = "✅" if has_image else "❌"
    builder.button(
        text=f"🖼️ Добавить изображение {image_status}",
        callback_data=AIEditCB(action="add_image").pack(),
    )

    # Подтверждение
    builder.button(text="✅ Создать кампанию", callback_data=AIEditCB(action="confirm").pack())

    # Назад
    builder.button(text="🔙 Назад", callback_data=CampaignCreateCB(step="back_to_variants").pack())

    builder.adjust(1)

    return builder.as_markup()


def get_quick_campaign_keyboard(variant_index: int, topic: str) -> InlineKeyboardMarkup:
    """
    Быстрое создание кампании с выбранным вариантом.

    Args:
        variant_index: Индекс выбранного варианта.
        topic: Тематика.
    """
    builder = InlineKeyboardBuilder()

    builder.button(
        text="🚀 Быстро создать кампанию",
        callback_data=AIVariantCB(variant_index=variant_index, topic=topic).pack(),
    )

    builder.button(
        text="✏️ Редактировать перед созданием",
        callback_data=AIEditCB(action="edit_before_create").pack(),
    )

    builder.button(
        text="🔙 К вариантам", callback_data=CampaignCreateCB(step="back_to_variants").pack()
    )

    builder.adjust(1)

    return builder.as_markup()
