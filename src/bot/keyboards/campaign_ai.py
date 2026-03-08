"""
Клавиатуры для создания кампании с AI.
"""

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


class AIVariantCB(CallbackData, prefix="ai_variant"):
    """Выбор варианта AI текста."""

    variant_index: int  # 0, 1, 2


class AIEditCB(CallbackData, prefix="ai_edit"):
    """Редактирование AI текста."""

    action: str  # "edit_text", "add_url", "add_image", "confirm"


class CampaignCreateCB(CallbackData, prefix="campaign_create"):
    """Создание кампании."""

    step: str  # "style_xxx", "category_xxx", "custom_category", "generate", "edit", "confirm"


# Стили текста для AI генерации
TEXT_STYLES = {
    "business": "👔 Деловой",
    "energetic": "🔥 Энергичный",
    "friendly": "😊 Дружелюбный",
    "creative": "🎨 Креативный",
    "professional": "💼 Профессиональный",
    "emotional": "❤️ Эмоциональный",
}

# Категории кампаний (20 основных)
CAMPAIGN_CATEGORIES = {
    "it_tech": "💻 IT и технологии",
    "business_finance": "💰 Бизнес и финансы",
    "education": "🎓 Образование и курсы",
    "retail_shop": "👗 Розница и магазины",
    "beauty_health": "💄 Красота и здоровье",
    "food_restaurant": "🍔 Еда и рестораны",
    "travel": "✈️ Путешествия",
    "real_estate": "🏠 Недвижимость",
    "auto": "🚗 Автомобили",
    "sports": "⚽ Спорт",
    "entertainment": "🎬 Развлечения",
    "marketing": "📈 Маркетинг",
    "crypto_invest": "₿ Криптовалюты",
    "psychology": "🧠 Психология",
    "parenting": "👶 Родительство",
    "fashion": "👠 Мода",
    "home_garden": "🏡 Дом и сад",
    "pets": "🐾 Животные",
    "news": "📰 Новости",
    "other": "📦 Другое",
}


def get_ai_style_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура выбора стиля текста для AI генерации.
    """
    builder = InlineKeyboardBuilder()

    for style_key, style_name in TEXT_STYLES.items():
        builder.button(
            text=style_name,
            callback_data=CampaignCreateCB(step=f"style_{style_key}").pack()
        )

    builder.adjust(2, 2, 2)

    builder.button(text="🔙 Назад", callback_data=CampaignCreateCB(step="back_to_menu").pack())
    builder.adjust(1)

    return builder.as_markup()


def get_ai_category_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура выбора категории кампании.
    """
    builder = InlineKeyboardBuilder()

    # Показываем по 3 категории в ряд
    categories_list = list(CAMPAIGN_CATEGORIES.items())
    for i in range(0, len(categories_list), 3):
        for cat_key, cat_name in categories_list[i:i+3]:
            builder.button(
                text=cat_name,
                callback_data=CampaignCreateCB(step=f"category_{cat_key}").pack()
            )
        builder.adjust(3)

    builder.button(
        text="✍️ Своя категория",
        callback_data=CampaignCreateCB(step="custom_category").pack()
    )
    builder.adjust(1)

    builder.button(text="🔙 Назад", callback_data=CampaignCreateCB(step="back_to_style").pack())
    builder.adjust(1)

    return builder.as_markup()


def get_ai_variants_keyboard(variants: list[str]) -> InlineKeyboardMarkup:
    """
    Клавиатура с вариантами AI текстов.

    Args:
        variants: Список сгенерированных текстов.
    """
    builder = InlineKeyboardBuilder()

    # Кнопки выбора вариантов
    for i, variant in enumerate(variants[:3], 1):
        preview = variant[:100].replace("\n", " ") + "..." if len(variant) > 100 else variant
        builder.button(
            text=f"📝 Вариант {i}: {preview}",
            callback_data=AIVariantCB(variant_index=i - 1).pack(),
        )

    # Кнопки действий
    builder.button(
        text="🔄 Сгенерировать заново", callback_data=CampaignCreateCB(step="regenerate").pack()
    )
    builder.button(
        text="✏️ Написать свой текст", callback_data=CampaignCreateCB(step="manual_text").pack()
    )
    builder.button(text="🔙 Назад", callback_data=CampaignCreateCB(step="back_to_category").pack())

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
    builder.button(text="✅ Далее", callback_data=AIEditCB(action="confirm").pack())

    # Назад
    builder.button(text="🔙 Назад", callback_data=CampaignCreateCB(step="back_to_variants").pack())

    builder.adjust(1, 2, 1, 1)

    return builder.as_markup()


def get_audience_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура выбора аудитории для кампании.
    Показывает топ-8 тематик из categories.py.
    Кнопка "Все тематики" — без фильтра.
    Кнопка "Пропустить" — перейти дальше без фильтра.
    """
    builder = InlineKeyboardBuilder()

    # Основные тематики (из CAMPAIGN_CATEGORIES)
    audience_options = {
        "it_tech": "💻 IT и технологии",
        "business_finance": "💰 Бизнес и финансы",
        "marketing": "📈 Маркетинг",
        "education": "🎓 Образование",
        "crypto_invest": "₿ Криптовалюты",
        "retail_shop": "👗 Розница",
        "beauty_health": "💄 Красота и здоровье",
        "food_restaurant": "🍔 Еда и рестораны",
    }

    for key, name in audience_options.items():
        builder.button(
            text=name,
            callback_data=CampaignCreateCB(step=f"audience_{key}").pack()
        )

    builder.adjust(2, 2, 2, 2)

    # Кнопки "Все тематики" и "Пропустить"
    builder.button(
        text="📡 Все доступные каналы",
        callback_data=CampaignCreateCB(step="audience_all").pack()
    )
    builder.button(
        text="⏭️ Пропустить →",
        callback_data=CampaignCreateCB(step="audience_skip").pack()
    )
    builder.adjust(2)

    # Кнопка "Назад"
    builder.button(
        text="🔙 Назад",
        callback_data=CampaignCreateCB(step="back_to_image").pack()
    )
    builder.adjust(1)

    return builder.as_markup()


def get_schedule_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура планирования кампании.
    Опции:
    - "Запустить сейчас" → scheduled_at = None
    - "Через 1 час"     → scheduled_at = now + 1h
    - "Сегодня вечером" → scheduled_at = сегодня 20:00 МСК
    - "Завтра утром"    → scheduled_at = завтра 09:00 МСК
    - "Выбрать дату"    → запросить ввод текстом
    """
    builder = InlineKeyboardBuilder()

    # Быстрые опции
    builder.button(
        text="🚀 Запустить сейчас",
        callback_data=CampaignCreateCB(step="schedule_now").pack()
    )
    builder.button(
        text="⏰ Через 1 час",
        callback_data=CampaignCreateCB(step="schedule_1h").pack()
    )
    builder.button(
        text="🌆 Сегодня вечером (20:00)",
        callback_data=CampaignCreateCB(step="schedule_evening").pack()
    )
    builder.button(
        text="🌅 Завтра утром (09:00)",
        callback_data=CampaignCreateCB(step="schedule_tomorrow").pack()
    )

    builder.adjust(1)

    # Кнопка выбора даты
    builder.button(
        text="📅 Выбрать дату",
        callback_data=CampaignCreateCB(step="schedule_custom").pack()
    )
    builder.adjust(1)

    # Кнопка "Назад"
    builder.button(
        text="🔙 Назад",
        callback_data=CampaignCreateCB(step="back_to_budget").pack()
    )
    builder.adjust(1)

    return builder.as_markup()
