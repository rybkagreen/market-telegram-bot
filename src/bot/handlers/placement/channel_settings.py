"""
CRUD настроек канала через модель ChannelSettings.
Этап 3.1 — полное управление конфигурацией монетизации канала.

Callback prefix: ch_cfg:* (чтобы не конфликтовать с ch_settings: из channel_owner.py)
"""

import logging
from datetime import datetime, time
from decimal import Decimal

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InaccessibleMessage,
    Message,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.bot.states.channel_settings import ChannelSettingsStates
from src.bot.utils.safe_callback import safe_callback_edit
from src.constants.payments import PLATFORM_COMMISSION
from src.db.models.analytics import TelegramChat
from src.db.models.channel_settings import (
    MAX_PACKAGE_DISCOUNT,
    MAX_SUBSCRIPTION_DAYS,
    MIN_SUBSCRIPTION_DAYS,
    ChannelSettings,
)
from src.db.repositories.channel_settings_repo import ChannelSettingsRepo
from src.db.session import async_session_factory

logger = logging.getLogger(__name__)
router = Router(name="channel_settings_owner")

# =============================================================================
# КОНСТАНТЫ
# =============================================================================

MIN_PRICE_PER_POST_INT: int = 100  # минимальная цена за пост в кредитах
MAX_POSTS_PER_DAY_INT: int = 5  # максимум постов в день
MIN_HOURS_BETWEEN_POSTS_INT: int = 4  # минимум часов между постами
# PLATFORM_COMMISSION импортируется из src.constants.payments

# =============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =============================================================================


def parse_time(value: str) -> time | None:
    """Распарсить "HH:MM" → time. None если формат неверный."""
    try:
        return datetime.strptime(value.strip(), "%H:%M").time()
    except ValueError:
        return None


def time_to_str(t: time | None) -> str:
    """Конвертировать time → "HH:MM". Пустая строка если None."""
    if t is None:
        return "—"
    return t.strftime("%H:%M")


async def show_channel_cfg_menu(
    callback: CallbackQuery,
    channel_id: int,
    settings: ChannelSettings,
) -> None:
    """
    Показать главное меню настроек канала.

    Args:
        callback: Callback query.
        channel_id: ID канала.
        settings: Объект настроек.
    """
    # Получаем username канала
    username = getattr(callback.message, "chat", None)
    channel_username = f"@{username.username}" if username and hasattr(username, "username") and username.username else f"ID:{channel_id}"

    # Формируем текст
    owner_earnings = float(settings.price_per_post) * (1 - float(PLATFORM_COMMISSION))

    text = (
        f"⚙️ <b>Настройки канала {channel_username}</b>\n\n"
        f"💰 Цена за пост: {settings.price_per_post:.0f} ₽ → вы получаете {owner_earnings:.0f} ₽ ({(1 - float(PLATFORM_COMMISSION)) * 100:.0f}%)\n"
        f"🕐 Публикации: {time_to_str(settings.publish_start_time)} – {time_to_str(settings.publish_end_time)}\n"
        f"☕ Перерыв: {time_to_str(settings.break_start_time)} – {time_to_str(settings.break_end_time)}\n"
        f"📅 Макс постов/день: {settings.daily_package_max}\n"
        f"⏱ Мин. между постами: {MIN_HOURS_BETWEEN_POSTS_INT} ч\n\n"
        f"📦 Дневной пакет: {'✅' if settings.daily_package_enabled else '❌'} скидка {settings.daily_package_discount}%\n"
        f"📦 Недельный пакет: {'✅' if settings.weekly_package_enabled else '❌'} скидка {settings.weekly_package_discount}%\n"
        f"🔄 Подписка: {'✅' if settings.subscription_enabled else '❌'} {settings.subscription_min_days}–{settings.subscription_max_days} дней\n\n"
        f"{'🤖' if settings.auto_accept_enabled else '👁'} Авто-принятие: {'включено' if settings.auto_accept_enabled else 'выключено'}"
    )

    # Формируем клавиатуру
    kb_builder = InlineKeyboardBuilder()

    kb_builder.button(
        text="💰 Цена за пост",
        callback_data=f"ch_cfg:price:{channel_id}",
    )
    kb_builder.button(
        text="🕐 Расписание",
        callback_data=f"ch_cfg:schedule:{channel_id}",
    )
    kb_builder.button(
        text="📦 Пакеты",
        callback_data=f"ch_cfg:packages:{channel_id}",
    )
    kb_builder.button(
        text="📅 Подписка",
        callback_data=f"ch_cfg:subscription:{channel_id}",
    )

    auto_text = "👁 Выключить" if settings.auto_accept_enabled else "🤖 Включить"
    kb_builder.button(
        text=f"Авто-принятие: {auto_text}",
        callback_data=f"ch_cfg:auto_accept:{channel_id}",
    )

    kb_builder.button(
        text="◀️ Назад",
        callback_data=f"channel_menu:{channel_id}",
    )

    kb_builder.adjust(2, 2, 1)

    await safe_callback_edit(
        callback.message,
        text,
        reply_markup=kb_builder.as_markup(),
    )
    await callback.answer()


