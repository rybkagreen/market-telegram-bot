"""
Handler для базы каналов — статистика, поиск по категориям, подкатегории.
Аналог Mini App страницы Channels.
"""

import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.bot.keyboards.channels import (
    ChannelsCB,
    get_categories_kb,
    get_channels_menu_kb,
    get_tariff_filter_kb,
)
from src.bot.keyboards.main_menu import MainMenuCB
from src.db.session import async_session_factory
from src.services import get_user_service
from src.utils.categories import SUBCATEGORIES

logger = logging.getLogger(__name__)

router = Router()


@router.callback_query(MainMenuCB.filter(F.action == "channels_db"))
async def show_channels_menu(callback: CallbackQuery) -> None:
    """Показать главное меню базы каналов."""
    text = (
        "📡 <b>База каналов Telegram</b>\n\n"
        "Выберите раздел:\n\n"
        "📊 Статистика базы — общая статистика по всем каналам\n"
        "🔍 Поиск по категориям — фильтрация по тематикам\n"
        "📡 Топ каналов — крупнейшие каналы по подписчикам"
    )

    await callback.message.edit_text(
        text,
        reply_markup=get_channels_menu_kb(),
    )


@router.callback_query(ChannelsCB.filter(F.action == "stats"))
async def handle_channels_stats(callback: CallbackQuery) -> None:
    """
    Показать общую статистику базы каналов.
    Аналог GET /api/channels/stats
    """
    async with get_user_service() as svc:
        user = await svc._user_repo.get_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        plan_str = user.plan.value if hasattr(user.plan, "value") else str(user.plan)

        # Получаем статистику из БД
        async with async_session_factory() as session:
            from sqlalchemy import func, select, true

            from src.db.models.analytics import TelegramChat

            # Всего каналов
            total_result = await session.execute(
                select(func.count(TelegramChat.id)).where(TelegramChat.is_active == true())
            )
            total = total_result.scalar() or 0

            # По категориям
            cat_result = await session.execute(
                select(
                    TelegramChat.topic.label("topic"),
                    func.count(TelegramChat.id).label("total"),
                )
                .where(TelegramChat.is_active == true())
                .group_by(TelegramChat.topic)
                .order_by(func.count(TelegramChat.id).desc())
            )
            categories = cat_result.all()

        # Формируем текст
        text = "📊 <b>Статистика базы каналов</b>\n\n"
        text += f"📡 <b>Всего каналов:</b> {total:,}\n\n"
        text += "<b>По категориям:</b>\n"

        for cat in categories[:10]:  # Топ-10 категорий
            if cat.topic:
                text += f"• {cat.topic}: {cat.total:,}\n"

        # Статистика по тарифам
        text += f"\n<b>Доступно на вашем тарифе ({plan_str.upper()}):</b>\n"

        tariff_limits = {
            "free": 10_000,
            "starter": 50_000,
            "pro": 200_000,
            "business": -1,
        }

        limit = tariff_limits.get(plan_str, -1)
        if limit == -1:
            text += f"✅ Все {total:,} каналов"
        else:
            async with async_session_factory() as session:
                avail_result = await session.execute(
                    select(func.count(TelegramChat.id))
                    .where(
                        TelegramChat.is_active == true(),
                        TelegramChat.member_count <= limit,
                    )
                )
                available = avail_result.scalar() or 0
            text += f"✅ {available:,} из {total:,} каналов"

        builder = InlineKeyboardBuilder()
        builder.button(
            text="🔍 Поиск по категориям",
            callback_data=ChannelsCB(action="categories"),
        )
        builder.button(
            text="🔙 В меню базы",
            callback_data=ChannelsCB(action="menu"),
        )
        builder.button(
            text="🔙 В главное меню",
            callback_data=MainMenuCB(action="main_menu"),
        )
        builder.adjust(1, 1, 1)

        await callback.message.edit_text(
            text,
            reply_markup=builder.as_markup(),
        )


