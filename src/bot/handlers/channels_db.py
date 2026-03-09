"""
Handler для базы каналов — статистика, поиск по категориям, подкатегории.
Аналог Mini App страницы Channels.
"""

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Импортировать router из mediakit handlers
from src.bot.handlers.channels_db_mediakit import router as mediakit_router
from src.bot.keyboards.channels import (
    ChannelsCB,
    get_categories_kb,
    get_channels_menu_kb,
    get_tariff_filter_kb,
)
from src.bot.keyboards.comparison import ComparisonCB
from src.bot.keyboards.main_menu import MainMenuCB
from src.bot.utils.message_utils import safe_edit_message
from src.bot.utils.safe_callback import safe_callback_edit
from src.db.repositories.user_repo import UserRepository
from src.db.session import async_session_factory
from src.utils.categories import SUBCATEGORIES

logger = logging.getLogger(__name__)

router = Router()
router.include_router(mediakit_router)


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

    await safe_edit_message(
        callback.message,
        text,
        reply_markup=get_channels_menu_kb(),
    )


@router.callback_query(ChannelsCB.filter(F.action == "stats"))
async def handle_channels_stats(callback: CallbackQuery) -> None:
    """
    Показать общую статистику базы каналов.
    Аналог GET /api/channels/stats
    """
    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(callback.from_user.id)
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
                    select(func.count(TelegramChat.id)).where(
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

        await safe_edit_message(
            callback.message,
            text,
            reply_markup=builder.as_markup(),
        )


@router.callback_query(ChannelsCB.filter(F.action == "categories"))
async def handle_categories(callback: CallbackQuery) -> None:
    """Показать список категорий для фильтрации."""

    text = (
        "🔍 <b>Фильтры каталога</b>\n\n"
        "Выберите режим фильтрации:\n\n"
        "📁 <b>Одиночный выбор</b> — выберите одну категорию\n"
        "✅ <b>Мультивыбор</b> — выберите несколько категорий и тарифов\n\n"
        "Мультивыбор позволяет комбинировать фильтры через AND/OR."
    )

    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    # Проверить есть ли активные фильтры
    async with async_session_factory() as session:
        from sqlalchemy import func, select, true

        from src.db.models.analytics import TelegramChat

        total_result = await session.execute(
            select(func.count(TelegramChat.id)).where(TelegramChat.is_active == true())
        )
        total = total_result.scalar() or 0

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📁 Одиночный выбор", callback_data=ChannelsCB(action="single_select").pack())],
        [InlineKeyboardButton(text="✅ Мультивыбор", callback_data=ChannelsCB(action="multi_select").pack())],
        [InlineKeyboardButton(text=f"📊 Все каналы ({total:,})", callback_data=ChannelsCB(action="stats").pack())],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=ChannelsCB(action="menu").pack())],
    ])

    await safe_edit_message(
        callback.message,
        text,
        reply_markup=keyboard,
    )


@router.callback_query(ChannelsCB.filter(F.action == "single_select"))
async def single_select(callback: CallbackQuery) -> None:
    """Одиночный выбор категории (старый режим)."""
    text = "📁 <b>Выберите категорию</b>\n\nФильтрация каналов по тематике:\n"

    await safe_edit_message(
        callback.message,
        text,
        reply_markup=get_categories_kb(),
    )