async def check_channel_owner(callback: CallbackQuery, channel_id: int) -> bool:
    """
    Проверить что пользователь — владелец канала.

    Args:
        callback: Callback query.
        channel_id: ID канала.

    Returns:
        True если владелец, False иначе.
    """
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return False

    async with async_session_factory() as session:
        channel = await session.get(TelegramChat, channel_id)
        if not channel or channel.owner_user_id != callback.from_user.id:
            await callback.answer("❌ Доступ запрещён", show_alert=True)
            return False
    return True


# =============================================================================
# H1: ГЛАВНОЕ МЕНЮ НАСТРОЕК
# =============================================================================


@router.callback_query(F.data.startswith("ch_cfg:view:"))
async def handle_view_settings(callback: CallbackQuery) -> None:
    """H1 — главное меню настроек ChannelSettings."""
    if not await check_channel_owner(callback, int(callback.data.split(":")[2])):
        return

    channel_id = int(callback.data.split(":")[2])

    async with async_session_factory() as session:
        repo = ChannelSettingsRepo(session)
        settings = await repo.get_or_create_default(channel_id, callback.from_user.id)

    await show_channel_cfg_menu(callback, channel_id, settings)


# =============================================================================
# H2: ИЗМЕНИТЬ ЦЕНУ
# =============================================================================


@router.callback_query(F.data.startswith("ch_cfg:price:"))
async def handle_edit_price(callback: CallbackQuery, state: FSMContext) -> None:
    """H2 — изменить цену за пост."""
    if not await check_channel_owner(callback, int(callback.data.split(":")[2])):
        return

    channel_id = int(callback.data.split(":")[2])

    async with async_session_factory() as session:
        repo = ChannelSettingsRepo(session)
        settings = await repo.get_by_channel(channel_id)

    current_price = float(settings.price_per_post) if settings else 500
    owner_earnings = current_price * (1 - float(PLATFORM_COMMISSION))

    text = (
        f"💰 <b>Изменение цены за пост</b>\n\n"
        f"Текущая цена: {current_price:.0f} ₽\n"
        f"Вы получаете: {owner_earnings:.0f} ₽ (80%)\n"
        f"Комиссия платформы: {current_price - owner_earnings:.0f} ₽ (20%)\n\n"
        f"Минимальная цена: {MIN_PRICE_PER_POST_INT} ₽\n\n"
        f"Введите новую цену в кредитах:"
    )

    kb = InlineKeyboardBuilder()
    kb.button(text="◀️ Назад", callback_data=f"ch_cfg:view:{channel_id}")
    kb.adjust(1)

    await state.update_data(channel_id=channel_id)
    await state.set_state(ChannelSettingsStates.waiting_price_per_post)

    await safe_callback_edit(
        callback.message,
        text,
        reply_markup=kb.as_markup(),
    )
    await callback.answer()


@router.message(ChannelSettingsStates.waiting_price_per_post)
async def process_price_input(message: Message, state: FSMContext) -> None:
    """H2a — обработка ввода цены."""
    if message.text is None:
        await message.answer("❌ Введите числовое значение.")
        return

    text = message.text.strip()

    if not text.isdigit():
        await message.answer("❌ Цена должна быть числом. Введите целое число.")
        return

    new_price = int(text)

    if new_price < MIN_PRICE_PER_POST_INT:
        await message.answer(
            f"❌ Минимальная цена: {MIN_PRICE_PER_POST_INT} ₽.\n"
            f"Введите значение не меньше {MIN_PRICE_PER_POST_INT}."
        )
        return

    data = await state.get_data()
    channel_id = data.get("channel_id")

    if not channel_id:
        await message.answer("❌ Ошибка сессии. Попробуйте ещё раз.")
        await state.clear()
        return

    async with async_session_factory() as session:
        repo = ChannelSettingsRepo(session)
        await repo.upsert(
            channel_id=channel_id,
            owner_id=message.from_user.id,
            price_per_post=Decimal(str(new_price)),
        )
        await session.commit()

    owner_earnings = new_price * (1 - float(PLATFORM_COMMISSION))

    text = (
        f"✅ <b>Цена обновлена!</b>\n\n"
        f"Новая цена: {new_price} ₽\n"
        f"Вы получаете: {owner_earnings:.0f} ₽ (80%)\n"
        f"Комиссия платформы: {new_price - owner_earnings:.0f} ₽ (20%)"
    )

    kb = InlineKeyboardBuilder()
    kb.button(text="⚙️ Настройки", callback_data=f"ch_cfg:view:{channel_id}")
    kb.button(text="📺 Мои каналы", callback_data="main:my_channels")
    kb.adjust(1)

    await message.answer(text, reply_markup=kb.as_markup())
    await state.clear()