@router.callback_query(ChannelsCB.filter(F.action == "categories"))
async def handle_categories(callback: CallbackQuery) -> None:
    """Показать список категорий для фильтрации."""
    text = (
        "🔍 <b>Выберите категорию</b>\n\n"
        "Фильтрация каналов по тематике:\n"
    )

    await callback.message.edit_text(
        text,
        reply_markup=get_categories_kb(),
    )


@router.callback_query(ChannelsCB.filter(F.action == "category"))
async def handle_category_detail(callback: CallbackQuery, callback_data: ChannelsCB) -> None:
    """
    Показать детальную информацию по категории.

    callback_data.value: название категории (например, "it", "бизнес")
    """
    category = callback_data.value

    async with async_session_factory() as session:
        from sqlalchemy import func, select, true

        from src.db.models.analytics import TelegramChat

        # Всего в категории (case-insensitive comparison)
        total_result = await session.execute(
            select(func.count(TelegramChat.id))
            .where(
                TelegramChat.is_active == true(),
                func.lower(TelegramChat.topic) == category.lower(),
            )
        )
        total = total_result.scalar() or 0

        # Топ-3 канала
        top_result = await session.execute(
            select(
                TelegramChat.username,
                TelegramChat.title,
                TelegramChat.member_count,
            )
            .where(
                TelegramChat.is_active == true(),
                func.lower(TelegramChat.topic) == category.lower(),
            )
            .order_by(TelegramChat.member_count.desc())
            .limit(3)
        )
        top_channels = top_result.all()

    # Проверяем подкатегории
    has_subcats = category in SUBCATEGORIES

    text = f"📁 <b>Категория: {category}</b>\n\n"
    text += f"📡 Каналов: <b>{total:,}</b>\n\n"

    if top_channels:
        text += "<b>Крупнейшие каналы:</b>\n"
        for i, ch in enumerate(top_channels, 1):
            # ch is a tuple: (username, title, member_count)
            username = ch[0] or "—"
            title = ch[1] or "Без названия"
            subs = f"{ch[2]:,}" if ch[2] else "—"
            text += f"{i}. <a href='https://t.me/{username}'>{title}</a> — {subs}\n"

    if has_subcats:
        subcats = SUBCATEGORIES[category]
        text += f"\n<b>Подкатегории ({len(subcats)}):</b>\n"
        for _code, name in list(subcats.items())[:5]:
            text += f"• {name}\n"
        if len(subcats) > 5:
            text += f"... и ещё {len(subcats) - 5}\n"

    builder = InlineKeyboardBuilder()

    if has_subcats:
        builder.button(
            text="📊 Подкатегории",
            callback_data=ChannelsCB(action="subcategories", value=category),
        )

    builder.button(
        text="🎯 Фильтр по тарифу",
        callback_data=ChannelsCB(action="tariff", value=category),
    )
    builder.button(
        text="🔙 Назад",
        callback_data=ChannelsCB(action="categories"),
    )
    builder.button(
        text="🔙 В меню базы",
        callback_data=ChannelsCB(action="menu"),
    )
    builder.adjust(1, 1, 1)

    await callback.message.edit_text(
        text,
        reply_markup=builder.as_markup(),
    )


