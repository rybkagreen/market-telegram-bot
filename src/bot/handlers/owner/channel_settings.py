"""Owner channel settings handler."""

import logging
from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.states.channel_settings import ChannelSettingsStates
from src.db.models.channel_settings import ChannelSettings
from src.db.models.telegram_chat import TelegramChat

logger = logging.getLogger(__name__)
router = Router()

_FORMATS = [
    ("post_24h", "📄 Пост 24ч", "allow_format_post_24h"),
    ("post_48h", "📄 Пост 48ч", "allow_format_post_48h"),
    ("post_7d", "📄 Пост 7 дней", "allow_format_post_7d"),
    ("pin_24h", "📌 Закреп 24ч", "allow_format_pin_24h"),
    ("pin_48h", "📌 Закреп 48ч", "allow_format_pin_48h"),
]


async def _get_or_create_settings(session: AsyncSession, channel_id: int) -> ChannelSettings:
    settings = await session.get(ChannelSettings, channel_id)
    if not settings:
        settings = ChannelSettings(channel_id=channel_id)
        session.add(settings)
        await session.commit()
    return settings


# ---------------------------------------------------------------------------
# Main settings screen  –  own:settings:{channel_id}  (numeric id only)
# ---------------------------------------------------------------------------


@router.callback_query(F.data.regexp(r"^own:settings:\d+$"))
async def show_settings(callback: CallbackQuery, session: AsyncSession) -> None:
    """Показать настройки канала."""
    if not isinstance(callback.message, Message):
        return
    channel_id = int((callback.data or "").split(":")[-1])
    ch = await session.get(TelegramChat, channel_id)
    settings = await _get_or_create_settings(session, channel_id)

    formats_lines = []
    for _key, name, attr in _FORMATS:
        icon = "✅" if getattr(settings, attr, False) else "❌"
        formats_lines.append(f"{icon} {name}")

    start = settings.publish_start_time.strftime("%H:%M") if settings.publish_start_time else "09:00"
    end = settings.publish_end_time.strftime("%H:%M") if settings.publish_end_time else "21:00"
    brk_str = (
        f"{settings.break_start_time.strftime('%H:%M')}–{settings.break_end_time.strftime('%H:%M')}"
        if settings.break_start_time and settings.break_end_time
        else "нет"
    )

    auto_label = "🟢 Вкл" if settings.auto_accept_enabled else "🔴 Выкл"
    builder = InlineKeyboardBuilder()
    builder.button(text="💰 Изменить цену", callback_data=f"own:settings:price:{channel_id}")
    builder.button(text="📄 Форматы публикаций", callback_data=f"own:settings:formats:{channel_id}")
    builder.button(text="⏰ Расписание", callback_data=f"own:settings:schedule:{channel_id}")
    builder.button(
        text=f"🤖 Автоподтверждение: {auto_label}",
        callback_data=f"own:settings:autoaccept:{channel_id}",
    )
    builder.button(text="🔙 Детали канала", callback_data=f"own:channel:{channel_id}")
    builder.adjust(1)

    ch_name = f"@{ch.username}" if ch and ch.username else str(channel_id)
    await callback.message.edit_text(
        f"⚙️ *Настройки {ch_name}*\n\n"
        f"💰 Цена: *{settings.price_per_post:.0f} ₽*\n"
        f"⏰ Время: *{start}*–*{end}*\n"
        f"☕ Перерыв: *{brk_str}*\n"
        f"📅 Макс./день: *{settings.max_posts_per_day}*\n\n"
        f"─── Форматы ───\n" + "\n".join(formats_lines),
        reply_markup=builder.as_markup(),
        parse_mode="Markdown",
    )
    await callback.answer()


# ---------------------------------------------------------------------------
# Price editing
# ---------------------------------------------------------------------------