# =============================================================================
# H3: РАСПИСАНИЕ ПУБЛИКАЦИЙ
# =============================================================================


@router.callback_query(F.data.startswith("ch_cfg:schedule:"))
async def handle_edit_schedule(callback: CallbackQuery, state: FSMContext) -> None:
    """H3 — настройки расписания публикаций."""
    if not await check_channel_owner(callback, int(callback.data.split(":")[2])):
        return

    channel_id = int(callback.data.split(":")[2])

    async with async_session_factory() as session:
        repo = ChannelSettingsRepo(session)
        settings = await repo.get_by_channel(channel_id)

    start_time = time_to_str(settings.publish_start_time) if settings else "09:00"
    end_time = time_to_str(settings.publish_end_time) if settings else "21:00"
    break_start = time_to_str(settings.break_start_time) if settings else "—"
    break_end = time_to_str(settings.break_end_time) if settings else "—"

    text = (
        f"🕐 <b>Настройки расписания</b>\n\n"
        f"Текущие значения:\n"
        f"• Начало публикаций: {start_time}\n"
        f"• Конец публикаций: {end_time}\n"
        f"• Перерыв: {break_start} – {break_end}\n\n"
        f"Введите время начала публикаций в формате HH:MM (например, 09:00):"
    )

    kb = InlineKeyboardBuilder()
    kb.button(text="◀️ Назад", callback_data=f"ch_cfg:view:{channel_id}")
    kb.adjust(1)

    await state.update_data(
        channel_id=channel_id,
        current_start=start_time,
        current_end=end_time,
    )
    await state.set_state(ChannelSettingsStates.waiting_start_time)

    await safe_callback_edit(
        callback.message,
        text,
        reply_markup=kb.as_markup(),
    )
    await callback.answer()


@router.message(ChannelSettingsStates.waiting_start_time)
async def process_start_time(message: Message, state: FSMContext) -> None:
    """H3a — обработка времени начала."""
    if message.text is None:
        await message.answer("❌ Введите время в формате HH:MM.")
        return

    start_time = parse_time(message.text.strip())

    if start_time is None:
        await message.answer("❌ Неверный формат. Используйте HH:MM (например, 09:00).")
        return

    await state.update_data(start_time=message.text.strip())
    await state.set_state(ChannelSettingsStates.waiting_end_time)

    await message.answer(
        "✅ Время начала принято.\n\n"
        "Введите время окончания публикаций в формате HH:MM:"
    )


@router.message(ChannelSettingsStates.waiting_end_time)
async def process_end_time(message: Message, state: FSMContext) -> None:
    """H3b — обработка времени окончания."""
    if message.text is None:
        await message.answer("❌ Введите время в формате HH:MM.")
        return

    end_time = parse_time(message.text.strip())

    if end_time is None:
        await message.answer("❌ Неверный формат. Используйте HH:MM (например, 21:00).")
        return

    data = await state.get_data()
    start_time_str = data.get("start_time")
    start_time = parse_time(start_time_str) if start_time_str else None

    if start_time and end_time <= start_time:
        await message.answer(
            "❌ Время окончания должно быть позже времени начала.\n"
            f"Время начала: {start_time_str}\n"
            "Введите корректное время окончания:"
        )
        return

    await state.update_data(end_time=message.text.strip())
    await state.set_state(ChannelSettingsStates.waiting_break_start)

    await message.answer(
        "✅ Время окончания принято.\n\n"
        "Введите начало перерыва в формате HH:MM или /skip чтобы пропустить:"
    )