@router.callback_query(ChannelsCB.filter(F.action == "multi_select"))
async def multi_select(callback: CallbackQuery, state: FSMContext) -> None:
    """Мультивыбор категорий и тарифов."""

    # Сбросить предыдущие фильтры
    await state.update_data(
        filter_selected_categories=[],
        filter_selected_tariffs=[],
    )

    from src.bot.keyboards.channels import get_multi_select_categories_kb

    text = (
        "✅ <b>Мультивыбор фильтров</b>\n\n"
        "📁 <b>Категории:</b> выберите одну или несколько тематик\n"
        "💎 <b>Тарифы:</b> выберите один или несколько тарифов\n\n"
        "Фильтры комбинируются:\n"
        "• Внутри группы (категории) — OR\n"
        "• Между группами (категории + тарифы) — AND\n\n"
        "Выберите категорию для начала:"
    )

    await safe_edit_message(
        callback.message,
        text,
        reply_markup=get_multi_select_categories_kb(),
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
            select(func.count(TelegramChat.id)).where(
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
        top_channels = top_result.tuples().all()

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
        text="📊 Сравнить каналы",
        callback_data=ComparisonCB(action="show_bar").pack(),
    )
    builder.button(
        text="🔙 Назад",
        callback_data=ChannelsCB(action="categories"),
    )
    builder.button(
        text="🔙 В меню базы",
        callback_data=ChannelsCB(action="menu"),
    )
    builder.adjust(1, 1, 1, 1)

    await safe_edit_message(
        callback.message,
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

    # Получаем подкатегории из БД (с fallback)
    from src.utils.categories import get_subcategories_from_db
    subcats = await get_subcategories_from_db(topic)

    if not subcats:
        text = f"❌ Для категории <b>{topic}</b> нет подкатегорий"
        builder = InlineKeyboardBuilder()
        builder.button(
            text="🔙 Назад",
            callback_data=ChannelsCB(action="category", value=topic),
        )
        builder.adjust(1)
        await safe_edit_message(callback.message, text, reply_markup=builder.as_markup())
        return

    text = f"📊 <b>Подкатегории: {topic}</b>\n\n"

    # Получаем статистику по подкатегориям
    async with async_session_factory() as session:
        from sqlalchemy import func, select, true

        from src.db.models.analytics import TelegramChat

        # Каналы С подкатегорией
        result_with_subcat = await session.execute(
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
        rows_with_subcat = result_with_subcat.tuples().all()

        # Каналы БЕЗ подкатегории
        result_without_subcat = await session.execute(
            select(func.count(TelegramChat.id).label("total"))
            .where(
                TelegramChat.is_active == true(),
                func.lower(TelegramChat.topic) == topic.lower(),
                TelegramChat.subcategory == None,
            )
        )
        total_without_subcat = result_without_subcat.scalar() or 0

    # Формируем список
    for row in rows_with_subcat:
        # row is a tuple: (subcat, total)
        subcat = row[0]
        total = row[1]
        if subcat:
            name = subcats.get(subcat, subcat)
            text += f"• {name}: <b>{total:,}</b>\n"

    # Добавляем информацию о каналах без subcategory
    if total_without_subcat > 0:
        text += f"\n⚠️ <b>{total_without_subcat:,} каналов</b> без подкатегории\n"
        text += "Классификация будет добавлена в ближайшее время."

    if not rows_with_subcat and total_without_subcat == 0:
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

    await safe_edit_message(
        callback.message,
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

    await safe_edit_message(
        callback.message,
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

    await safe_edit_message(
        callback.message,
        text,
        reply_markup=builder.as_markup(),
    )


# ─────────────────────────────────────────────
# Расширенные фильтры каталога (Спринт 3)
# ─────────────────────────────────────────────

@router.callback_query(ChannelsCB.filter(F.action == "advanced_filters"))
async def handle_advanced_filters(callback: CallbackQuery) -> None:
    """
    Показать расширенные фильтры каталога.
    Спринт 3: фильтр по ER, рейтингу надёжности, fraud_flag.
    """
    text = (
        "🔧 <b>Расширенные фильтры</b>\n\n"
        "Выберите фильтр:\n\n"
        "📊 Минимальный ER — фильтрация по engagement rate\n"
        "⭐ Рейтинг надёжности — только верифицированные каналы\n"
        "🛡 Без накрутки — исключить каналы с fraud_flag"
    )

    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Мин. ER", callback_data=ChannelsCB(action="filter_er").pack())
    builder.button(text="⭐ Рейтинг", callback_data=ChannelsCB(action="filter_rating").pack())
    builder.button(text="🛡 Без накрутки", callback_data=ChannelsCB(action="filter_fraud").pack())
    builder.button(text="◀️ Назад", callback_data=ChannelsCB(action="back").pack())
    builder.adjust(2, 2)

    await safe_edit_message(
        callback.message,
        text,
        reply_markup=builder.as_markup(),
    )


@router.callback_query(ChannelsCB.filter(F.action == "filter_er"))
async def handle_filter_er(callback: CallbackQuery) -> None:
    """Фильтр по минимальному ER."""
    text = (
        "📊 <b>Фильтр по ER</b>\n\n"
        "Выберите минимальный engagement rate:\n\n"
        "• ≥ 1% — все каналы\n"
        "• ≥ 3% — хорошие каналы\n"
        "• ≥ 5% — отличные каналы\n"
        "• ≥ 10% — премиум каналы"
    )

    builder = InlineKeyboardBuilder()
    builder.button(text="≥ 1%", callback_data=ChannelsCB(action="er_1").pack())
    builder.button(text="≥ 3%", callback_data=ChannelsCB(action="er_3").pack())
    builder.button(text="≥ 5%", callback_data=ChannelsCB(action="er_5").pack())
    builder.button(text="≥ 10%", callback_data=ChannelsCB(action="er_10").pack())
    builder.button(text="◀️ Назад", callback_data=ChannelsCB(action="advanced_filters").pack())
    builder.adjust(2, 2)

    await safe_edit_message(
        callback.message,
        text,
        reply_markup=builder.as_markup(),
    )


@router.callback_query(ChannelsCB.filter(F.action == "filter_rating"))
async def handle_filter_rating(callback: CallbackQuery) -> None:
    """Фильтр по рейтингу надёжности."""
    text = (
        "⭐ <b>Фильтр по рейтингу надёжности</b>\n\n"
        "Выберите минимальное количество звёзд:\n\n"
        "Рейтинг рассчитывается на основе отзывов и активности канала."
    )

    builder = InlineKeyboardBuilder()
    builder.button(text="≥ 3★", callback_data=ChannelsCB(action="rating_3").pack())
    builder.button(text="≥ 4★", callback_data=ChannelsCB(action="rating_4").pack())
    builder.button(text="5★", callback_data=ChannelsCB(action="rating_5").pack())
    builder.button(text="◀️ Назад", callback_data=ChannelsCB(action="advanced_filters").pack())
    builder.adjust(3)

    await safe_edit_message(
        callback.message,
        text,
        reply_markup=builder.as_markup(),
    )


@router.callback_query(ChannelsCB.filter(F.action == "filter_fraud"))
async def handle_filter_fraud(callback: CallbackQuery) -> None:
    """Фильтр без накрутки."""
    async with async_session_factory() as session:
        from sqlalchemy import false, select, true

        from src.db.models.analytics import TelegramChat
        from src.db.models.channel_rating import ChannelRating

        # Получаем каналы без fraud_flag
        stmt = (
            select(TelegramChat)
            .join(ChannelRating, ChannelRating.channel_id == TelegramChat.id)
            .where(
                TelegramChat.is_active == true(),
                ChannelRating.fraud_flag == false(),  # noqa: E712
            )
            .order_by(ChannelRating.total_score.desc())
            .limit(20)
        )
        result = await session.execute(stmt)
        channels = list(result.scalars().all())

    text = (
        "🛡 <b>Каналы без накрутки</b>\n\n"
        f"Найдено {len(channels)} верифицированных каналов.\n\n"
        "Эти каналы прошли проверку на накрутку подписчиков."
    )

    builder = InlineKeyboardBuilder()
    for ch in channels[:10]:
        builder.button(
            text=f"📺 {ch.username or ch.title}",
            callback_data=ChannelsCB(action="view_channel", value=str(ch.id)).pack(),
        )
    builder.button(text="◀️ Назад", callback_data=ChannelsCB(action="advanced_filters").pack())
    builder.adjust(1)

    await safe_edit_message(
        callback.message,
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

    await safe_edit_message(
        callback.message,
        text,
        reply_markup=get_channels_menu_kb(),
    )


# ─────────────────────────────────────────────
# TASK 4: Детальная страница канала
# ─────────────────────────────────────────────

@router.callback_query(ChannelsCB.filter(F.action == "view_channel"))
async def view_channel_detail(callback: CallbackQuery, callback_data: ChannelsCB) -> None:
    """
    Показать детальную страницу канала.
    """
    if callback.message is None:
        return

    channel_id = int(callback_data.value)

    async with async_session_factory() as session:
        from sqlalchemy import false, func, select

        from src.db.models.analytics import TelegramChat
        from src.db.models.mailing_log import MailingLog, MailingStatus
        from src.db.models.review import Review, ReviewerRole

        channel = await session.get(TelegramChat, channel_id)
        if not channel:
            await callback.answer("❌ Канал не найден", show_alert=True)
            return

        # Статистика размещений
        stmt = select(func.count(MailingLog.id)).where(
            MailingLog.chat_id == channel_id
        )
        total_placements = (await session.execute(stmt)).scalar() or 0

        stmt = select(func.count(MailingLog.id)).where(
            MailingLog.chat_id == channel_id,
            MailingLog.status == MailingStatus.SENT,
        )
        completed_placements = (await session.execute(stmt)).scalar() or 0

        # Рейтинг и отзывы
        stmt = select(func.avg(Review.score_compliance)).where(
            Review.channel_id == channel_id,
            Review.reviewer_role == ReviewerRole.ADVERTISER,
            Review.is_hidden == false(),
        )
        avg_rating = (await session.execute(stmt)).scalar() or 0.0

        stmt = select(func.count(Review.id)).where(
            Review.channel_id == channel_id,
            Review.reviewer_role == ReviewerRole.ADVERTISER,
            Review.is_hidden == false(),
        )
        reviews_count = (await session.execute(stmt)).scalar() or 0

        # Формируем текст
        username = f"@{channel.username}" if channel.username else "—"
        member_count = f"{channel.member_count:,}" if channel.member_count else "—"
        er = f"{channel.er:.1f}%" if hasattr(channel, 'er') and channel.er else "—"
        rating = f"{avg_rating:.1f}" if avg_rating > 0 else "Нет оценок"
        price = f"{channel.price_per_post or 0} кр"
        topics = channel.topic or "Не указаны"
        joined_date = channel.created_at.strftime("%d.%m.%Y") if channel.created_at else "—"

        text = (
            f"📡 <b>Канал: {username}</b>\n\n"
            f"📝 <b>Название:</b> {channel.title or '—'}\n"
            f"👥 <b>Подписчиков:</b> {member_count}\n"
            f"📈 <b>ER:</b> {er}\n"
            f"⭐ <b>Рейтинг:</b> {rating} ({reviews_count} отзывов)\n"
            f"💰 <b>Цена:</b> {price} / пост\n"
            f"🏷 <b>Тематики:</b> {topics}\n"
            f"📅 <b>В базе с:</b> {joined_date}\n\n"
            f"━━ СТАТИСТИКА ━━\n"
            f"📤 <b>Размещений:</b> {total_placements}\n"
            f"✅ <b>Выполнено:</b> {completed_placements}\n"
        )

    from src.bot.keyboards.channels import get_channel_detail_kb
    keyboard = get_channel_detail_kb(channel_id)

    await safe_edit_message(
        callback.message,
        text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )


# ─────────────────────────────────────────────
# TASK: Добавить в кампанию
# ─────────────────────────────────────────────

@router.callback_query(ChannelsCB.filter(F.action == "add_to_campaign"))
async def add_channel_to_campaign(
    callback: CallbackQuery,
    callback_data: ChannelsCB,
    state: FSMContext,
) -> None:
    """
    Начать создание кампании с предвыбранным каналом.
    """
    channel_id = int(callback_data.value)

    async with async_session_factory() as session:
        from src.db.repositories.campaign_repo import CampaignRepository
        from src.db.repositories.user_repo import UserRepository

        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(callback.from_user.id)

        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        # Проверить тариф
        plan_value = user.plan.value if hasattr(user.plan, "value") else str(user.plan)
        if plan_value == "free":
            await callback.answer(
                "❌ На тарифе FREE создание кампаний недоступно\n\n"
                "Перейдите в Кабинет → Сменить тариф",
                show_alert=True,
            )
            return

        # Проверить лимит кампаний
        campaign_repo = CampaignRepository(session)
        campaign_count = await campaign_repo.get_user_campaigns_count(user.id)
        campaign_limit = user.get_campaign_limit()

        if campaign_count >= campaign_limit:
            await callback.answer(
                f"❌ Превышен лимит кампаний: {campaign_count}/{campaign_limit}\n\n"
                "Завершите текущие кампании или смените тариф",
                show_alert=True,
            )
            return

        # Получить данные канала
        from src.db.models.analytics import TelegramChat

        channel = await session.get(TelegramChat, channel_id)
        if not channel:
            await callback.answer("❌ Канал не найден", show_alert=True)
            return

        # Проверить что канал принимает рекламу
        if not channel.is_accepting_ads:
            await callback.answer(
                "⚠️ Этот канал временно не принимает рекламу",
                show_alert=True,
            )
            return

        # Сохранить в state
        await state.update_data(
            preselected_channel_id=channel_id,
            preselected_channel_username=channel.username,
            preselected_channel_price=channel.price_per_post,
            preselected_channel_topic=channel.topic,
        )

    # Показать приветственное сообщение
    text = (
        f"✅ <b>Канал выбран!</b>\n\n"
        f"📡 @{channel.username or channel.title}\n"
        f"💰 Цена за пост: {channel.price_per_post} кр\n\n"
        f"Теперь создайте кампанию:\n"
        f"1️⃣ Введите заголовок\n"
        f"2️⃣ Введите текст\n"
        f"3️⃣ Подтвердите запуск\n\n"
        f"Канал будет автоматически добавлен в список для рассылки."
    )

    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Начать создание", callback_data="start_campaign_with_channel")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data=ChannelsCB(action="top_channels").pack())],
    ])

    await safe_callback_edit(callback, text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "start_campaign_with_channel")
async def start_campaign_with_channel(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Перейти к вводу заголовка кампании."""
    from src.bot.keyboards.campaign import get_campaign_step_kb
    from src.bot.states.campaign import CampaignStates

    await state.set_state(CampaignStates.waiting_header)

    text = (
        "📝 <b>Заголовок кампании</b>\n\n"
        "Введите название для вашей кампании.\n"
        "Это поможет вам идентифицировать кампанию в списке.\n\n"
        "Пример: «Реклама в @example — Март 2026»\n\n"
        "👇 Введите заголовок:"
    )

    await safe_callback_edit(callback, text, reply_markup=get_campaign_step_kb())


# ─────────────────────────────────────────────
# TASK: Мультивыбор фильтров
# ─────────────────────────────────────────────

@router.callback_query(ChannelsCB.filter(F.action == "toggle_category"))
async def toggle_category(
    callback: CallbackQuery,
    callback_data: ChannelsCB,
    state: FSMContext,
) -> None:
    """Переключить категорию (добавить/убрать)."""

    category = callback_data.value

    # Получить текущие фильтры
    data = await state.get_data()
    selected = data.get("filter_selected_categories", [])

    # Toggle
    if category in selected:
        selected.remove(category)
    else:
        selected.append(category)

    await state.update_data(filter_selected_categories=selected)

    # Перерисовать клавиатуру
    from src.bot.keyboards.channels import get_multi_select_categories_kb

    await safe_callback_edit(
        callback,
        "📁 <b>Выберите категории</b>\n\n"
        f"Выбрано: {len(selected)}\n\n"
        "Нажмите на категорию чтобы добавить/убрать.\n"
        "Когда закончите — нажмите «Применить фильтры».",
        reply_markup=get_multi_select_categories_kb(selected),
    )
    await callback.answer()


@router.callback_query(ChannelsCB.filter(F.action == "toggle_tariff"))
async def toggle_tariff(
    callback: CallbackQuery,
    callback_data: ChannelsCB,
    state: FSMContext,
) -> None:
    """Переключить тариф (добавить/убрать)."""

    tariff = callback_data.value

    # Получить текущие фильтры
    data = await state.get_data()
    selected = data.get("filter_selected_tariffs", [])

    # Toggle
    if tariff in selected:
        selected.remove(tariff)
    else:
        selected.append(tariff)

    await state.update_data(filter_selected_tariffs=selected)

    # Перерисовать клавиатуру
    from src.bot.keyboards.channels import get_multi_select_tariffs_kb

    await safe_callback_edit(
        callback,
        "💎 <b>Выберите тарифы</b>\n\n"
        f"Выбрано: {len(selected)}\n\n"
        "Нажмите на тариф чтобы добавить/убрать.\n"
        "Когда закончите — нажмите «Применить фильтры».",
        reply_markup=get_multi_select_tariffs_kb(selected),
    )
    await callback.answer()


@router.callback_query(ChannelsCB.filter(F.action == "apply_filters"))
async def apply_filters(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Применить выбранные фильтры и показать результат."""

    data = await state.get_data()
    categories = data.get("filter_selected_categories", [])
    tariffs = data.get("filter_selected_tariffs", [])

    # Сохранить фильтры для последующего использования
    await state.update_data(
        filters_applied=True,
        filter_categories=categories,
        filter_tariffs=tariffs,
    )

    # Показать сообщение с применёнными фильтрами
    from src.bot.keyboards.channels import get_active_filters_bar

    filters_text = get_active_filters_bar(categories, tariffs)

    text = (
        f"{filters_text}\n"
        f"📡 <b>Поиск каналов...</b>\n\n"
        f"Используется фильтрация по выбранным критериям."
    )

    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Показать результаты", callback_data=ChannelsCB(action="show_filtered_results").pack())],
        [InlineKeyboardButton(text="✏️ Изменить фильтры", callback_data=ChannelsCB(action="categories").pack())],
        [InlineKeyboardButton(text="❌ Сбросить фильтры", callback_data=ChannelsCB(action="clear_filters").pack())],
    ])

    await safe_callback_edit(callback, text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(ChannelsCB.filter(F.action == "clear_filters"))
async def clear_filters(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Сбросить все фильтры."""

    # Очистить все фильтры из state
    await state.update_data(
        filter_selected_categories=[],
        filter_selected_tariffs=[],
        filters_applied=False,
    )

    await callback.answer("✅ Фильтры сброшены", show_alert=False)

    # Вернуться к основному меню каталога
    await handle_categories(callback)


@router.callback_query(ChannelsCB.filter(F.action == "show_filtered_results"))
async def show_filtered_results(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Показать каналы с применёнными фильтрами."""

    data = await state.get_data()
    categories = data.get("filter_categories", [])
    tariffs = data.get("filter_tariffs", [])

    async with async_session_factory() as session:
        from sqlalchemy import and_, func, or_, select

        from src.db.models.analytics import TelegramChat

        # Построить фильтры
        filters = [TelegramChat.is_active == True]  # noqa: E712

        # Категории (OR внутри)
        if categories:
            filters.append(
                or_(*[func.lower(TelegramChat.topic) == cat.lower() for cat in categories])
            )

        # Тарифы (если поле tariff_tier существует)
        # Пока пропускаем, т.к. поля может не быть в БД

        # Считаем количество
        total_result = await session.execute(
            select(func.count(TelegramChat.id)).where(and_(*filters))
        )
        total = total_result.scalar() or 0

        # Получаем топ каналов
        top_result = await session.execute(
            select(
                TelegramChat.username,
                TelegramChat.title,
                TelegramChat.member_count,
            )
            .where(and_(*filters))
            .order_by(TelegramChat.member_count.desc())
            .limit(10)
        )
        top_channels = top_result.tuples().all()

    # Формируем текст
    from src.bot.keyboards.channels import get_active_filters_bar

    filters_text = get_active_filters_bar(categories, tariffs)

    text = (
        f"{filters_text}\n\n"
        f"📡 <b>Найдено каналов: {total}</b>\n\n"
    )

    if top_channels:
        text += "<b>Топ каналов:</b>\n"
        for i, ch in enumerate(top_channels, 1):
            username = ch[0] or "—"
            title = ch[1] or "Без названия"
            subs = f"{ch[2]:,}" if ch[2] else "—"
            text += f"{i}. <a href='https://t.me/{username}'>{title}</a> — {subs}\n"

    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Изменить фильтры", callback_data=ChannelsCB(action="categories").pack())],
        [InlineKeyboardButton(text="❌ Сбросить фильтры", callback_data=ChannelsCB(action="clear_filters").pack())],
        [InlineKeyboardButton(text="🔙 В меню базы", callback_data=ChannelsCB(action="menu").pack())],
    ])

    await safe_callback_edit(callback, text, reply_markup=keyboard, parse_mode="HTML")