@router.callback_query(ChannelsCB.filter(F.action == "subcategories"))
async def handle_subcategories(callback: CallbackQuery, callback_data: ChannelsCB) -> None:
    """
    Показать подкатегории для выбранной категории.

    callback_data.value: название родительской категории
    """
    topic = callback_data.value

    subcats = SUBCATEGORIES.get(topic, {})

    if not subcats:
        text = f"❌ Для категории <b>{topic}</b> нет подкатегорий"
        builder = InlineKeyboardBuilder()
        builder.button(
            text="🔙 Назад",
            callback_data=ChannelsCB(action="categories"),
        )
        builder.adjust(1)
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
        return

    text = f"📊 <b>Подкатегории: {topic}</b>\n\n"

    # Получаем статистику по подкатегориям
    async with async_session_factory() as session:
        from sqlalchemy import func, select, true

        from src.db.models.analytics import TelegramChat

        result = await session.execute(
            select(
                TelegramChat.subcategory.label("subcat"),
                func.count(TelegramChat.id).label("total"),
            )
            .where(
                TelegramChat.is_active == true(),
                func.lower(TelegramChat.topic) == topic.lower(),
                TelegramChat.subcategory.in_(list(subcats.keys())),
            )
            .group_by(TelegramChat.subcategory)
            .order_by(func.count(TelegramChat.id).desc())
        )
        rows = result.all()

    # Формируем список
    for row in rows:
        # row is a tuple: (subcat, total)
        subcat = row[0]
        total = row[1]
        if subcat:
            name = subcats.get(subcat, subcat)
            text += f"• {name}: <b>{total:,}</b>\n"

    if not rows:
        text += "Пока нет данных по подкатегориям.\n"

    builder = InlineKeyboardBuilder()
    builder.button(
        text="🔙 Назад",
        callback_data=ChannelsCB(action="category", value=topic),
    )
    builder.button(
        text="🔙 В меню базы",
        callback_data=ChannelsCB(action="menu"),
    )
    builder.adjust(1, 1)

    await callback.message.edit_text(
        text,
        reply_markup=builder.as_markup(),
    )


@router.callback_query(ChannelsCB.filter(F.action == "tariff"))
async def handle_tariff_filter(callback: CallbackQuery, callback_data: ChannelsCB) -> None:
    """
    Показать фильтр по тарифам для категории.

    callback_data.value: категория или категория_тариф
    """
    value = callback_data.value

    parts = value.split("_") if "_" in value else [value, ""]
    category = parts[0] if parts[0] else None

    text = "🎯 <b>Фильтр по тарифам</b>\n\n"
    if category:
        text += f"Категория: <b>{category}</b>\n\n"
    text += "Выберите тариф для фильтрации:\n"

    await callback.message.edit_text(
        text,
        reply_markup=get_tariff_filter_kb(category),
    )


@router.callback_query(ChannelsCB.filter(F.action == "top_channels"))
async def handle_top_channels(callback: CallbackQuery) -> None:
    """Показать топ каналов по подписчикам."""
    async with async_session_factory() as session:
        from sqlalchemy import select, true

        from src.db.models.analytics import TelegramChat

        result = await session.execute(
            select(
                TelegramChat.username,
                TelegramChat.title,
                TelegramChat.member_count,
                TelegramChat.topic,
            )
            .where(TelegramChat.is_active == true())
            .order_by(TelegramChat.member_count.desc())
            .limit(15)
        )
        rows = result.all()

    text = "📡 <b>Топ каналов по подписчикам</b>\n\n"

    for i, row in enumerate(rows, 1):
        username = row.username or "—"
        title = row.title or "Без названия"
        subs = f"{row.member_count:,}" if row.member_count else "—"
        topic = row.topic or "—"
        text += f"{i}. <a href='https://t.me/{username}'>{title}</a>\n"
        text += f"   👥 {subs} | 📁 {topic}\n\n"

    builder = InlineKeyboardBuilder()
    builder.button(
        text="🔙 В меню базы",
        callback_data=ChannelsCB(action="menu"),
    )
    builder.button(
        text="🔙 В главное меню",
        callback_data=MainMenuCB(action="main_menu"),
    )
    builder.adjust(1, 1)

    await callback.message.edit_text(
        text,
        reply_markup=builder.as_markup(),
    )


@router.callback_query(ChannelsCB.filter(F.action == "menu"))
async def back_to_channels_menu(callback: CallbackQuery) -> None:
    """Вернуться в главное меню базы каналов."""
    text = (
        "📡 <b>База каналов Telegram</b>\n\n"
        "Выберите раздел:\n\n"
        "📊 Статистика базы — общая статистика по всем каналам\n"
        "🔍 Поиск по категориям — фильтрация по тематикам\n"
        "📡 Топ каналов — крупнейшие каналы по подписчикам"
    )

    await callback.message.edit_text(
        text,
        reply_markup=get_channels_menu_kb(),
    )