@router.message(ChannelSettingsStates.waiting_break_start)
async def process_break_start(message: Message, state: FSMContext) -> None:
    """H3c — обработка начала перерыва."""
    if message.text is None:
        await message.answer("❌ Введите время в формате HH:MM или /skip.")
        return

    text = message.text.strip()

    if text.lower() == "/skip":
        # Пропускаем оба break
        await state.update_data(break_start=None, break_end=None)
        await _save_schedule_and_finish(message, state)
        return

    break_start = parse_time(text)

    if break_start is None:
        await message.answer("❌ Неверный формат. Используйте HH:MM или /skip.")
        return

    data = await state.get_data()
    start_time_str = data.get("start_time")
    end_time_str = data.get("end_time")
    start_time = parse_time(start_time_str) if start_time_str else None
    end_time = parse_time(end_time_str) if end_time_str else None

    if start_time and end_time and (break_start < start_time or break_start >= end_time):
        await message.answer(
            f"❌ Перерыв должен быть между {start_time_str} и {end_time_str}.\n"
            "Введите корректное время или /skip:"
        )
        return

    await state.update_data(break_start=text)
    await state.set_state(ChannelSettingsStates.waiting_break_end)

    await message.answer(
        "✅ Начало перерыва принято.\n\n"
        "Введите конец перерыва в формате HH:MM:"
    )


@router.message(ChannelSettingsStates.waiting_break_end)
async def process_break_end(message: Message, state: FSMContext) -> None:
    """H3d — обработка конца перерыва."""
    if message.text is None:
        await message.answer("❌ Введите время в формате HH:MM.")
        return

    break_end = parse_time(message.text.strip())

    if break_end is None:
        await message.answer("❌ Неверный формат. Используйте HH:MM.")
        return

    data = await state.get_data()
    break_start_str = data.get("break_start")
    break_start = parse_time(break_start_str) if break_start_str else None

    if break_start and break_end <= break_start:
        await message.answer(
            "❌ Конец перерыва должен быть позже начала.\n"
            f"Начало перерыва: {break_start_str}\n"
            "Введите корректное время:"
        )
        return

    await state.update_data(break_end=message.text.strip())
    await _save_schedule_and_finish(message, state)


async def _save_schedule_and_finish(message: Message, state: FSMContext) -> None:
    """Сохранить все 4 поля расписания и завершить FSM."""
    data = await state.get_data()
    channel_id = data.get("channel_id")

    if not channel_id:
        await message.answer("❌ Ошибка сессии. Попробуйте ещё раз.")
        await state.clear()
        return

    start_time = parse_time(data.get("start_time", "09:00"))
    end_time = parse_time(data.get("end_time", "21:00"))
    break_start = parse_time(data.get("break_start")) if data.get("break_start") else None
    break_end = parse_time(data.get("break_end")) if data.get("break_end") else None

    async with async_session_factory() as session:
        repo = ChannelSettingsRepo(session)
        await repo.upsert(
            channel_id=channel_id,
            owner_id=message.from_user.id,
            publish_start_time=start_time,
            publish_end_time=end_time,
            break_start_time=break_start,
            break_end_time=break_end,
        )
        await session.commit()

    text = (
        f"✅ <b>Расписание обновлено!</b>\n\n"
        f"Публикации: {time_to_str(start_time)} – {time_to_str(end_time)}\n"
        f"Перерыв: {time_to_str(break_start)} – {time_to_str(break_end)}"
    )

    kb = InlineKeyboardBuilder()
    kb.button(text="⚙️ Настройки", callback_data=f"ch_cfg:view:{channel_id}")
    kb.button(text="📺 Мои каналы", callback_data="main:my_channels")
    kb.adjust(1)

    await message.answer(text, reply_markup=kb.as_markup())
    await state.clear()


# =============================================================================
# H4: ПАКЕТЫ
# =============================================================================