@router.callback_query(F.data.startswith("own:settings:price:"))
async def edit_price_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Начать редактирование цены."""
    if not isinstance(callback.message, Message):
        return
    channel_id = int((callback.data or "").split(":")[-1])
    await state.update_data(editing_channel_id=channel_id)
    await state.set_state(ChannelSettingsStates.editing_price)

    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data=f"own:settings:{channel_id}")
    await callback.message.edit_text(
        "💰 Введите новую базовую цену за пост (₽):\n\n📌 Минимум: 100 ₽\nПример: 1500",
        reply_markup=builder.as_markup(),
    )
    await callback.answer()


@router.message(ChannelSettingsStates.editing_price)
async def edit_price_input(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Сохранить новую цену."""
    try:
        price = Decimal((message.text or "").strip().replace(" ", ""))
        if price < 100:
            await message.answer("❌ Минимальная цена — 100 ₽")
            return
    except InvalidOperation:
        await message.answer("❌ Введите число (например: 1500)")
        return

    data = await state.get_data()
    channel_id = data["editing_channel_id"]

    settings = await _get_or_create_settings(session, channel_id)
    settings.price_per_post = price
    await session.commit()
    await state.clear()

    builder = InlineKeyboardBuilder()
    builder.button(text="⚙️ Назад к настройкам", callback_data=f"own:settings:{channel_id}")
    await message.answer(
        f"✅ Цена обновлена: *{price:.0f} ₽*",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown",
    )


# ---------------------------------------------------------------------------
# Formats editing
# ---------------------------------------------------------------------------


@router.callback_query(F.data.regexp(r"^own:settings:formats:\d+$"))
async def edit_formats(callback: CallbackQuery, session: AsyncSession) -> None:
    """Показать экран редактирования форматов."""
    if not isinstance(callback.message, Message):
        return
    channel_id = int((callback.data or "").split(":")[-1])
    settings = await _get_or_create_settings(session, channel_id)

    builder = InlineKeyboardBuilder()
    for fmt_key, name, attr in _FORMATS:
        enabled = getattr(settings, attr, False)
        icon = "✅" if enabled else "❌"
        builder.button(
            text=f"{icon} {name}",
            callback_data=f"own:format:toggle:{fmt_key}:{channel_id}",
        )
    builder.button(text="💾 Готово", callback_data=f"own:settings:{channel_id}")
    builder.button(text="🔙 Назад", callback_data=f"own:settings:{channel_id}")
    builder.adjust(1)

    await callback.message.edit_text(
        "📄 *Форматы публикаций*\n\nВключите или выключите нужные форматы:",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("own:format:toggle:"))
async def toggle_format(callback: CallbackQuery, session: AsyncSession) -> None:
    """Переключить формат и перерисовать экран."""
    parts = (callback.data or "").split(":")
    fmt_key = parts[3]
    channel_id = int(parts[4])

    settings = await session.get(ChannelSettings, channel_id)
    if not settings:
        await callback.answer("❌ Настройки не найдены", show_alert=True)
        return

    attr_map = {
        "post_24h": "allow_format_post_24h",
        "post_48h": "allow_format_post_48h",
        "post_7d": "allow_format_post_7d",
        "pin_24h": "allow_format_pin_24h",
        "pin_48h": "allow_format_pin_48h",
    }
    attr = attr_map.get(fmt_key)
    if attr:
        setattr(settings, attr, not getattr(settings, attr))
        await session.commit()

    # Re-draw formats screen
    callback.data = f"own:settings:formats:{channel_id}"
    await edit_formats(callback, session)


# ---------------------------------------------------------------------------
# Auto-accept toggle
# ---------------------------------------------------------------------------


