"""Placement keyboards for campaign creation."""

from decimal import Decimal
from typing import Any

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

BACK_BTN = "Назад"
CANCEL_BTN = "Отменить"


def category_kb(categories: list[Any]) -> InlineKeyboardMarkup:
    """Выбор категории из БД (по 2 в ряд)."""
    builder = InlineKeyboardBuilder()
    for i in range(0, len(categories), 2):
        row = []
        cat = categories[i]
        row.append(
            InlineKeyboardButton(
                text=f"{cat.emoji} {cat.name_ru}",
                callback_data=f"camp:cat:{cat.slug}",
            )
        )
        if i + 1 < len(categories):
            cat2 = categories[i + 1]
            row.append(
                InlineKeyboardButton(
                    text=f"{cat2.emoji} {cat2.name_ru}",
                    callback_data=f"camp:cat:{cat2.slug}",
                )
            )
        builder.row(*row)
    builder.row(InlineKeyboardButton(text="Отмена", callback_data="main:adv_menu"))
    return builder.as_markup()


def channel_card_kb(cid: int, selected: bool, sel_count: int) -> InlineKeyboardMarkup:
    """Карточка канала."""
    builder = InlineKeyboardBuilder()
    btn_text = "❌ Убрать" if selected else "✅ Выбрать"
    builder.row(InlineKeyboardButton(text=btn_text, callback_data=f"camp:channel:select:{cid}"))
    builder.row(InlineKeyboardButton(text="Пропустить", callback_data="camp:channel:skip"))
    if sel_count > 0:
        builder.row(
            InlineKeyboardButton(text=f"Далее ({sel_count})", callback_data="camp:channels:done")
        )
    builder.row(InlineKeyboardButton(text=BACK_BTN, callback_data="camp:back:category"))
    return builder.as_markup()


def format_kb(allowed: list[str], plan: str, base: Decimal) -> InlineKeyboardMarkup:
    """Выбор формата публикации."""
    builder = InlineKeyboardBuilder()
    formats = {
        "post_24h": ("Пост 24ч", Decimal("1.0")),
        "post_48h": ("Пост 48ч", Decimal("1.4")),
        "post_7d": ("Пост 7дн", Decimal("2.0")),
        "pin_24h": ("Закреп 24ч", Decimal("3.0")),
        "pin_48h": ("Закреп 48ч", Decimal("4.0")),
    }
    plan_formats = {
        "free": ["post_24h"],
        "starter": ["post_24h", "post_48h"],
        "pro": ["post_24h", "post_48h", "post_7d"],
        "business": ["post_24h", "post_48h", "post_7d", "pin_24h", "pin_48h"],
    }
    available = plan_formats.get(plan, ["post_24h"])
    for fmt_code in allowed:
        if fmt_code in available:
            name, mult = formats.get(fmt_code, (fmt_code, Decimal("1.0")))
            price = base * mult
            builder.row(
                InlineKeyboardButton(
                    text=f"{name} — {price:.0f} ₽", callback_data=f"camp:format:{fmt_code}"
                )
            )
    builder.row(InlineKeyboardButton(text=BACK_BTN, callback_data="camp:back:channels"))
    return builder.as_markup()


def text_method_kb(plan: str, ai_left: int) -> InlineKeyboardMarkup:
    """Выбор метода ввода текста."""
    builder = InlineKeyboardBuilder()
    if plan != "free" and ai_left > 0:
        builder.row(InlineKeyboardButton(text="🤖 AI", callback_data="camp:text:ai"))
    builder.row(InlineKeyboardButton(text="✍️ Вручную", callback_data="camp:text:manual"))
    builder.row(InlineKeyboardButton(text=BACK_BTN, callback_data="camp:back:format"))
    return builder.as_markup()


def ai_variants_kb() -> InlineKeyboardMarkup:
    """AI варианты текста."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="1️⃣", callback_data="camp:text:choose:1"),
        InlineKeyboardButton(text="2️⃣", callback_data="camp:text:choose:2"),
        InlineKeyboardButton(text="3️⃣", callback_data="camp:text:choose:3"),
    )
    builder.row(InlineKeyboardButton(text="🔄 Ещё", callback_data="camp:text:ai:regenerate"))
    builder.row(InlineKeyboardButton(text="✍️ Вручную", callback_data="camp:text:manual"))
    return builder.as_markup()


def camp_confirm_kb() -> InlineKeyboardMarkup:
    """Подтверждение кампании."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Отправить", callback_data="camp:submit"))
    builder.row(
        InlineKeyboardButton(text="Изменить текст", callback_data="camp:back:text"),
        InlineKeyboardButton(text=CANCEL_BTN, callback_data="main:adv_menu"),
    )
    return builder.as_markup()


def camp_waiting_kb(rid: int) -> InlineKeyboardMarkup:
    """Ожидание ответа владельца."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Мои кампании", callback_data="main:my_campaigns"))
    builder.row(InlineKeyboardButton(text=CANCEL_BTN, callback_data=f"camp:cancel:{rid}"))
    return builder.as_markup()


def camp_payment_kb(rid: int, bal: Decimal, price: Decimal) -> InlineKeyboardMarkup:
    """Оплата кампании."""
    builder = InlineKeyboardBuilder()
    if bal >= price:
        builder.row(
            InlineKeyboardButton(text="Оплатить с баланса", callback_data=f"camp:pay:balance:{rid}")
        )
    else:
        builder.row(InlineKeyboardButton(text="Пополнить", callback_data="billing:topup_start"))
    builder.row(InlineKeyboardButton(text=CANCEL_BTN, callback_data=f"camp:cancel:{rid}"))
    return builder.as_markup()


def camp_counter_kb(rid: int, round: int) -> InlineKeyboardMarkup:
    """Контр-оффер."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Принять", callback_data=f"camp:counter:accept:{rid}"))
    if round < 3:
        builder.row(InlineKeyboardButton(text="Контр", callback_data=f"camp:counter:reply:{rid}"))
    builder.row(InlineKeyboardButton(text=CANCEL_BTN, callback_data=f"camp:cancel:{rid}"))
    return builder.as_markup()


def camp_published_kb(pid: int, within_48h: bool) -> InlineKeyboardMarkup:
    """Опубликованная кампания."""
    builder = InlineKeyboardBuilder()
    if within_48h:
        builder.row(InlineKeyboardButton(text="Пожаловаться", callback_data=f"dispute:open:{pid}"))
    builder.row(InlineKeyboardButton(text="Мои кампании", callback_data="main:my_campaigns"))
    return builder.as_markup()


def video_upload_keyboard() -> InlineKeyboardMarkup:
    """Предложение загрузить видео к рекламному посту."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🎬 Загрузить видео", callback_data="campaign:add_video"))
    builder.row(InlineKeyboardButton(text="⏭ Пропустить", callback_data="campaign:skip_video"))
    return builder.as_markup()


def video_confirm_keyboard() -> InlineKeyboardMarkup:
    """Подтверждение загруженного видео."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="✅ Продолжить", callback_data="campaign:video_confirm"))
    builder.row(InlineKeyboardButton(text="🔄 Заменить видео", callback_data="campaign:add_video"))
    builder.row(
        InlineKeyboardButton(text="❌ Удалить видео", callback_data="campaign:remove_video")
    )
    return builder.as_markup()