@router.callback_query(F.data.startswith("ch_cfg:packages:"))
async def handle_packages_menu(callback: CallbackQuery) -> None:
    """H4 — меню пакетов (дневной и недельный)."""
    if not await check_channel_owner(callback, int(callback.data.split(":")[2])):
        return

    channel_id = int(callback.data.split(":")[2])

    async with async_session_factory() as session:
        repo = ChannelSettingsRepo(session)
        settings = await repo.get_by_channel(channel_id)

    if not settings:
        await callback.answer("❌ Настройки не найдены", show_alert=True)
        return

    text = (
        f"📦 <b>Настройки пакетов</b>\n\n"
        f"📅 Дневной пакет:\n"
        f"• Статус: {'✅ Включён' if settings.daily_package_enabled else '❌ Выключен'}\n"
        f"• Скидка: {settings.daily_package_discount}%\n"
        f"• Макс. постов/день: {settings.daily_package_max}\n\n"
        f"📅 Недельный пакет:\n"
        f"• Статус: {'✅ Включён' if settings.weekly_package_enabled else '❌ Выключен'}\n"
        f"• Скидка: {settings.weekly_package_discount}%\n"
        f"• Макс. постов/неделю: {settings.weekly_package_max}\n\n"
        f"⏱ Мин. часов между постами: {MIN_HOURS_BETWEEN_POSTS_INT}"
    )

    kb = InlineKeyboardBuilder()

    # Дневной пакет
    daily_toggle_text = "❌ Выключить" if settings.daily_package_enabled else "✅ Включить"
    kb.button(
        text=f"Дневной пакет: {daily_toggle_text}",
        callback_data=f"ch_cfg:pkg_daily_toggle:{channel_id}",
    )
    kb.button(
        text=f"Скидка дня: {settings.daily_package_discount}%",
        callback_data=f"ch_cfg:pkg_daily_discount:{channel_id}",
    )

    # Недельный пакет
    weekly_toggle_text = "❌ Выключить" if settings.weekly_package_enabled else "✅ Включить"
    kb.button(
        text=f"Недельный пакет: {weekly_toggle_text}",
        callback_data=f"ch_cfg:pkg_weekly_toggle:{channel_id}",
    )
    kb.button(
        text=f"Скидка недели: {settings.weekly_package_discount}%",
        callback_data=f"ch_cfg:pkg_weekly_discount:{channel_id}",
    )

    # Лимиты постов
    kb.button(
        text=f"Лимит постов/день: {settings.daily_package_max}",
        callback_data=f"ch_cfg:max_posts:{channel_id}",
    )

    kb.button(
        text="◀️ Назад",
        callback_data=f"ch_cfg:view:{channel_id}",
    )

    kb.adjust(2, 2, 1)

    await safe_callback_edit(
        callback.message,
        text,
        reply_markup=kb.as_markup(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("ch_cfg:pkg_daily_toggle:"))
async def handle_daily_toggle(callback: CallbackQuery) -> None:
    """H4a — toggle дневного пакета."""
    if not await check_channel_owner(callback, int(callback.data.split(":")[3])):
        return

    channel_id = int(callback.data.split(":")[3])

    async with async_session_factory() as session:
        repo = ChannelSettingsRepo(session)
        settings = await repo.get_by_channel(channel_id)
        if not settings:
            await callback.answer("❌ Настройки не найдены", show_alert=True)
            return

        new_val = not settings.daily_package_enabled
        await repo.upsert(
            channel_id=channel_id,
            owner_id=callback.from_user.id,
            daily_package_enabled=new_val,
        )
        await session.commit()

    await callback.answer(
        f"📦 Дневной пакет {'включён' if new_val else 'выключен'}",
        show_alert=False,
    )

    # Перерисовать меню
    settings.daily_package_enabled = new_val
    await handle_packages_menu(callback)


@router.callback_query(F.data.startswith("ch_cfg:pkg_weekly_toggle:"))
async def handle_weekly_toggle(callback: CallbackQuery) -> None:
    """H4a — toggle недельного пакета."""
    if not await check_channel_owner(callback, int(callback.data.split(":")[3])):
        return

    channel_id = int(callback.data.split(":")[3])

    async with async_session_factory() as session:
        repo = ChannelSettingsRepo(session)
        settings = await repo.get_by_channel(channel_id)
        if not settings:
            await callback.answer("❌ Настройки не найдены", show_alert=True)
            return

        new_val = not settings.weekly_package_enabled
        await repo.upsert(
            channel_id=channel_id,
            owner_id=callback.from_user.id,
            weekly_package_enabled=new_val,
        )
        await session.commit()

    await callback.answer(
        f"📦 Недельный пакет {'включён' if new_val else 'выключен'}",
        show_alert=False,
    )

    # Перерисовать меню
    settings.weekly_package_enabled = new_val
    await handle_packages_menu(callback)


@router.callback_query(F.data.startswith("ch_cfg:max_posts:"))
async def handle_max_posts(callback: CallbackQuery) -> None:
    """H4a — выбор лимита постов в день."""
    if not await check_channel_owner(callback, int(callback.data.split(":")[3])):
        return

    channel_id = int(callback.data.split(":")[3])

    # Циклическое переключение: 2 → 3 → 5 → 1 → 2
    limits = [1, 2, 3, 5]

    async with async_session_factory() as session:
        repo = ChannelSettingsRepo(session)
        settings = await repo.get_by_channel(channel_id)
        if not settings:
            await callback.answer("❌ Настройки не найдены", show_alert=True)
            return

        current = settings.daily_package_max
        try:
            idx = limits.index(current)
            new_val = limits[(idx + 1) % len(limits)]
        except ValueError:
            new_val = 2

        await repo.upsert(
            channel_id=channel_id,
            owner_id=callback.from_user.id,
            daily_package_max=new_val,
        )
        await session.commit()

    await callback.answer(f"📅 Лимит постов/день: {new_val}", show_alert=False)

    # Перерисовать меню
    settings.daily_package_max = new_val
    await handle_packages_menu(callback)


@router.callback_query(F.data.startswith("ch_cfg:pkg_daily_discount:"))
async def handle_daily_discount(callback: CallbackQuery, state: FSMContext) -> None:
    """H4 — изменить скидку дневного пакета (FSM)."""
    if not await check_channel_owner(callback, int(callback.data.split(":")[3])):
        return

    channel_id = int(callback.data.split(":")[3])

    text = (
        f"📦 <b>Скидка дневного пакета</b>\n\n"
        f"Введите скидку в процентах (1–{MAX_PACKAGE_DISCOUNT}%):"
    )

    kb = InlineKeyboardBuilder()
    kb.button(text="◀️ Назад", callback_data=f"ch_cfg:packages:{channel_id}")
    kb.adjust(1)

    await state.update_data(channel_id=channel_id, discount_type="daily")
    await state.set_state(ChannelSettingsStates.waiting_daily_discount)

    await safe_callback_edit(
        callback.message,
        text,
        reply_markup=kb.as_markup(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("ch_cfg:pkg_weekly_discount:"))
async def handle_weekly_discount(callback: CallbackQuery, state: FSMContext) -> None:
    """H4 — изменить скидку недельного пакета (FSM)."""
    if not await check_channel_owner(callback, int(callback.data.split(":")[3])):
        return

    channel_id = int(callback.data.split(":")[3])

    text = (
        f"📦 <b>Скидка недельного пакета</b>\n\n"
        f"Введите скидку в процентах (1–{MAX_PACKAGE_DISCOUNT}%):"
    )

    kb = InlineKeyboardBuilder()
    kb.button(text="◀️ Назад", callback_data=f"ch_cfg:packages:{channel_id}")
    kb.adjust(1)

    await state.update_data(channel_id=channel_id, discount_type="weekly")
    await state.set_state(ChannelSettingsStates.waiting_weekly_discount)

    await safe_callback_edit(
        callback.message,
        text,
        reply_markup=kb.as_markup(),
    )
    await callback.answer()


@router.message(ChannelSettingsStates.waiting_daily_discount)
@router.message(ChannelSettingsStates.waiting_weekly_discount)
async def process_discount_input(message: Message, state: FSMContext) -> None:
    """Обработка ввода скидки пакета."""
    if message.text is None:
        await message.answer("❌ Введите число от 1 до 50.")
        return

    text = message.text.strip()

    if not text.isdigit():
        await message.answer("❌ Скидка должна быть числом.")
        return

    discount = int(text)

    if discount < 1 or discount > MAX_PACKAGE_DISCOUNT:
        await message.answer(f"❌ Скидка должна быть от 1 до {MAX_PACKAGE_DISCOUNT}%.")
        return

    data = await state.get_data()
    channel_id = data.get("channel_id")
    discount_type = data.get("discount_type")

    if not channel_id or not discount_type:
        await message.answer("❌ Ошибка сессии. Попробуйте ещё раз.")
        await state.clear()
        return

    async with async_session_factory() as session:
        repo = ChannelSettingsRepo(session)
        if discount_type == "daily":
            await repo.upsert(
                channel_id=channel_id,
                owner_id=message.from_user.id,
                daily_package_discount=discount,
            )
            pkg_name = "Дневного"
        else:
            await repo.upsert(
                channel_id=channel_id,
                owner_id=message.from_user.id,
                weekly_package_discount=discount,
            )
            pkg_name = "Недельного"
        await session.commit()

    text_response = f"✅ <b>Скидка обновлена!</b>\n\n{pkg_name} пакета: {discount}%"

    kb = InlineKeyboardBuilder()
    kb.button(text="📦 Пакеты", callback_data=f"ch_cfg:packages:{channel_id}")
    kb.button(text="⚙️ Настройки", callback_data=f"ch_cfg:view:{channel_id}")
    kb.adjust(1)

    await message.answer(text_response, reply_markup=kb.as_markup())
    await state.clear()


# =============================================================================
# H5: ПОДПИСКА
# =============================================================================


@router.callback_query(F.data.startswith("ch_cfg:subscription:"))
async def handle_subscription_menu(callback: CallbackQuery) -> None:
    """H5 — настройки подписки."""
    if not await check_channel_owner(callback, int(callback.data.split(":")[2])):
        return

    channel_id = int(callback.data.split(":")[2])

    async with async_session_factory() as session:
        repo = ChannelSettingsRepo(session)
        settings = await repo.get_by_channel(channel_id)

    if not settings:
        await callback.answer("❌ Настройки не найдены", show_alert=True)
        return

    status = "✅ Включена" if settings.subscription_enabled else "❌ Выключена"

    text = (
        f"🔄 <b>Настройки подписки</b>\n\n"
        f"Статус: {status}\n"
        f"Мин. срок: {settings.subscription_min_days} дней\n"
        f"Макс. срок: {settings.subscription_max_days} дней\n"
        f"Макс. постов/день: {settings.subscription_max_per_day}"
    )

    kb = InlineKeyboardBuilder()

    toggle_text = "❌ Выключить" if settings.subscription_enabled else "✅ Включить"
    kb.button(
        text=f"Подписка: {toggle_text}",
        callback_data=f"ch_cfg:sub_toggle:{channel_id}",
    )
    kb.button(
        text=f"Мин. дней: {settings.subscription_min_days}",
        callback_data=f"ch_cfg:sub_min:{channel_id}",
    )
    kb.button(
        text=f"Макс. дней: {settings.subscription_max_days}",
        callback_data=f"ch_cfg:sub_max:{channel_id}",
    )
    kb.button(
        text="◀️ Назад",
        callback_data=f"ch_cfg:view:{channel_id}",
    )

    kb.adjust(2, 2)

    await safe_callback_edit(
        callback.message,
        text,
        reply_markup=kb.as_markup(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("ch_cfg:sub_toggle:"))
async def handle_sub_toggle(callback: CallbackQuery) -> None:
    """H5 — toggle подписки."""
    if not await check_channel_owner(callback, int(callback.data.split(":")[3])):
        return

    channel_id = int(callback.data.split(":")[3])

    async with async_session_factory() as session:
        repo = ChannelSettingsRepo(session)
        settings = await repo.get_by_channel(channel_id)
        if not settings:
            await callback.answer("❌ Настройки не найдены", show_alert=True)
            return

        new_val = not settings.subscription_enabled
        await repo.upsert(
            channel_id=channel_id,
            owner_id=callback.from_user.id,
            subscription_enabled=new_val,
        )
        await session.commit()

    await callback.answer(
        f"🔄 Подписка {'включена' if new_val else 'выключена'}",
        show_alert=False,
    )

    # Перерисовать меню
    settings.subscription_enabled = new_val
    await handle_subscription_menu(callback)


@router.callback_query(F.data.startswith("ch_cfg:sub_min:"))
async def handle_sub_min(callback: CallbackQuery, state: FSMContext) -> None:
    """H5 — изменить мин. дней подписки (FSM)."""
    if not await check_channel_owner(callback, int(callback.data.split(":")[3])):
        return

    channel_id = int(callback.data.split(":")[3])

    text = (
        f"🔄 <b>Минимальный срок подписки</b>\n\n"
        f"Введите количество дней ({MIN_SUBSCRIPTION_DAYS}–{MAX_SUBSCRIPTION_DAYS}):"
    )

    kb = InlineKeyboardBuilder()
    kb.button(text="◀️ Назад", callback_data=f"ch_cfg:subscription:{channel_id}")
    kb.adjust(1)

    await state.update_data(channel_id=channel_id, sub_field="min")
    await state.set_state(ChannelSettingsStates.waiting_sub_min_days)

    await safe_callback_edit(
        callback.message,
        text,
        reply_markup=kb.as_markup(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("ch_cfg:sub_max:"))
async def handle_sub_max(callback: CallbackQuery, state: FSMContext) -> None:
    """H5 — изменить макс. дней подписки (FSM)."""
    if not await check_channel_owner(callback, int(callback.data.split(":")[3])):
        return

    channel_id = int(callback.data.split(":")[3])

    text = (
        f"🔄 <b>Максимальный срок подписки</b>\n\n"
        f"Введите количество дней ({MIN_SUBSCRIPTION_DAYS}–{MAX_SUBSCRIPTION_DAYS}):"
    )

    kb = InlineKeyboardBuilder()
    kb.button(text="◀️ Назад", callback_data=f"ch_cfg:subscription:{channel_id}")
    kb.adjust(1)

    await state.update_data(channel_id=channel_id, sub_field="max")
    await state.set_state(ChannelSettingsStates.waiting_sub_max_days)

    await safe_callback_edit(
        callback.message,
        text,
        reply_markup=kb.as_markup(),
    )
    await callback.answer()


@router.message(ChannelSettingsStates.waiting_sub_min_days)
@router.message(ChannelSettingsStates.waiting_sub_max_days)
async def process_sub_days_input(message: Message, state: FSMContext) -> None:
    """Обработка ввода дней подписки."""
    if message.text is None:
        await message.answer("❌ Введите число.")
        return

    text = message.text.strip()

    if not text.isdigit():
        await message.answer("❌ Введите целое число.")
        return

    days = int(text)

    if days < MIN_SUBSCRIPTION_DAYS or days > MAX_SUBSCRIPTION_DAYS:
        await message.answer(
            f"❌ Значение должно быть от {MIN_SUBSCRIPTION_DAYS} до {MAX_SUBSCRIPTION_DAYS}."
        )
        return

    data = await state.get_data()
    channel_id = data.get("channel_id")
    sub_field = data.get("sub_field")

    if not channel_id or not sub_field:
        await message.answer("❌ Ошибка сессии. Попробуйте ещё раз.")
        await state.clear()
        return

    # Проверка что max > min
    async with async_session_factory() as session:
        repo = ChannelSettingsRepo(session)
        settings = await repo.get_by_channel(channel_id)

        if not settings:
            await message.answer("❌ Настройки не найдены.")
            await state.clear()
            return

        if sub_field == "max" and days <= settings.subscription_min_days:
            await message.answer(
                f"❌ Максимум должен быть больше минимума ({settings.subscription_min_days} дней)."
            )
            return

        if sub_field == "min" and days >= settings.subscription_max_days:
            await message.answer(
                f"❌ Минимум должен быть меньше максимума ({settings.subscription_max_days} дней)."
            )
            return

        if sub_field == "min":
            await repo.upsert(
                channel_id=channel_id,
                owner_id=message.from_user.id,
                subscription_min_days=days,
            )
            field_name = "Минимальный"
        else:
            await repo.upsert(
                channel_id=channel_id,
                owner_id=message.from_user.id,
                subscription_max_days=days,
            )
            field_name = "Максимальный"

        await session.commit()

    text_response = f"✅ <b>{field_name} срок обновлён!</b>\n\n{days} дней"

    kb = InlineKeyboardBuilder()
    kb.button(text="🔄 Подписка", callback_data=f"ch_cfg:subscription:{channel_id}")
    kb.button(text="⚙️ Настройки", callback_data=f"ch_cfg:view:{channel_id}")
    kb.adjust(1)

    await message.answer(text_response, reply_markup=kb.as_markup())
    await state.clear()


# =============================================================================
# H6: АВТО-ПРИНЯТИЕ
# =============================================================================


@router.callback_query(F.data.startswith("ch_cfg:auto_accept:"))
async def handle_auto_accept_toggle(callback: CallbackQuery) -> None:
    """H6 — toggle авто-принятия заявок."""
    if not await check_channel_owner(callback, int(callback.data.split(":")[2])):
        return

    channel_id = int(callback.data.split(":")[2])

    async with async_session_factory() as session:
        repo = ChannelSettingsRepo(session)
        settings = await repo.get_by_channel(channel_id)
        if not settings:
            await callback.answer("❌ Настройки не найдены", show_alert=True)
            return

        new_val = not settings.auto_accept_enabled
        await repo.upsert(
            channel_id=channel_id,
            owner_id=callback.from_user.id,
            auto_accept_enabled=new_val,
        )
        await session.commit()

    answer_text = (
        "🤖 Авто-принятие включено\n"
        "Заявки будут приниматься автоматически."
        if new_val
        else "👁 Ручной режим включён\n"
        "Вы будете вручную проверять каждую заявку."
    )

    await callback.answer(answer_text, show_alert=True)

    # Перерисовать главное меню
    settings.auto_accept_enabled = new_val
    await show_channel_cfg_menu(callback, channel_id, settings)