@router.callback_query(F.data.startswith("own:settings:autoaccept:"))
async def toggle_autoaccept(callback: CallbackQuery, session: AsyncSession) -> None:
    """Переключить автоподтверждение."""
    channel_id = int((callback.data or "").split(":")[-1])
    settings = await session.get(ChannelSettings, channel_id)
    if not settings:
        await callback.answer("❌ Настройки не найдены", show_alert=True)
        return

    settings.auto_accept_enabled = not settings.auto_accept_enabled
    await session.commit()

    status = "включено" if settings.auto_accept_enabled else "выключено"
    await callback.answer(f"Автоподтверждение {status}")

    callback.data = f"own:settings:{channel_id}"
    await show_settings(callback, session)


# ---------------------------------------------------------------------------
# Schedule editing
# ---------------------------------------------------------------------------


@router.callback_query(F.data.regexp(r"^own:settings:schedule:\d+$"))
async def edit_schedule(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    """Открыть форму редактирования расписания."""
    if not isinstance(callback.message, Message):
        return
    channel_id = int((callback.data or "").split(":")[-1])
    settings = await _get_or_create_settings(session, channel_id)

    start = settings.publish_start_time.strftime("%H:%M") if settings.publish_start_time else "09:00"
    end = settings.publish_end_time.strftime("%H:%M") if settings.publish_end_time else "21:00"
    brk = (
        f"{settings.break_start_time.strftime('%H:%M')}–{settings.break_end_time.strftime('%H:%M')}"
        if settings.break_start_time and settings.break_end_time
        else "нет"
    )

    await state.update_data(editing_channel_id=channel_id)
    await state.set_state(ChannelSettingsStates.editing_schedule)

    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data=f"own:settings:{channel_id}")

    await callback.message.edit_text(
        f"⏰ *Расписание публикаций*\n\n"
        f"Текущее: *{start}*–*{end}* (перерыв: {brk})\n\n"
        f"Введите новое расписание в формате:\n"
        f"`ЧЧ:ММ-ЧЧ:ММ` — например: `09:00-21:00`\n\n"
        f"Или с перерывом:\n"
        f"`09:00-21:00 14:00-15:00`",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.message(ChannelSettingsStates.editing_schedule)
async def edit_schedule_input(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Сохранить новое расписание."""
    import re as _re
    from datetime import time as dt_time

    text = (message.text or "").strip()
    pattern = r"^(\d{2}:\d{2})-(\d{2}:\d{2})(?:\s+(\d{2}:\d{2})-(\d{2}:\d{2}))?$"
    m = _re.match(pattern, text)
    if not m:
        await message.answer(
            "❌ Неверный формат.\n\nПримеры:\n`09:00-21:00`\n`09:00-21:00 14:00-15:00`",
            parse_mode="Markdown",
        )
        return

    def _parse(s: str) -> dt_time:
        h, mn = map(int, s.split(":"))
        return dt_time(h, mn)

    try:
        start = _parse(m.group(1))
        end = _parse(m.group(2))
        brk_start = _parse(m.group(3)) if m.group(3) else None
        brk_end = _parse(m.group(4)) if m.group(4) else None
    except ValueError:
        await message.answer("❌ Неверное время. Используйте формат ЧЧ:ММ (например 09:00)")
        return

    if start >= end:
        await message.answer("❌ Время начала должно быть раньше времени окончания.")
        return

    data = await state.get_data()
    channel_id = data["editing_channel_id"]

    settings = await _get_or_create_settings(session, channel_id)
    settings.publish_start_time = start
    settings.publish_end_time = end
    settings.break_start_time = brk_start
    settings.break_end_time = brk_end
    await session.commit()
    await state.clear()

    brk_str = f"{m.group(3)}–{m.group(4)}" if brk_start else "нет"

    builder = InlineKeyboardBuilder()
    builder.button(text="⚙️ Назад к настройкам", callback_data=f"own:settings:{channel_id}")

    await message.answer(
        f"✅ *Расписание обновлено!*\n\n"
        f"⏰ Публикации: *{m.group(1)}*–*{m.group(2)}*\n"
        f"☕ Перерыв: *{brk_str}*",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown",
    )
