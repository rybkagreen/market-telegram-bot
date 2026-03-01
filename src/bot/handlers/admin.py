"""
Handlers админ-панели бота.

Все handlers защищены AdminFilter — доступны только пользователям из ADMIN_IDS.
"""

import logging
from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import func, select

from src.bot.filters.admin import AdminFilter
from src.bot.keyboards.admin import (
    AdminCB,
    get_admin_confirm_kb,
    get_admin_main_kb,
    get_back_kb,
    get_user_actions_kb,
    get_users_list_kb,
)
from src.bot.keyboards.campaign import (
    CampaignCB,
    get_member_count_kb,
    get_schedule_kb,
    get_topics_kb,
)
from src.bot.states.admin import (
    AdminAIGenerateStates,
    AdminBalanceStates,
    AdminBanStates,
    AdminBroadcastStates,
    AdminFreeCampaignStates,
)
from src.config.settings import settings
from src.core.services.ai_service import admin_ai_service
from src.db.models.campaign import CampaignStatus
from src.db.models.transaction import Transaction, TransactionType
from src.db.models.user import User
from src.db.repositories.campaign_repo import CampaignRepository
from src.db.repositories.user_repo import UserRepository
from src.db.session import async_session_factory
from src.tasks.mailing_tasks import send_campaign
from src.utils.content_filter.filter import check as content_filter_check

logger = logging.getLogger(__name__)

# Создаём роутер с фильтрами
router = Router()
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())


# ==================== ВХОД В АДМИНКУ ====================


@router.message(Command("admin"))
async def handle_admin_menu(message: Message, state: FSMContext) -> None:
    """
    Вход в панель администратора.

    Args:
        message: Сообщение от пользователя.
        state: FSM контекст.
    """
    await state.clear()
    await message.answer(
        "🔐 <b>Панель администратора</b>\n\n"
        f"Добро пожаловать, <b>{message.from_user.first_name}</b>!\n\n"
        f"Ваш ID: <code>{message.from_user.id}</code>",
        reply_markup=get_admin_main_kb(),
    )


# ==================== СТАТИСТИКА ПЛАТФОРМЫ ====================


@router.callback_query(AdminCB.filter(F.action == "stats"))
async def handle_admin_stats(callback: CallbackQuery) -> None:
    """
    Показать статистику всей платформы.

    Args:
        callback: Callback query.
    """
    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        campaign_repo = CampaignRepository(session)

        total_users = await user_repo.count()
        active_users = await user_repo.count(User.is_active == True)  # noqa: E712
        banned_users = await user_repo.count(User.is_banned == True)  # noqa: E712

        total_campaigns = await campaign_repo.count()
        running_campaigns = await campaign_repo.count(
            CampaignRepository.model.status == CampaignStatus.RUNNING
        )
        queued_campaigns = await campaign_repo.count(
            CampaignRepository.model.status == CampaignStatus.QUEUED
        )

        # Общая выручка (сумма всех пополнений)
        revenue_query = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.type == TransactionType.TOPUP
        )
        revenue_result = await session.execute(revenue_query)
        total_revenue = revenue_result.scalar_one() or 0

    text = (
        "📊 <b>Статистика платформы</b>\n\n"
        f"👥 Пользователей всего: <b>{total_users}</b>\n"
        f"🟢 Активных: <b>{active_users}</b>\n"
        f"🚫 Забаненных: <b>{banned_users}</b>\n\n"
        f"📣 Кампаний всего: <b>{total_campaigns}</b>\n"
        f"🔄 Активных сейчас: <b>{running_campaigns}</b>\n"
        f"⏳ В очереди: <b>{queued_campaigns}</b>\n\n"
        f"💰 Выручка всего: <b>{total_revenue}₽</b>"
    )

    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Назад", callback_data=AdminCB(action="main"))
    builder.adjust(1)

    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


# ==================== ИИ-ГЕНЕРАЦИЯ КАМПАНИИ ====================


@router.callback_query(AdminCB.filter(F.action == "ai_generate"))
async def handle_ai_generate_start(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Начать ИИ-генерацию кампании.

    Args:
        callback: Callback query.
        state: FSM контекст.
    """
    await state.clear()
    await state.set_state(AdminAIGenerateStates.waiting_description)

    await callback.message.edit_text(
        "🤖 <b>ИИ-генерация кампании</b>\n\n"
        "Опишите, о чём должна быть рекламная кампания.\n"
        "ИИ сгенерирует название, текст и варианты A/B тестирования.\n\n"
        "Пример: 'Продвижение онлайн-курса по программированию для начинающих'\n\n"
        "Введите описание:",
        reply_markup=get_back_kb(),
    )
    await callback.answer()


@router.message(AdminAIGenerateStates.waiting_description)
async def handle_ai_generate_description(message: Message, state: FSMContext) -> None:
    """
    Обработать описание для ИИ-генерации.

    Args:
        message: Сообщение с описанием.
        state: FSM контекст.
    """
    description = message.text.strip()

    if len(description) < 10 or len(description) > 500:
        await message.answer("❌ Описание должно быть от 10 до 500 символов.")
        return

    await state.update_data(ai_description=description)

    # Генерируем кампанию через ИИ (бесплатно для админа)
    await message.answer("⏳ Генерирую кампанию через ИИ...")

    try:
        # Генерируем A/B варианты
        variants = await admin_ai_service.generate_ab_variants(
            user_id=message.from_user.id,
            description=description,
            count=3,
        )

        # Сохраняем варианты
        await state.update_data(ai_variants=variants)

        # Формируем текст с вариантами
        text = "✅ <b>ИИ сгенерировал 3 варианта</b>\n\nВыберите лучший:\n\n"
        for i, variant in enumerate(variants, 1):
            text += f"<b>Вариант {i}:</b>\n{variant}\n\n"

        builder = InlineKeyboardBuilder()
        for i in range(1, 4):
            builder.button(
                text=f"Вариант {i}", callback_data=AdminCB(action="ai_variant_select", value=str(i))
            )
        builder.button(text="🔄 Перегенерировать", callback_data=AdminCB(action="ai_regenerate"))
        builder.button(text="🔙 Назад", callback_data=AdminCB(action="main"))
        builder.adjust(1, 1, 1)

        await message.answer(text, reply_markup=builder.as_markup())

    except Exception as e:
        logger.error(f"AI generation error: {e}")
        await message.answer(
            "❌ Ошибка при генерации через ИИ.\n"
            f"Попробуйте ещё раз или введите текст вручную.\n\n"
            f"Ошибка: {str(e)}",
            reply_markup=get_back_kb(),
        )
        await state.set_state(AdminAIGenerateStates.waiting_description)


@router.callback_query(AdminCB.filter(F.action == "ai_regenerate"))
async def handle_ai_regenerate(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Перегенерировать варианты через ИИ.

    Args:
        callback: Callback query.
        state: FSM контекст.
    """
    data = await state.get_data()
    description = data.get("ai_description", "")

    await callback.message.edit_text("⏳ Перегенерирую варианты...")

    try:
        variants = await admin_ai_service.generate_ab_variants(
            user_id=callback.from_user.id,
            description=description,
            count=3,
        )
        await state.update_data(ai_variants=variants)

        text = "✅ <b>ИИ сгенерировал 3 варианта</b>\n\nВыберите лучший:\n\n"
        for i, variant in enumerate(variants, 1):
            text += f"<b>Вариант {i}:</b>\n{variant}\n\n"

        builder = InlineKeyboardBuilder()
        for i in range(1, 4):
            builder.button(
                text=f"Вариант {i}", callback_data=AdminCB(action="ai_variant_select", value=str(i))
            )
        builder.button(text="🔄 Перегенерировать", callback_data=AdminCB(action="ai_regenerate"))
        builder.button(text="🔙 Назад", callback_data=AdminCB(action="main"))
        builder.adjust(1, 1, 1)

        await callback.message.edit_text(text, reply_markup=builder.as_markup())

    except Exception as e:
        logger.error(f"AI regeneration error: {e}")
        await callback.message.edit_text(
            "❌ Ошибка при перегенерации.\nПопробуйте ещё раз.",
            reply_markup=get_back_kb(),
        )


@router.callback_query(AdminCB.filter(F.action == "ai_variant_select"))
async def handle_ai_variant_select(
    callback: CallbackQuery,
    callback_data: AdminCB,
    state: FSMContext,
) -> None:
    """
    Выбрать вариант кампании.

    Args:
        callback: Callback query.
        callback_data: Данные callback.
        state: FSM контекст.
    """
    variant_index = int(callback_data.value) - 1
    data = await state.get_data()
    variants = data.get("ai_variants", [])

    if not variants or variant_index >= len(variants):
        await callback.answer("❌ Вариант не найден", show_alert=True)
        return

    selected_text = variants[variant_index]
    await state.update_data(text=selected_text, selected_variant=variant_index + 1)

    # Генерируем название на основе описания (бесплатно для админа)
    await callback.message.edit_text("⏳ Генерирую название...")

    try:
        title = await admin_ai_service.generate(
            prompt=f"Придумай короткое название (2-4 слова) для рекламной кампании: {data.get('ai_description', '')}",
            system="Ты профессиональный маркетолог. Придумай короткое и запоминающееся название для рекламной кампании.",
        )
        title = title.strip()[:100]
        await state.update_data(title=title)

        await state.set_state(AdminAIGenerateStates.waiting_topic)
        await callback.message.edit_text(
            f"✅ <b>Кампания сгенерирована!</b>\n\n"
            f"📋 <b>Название:</b> {title}\n"
            f"📝 <b>Текст:</b> {selected_text[:200]}...\n\n"
            f"Выберите тематику для рассылки:",
            reply_markup=get_topics_kb(),
        )

    except Exception as e:
        logger.error(f"AI title generation error: {e}")
        # Используем дефолтное название
        title = f"Кампания #{variant_index + 1}"
        await state.update_data(title=title)
        await state.set_state(AdminAIGenerateStates.waiting_topic)
        await callback.message.edit_text(
            f"✅ <b>Кампания сгенерирована!</b>\n\n"
            f"📋 <b>Название:</b> {title}\n"
            f"📝 <b>Текст:</b> {selected_text[:200]}...\n\n"
            f"Выберите тематику для рассылки:",
            reply_markup=get_topics_kb(),
        )


# ==================== СПИСОК ПОЛЬЗОВАТЕЛЕЙ ====================


@router.callback_query(AdminCB.filter(F.action == "users"))
async def handle_users_list(callback: CallbackQuery) -> None:
    """
    Показать список пользователей.

    Args:
        callback: Callback query.
    """
    await show_users_page(callback, page=1)


async def show_users_page(callback: CallbackQuery, page: int = 1) -> None:
    """
    Показать страницу списка пользователей.

    Args:
        callback: Callback query.
        page: Номер страницы.
    """
    per_page = 10

    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        users = await user_repo.find_many(
            limit=per_page,
            offset=(page - 1) * per_page,
            order_by=User.id.desc(),
        )
        total = await user_repo.count()

    total_pages = max(1, (total + per_page - 1) // per_page)

    text = f"👥 <b>Пользователи</b> (стр. {page}/{total_pages})\n\n"
    text += f"Всего: <b>{total}</b>\n\n"

    for i, user in enumerate(users, 1):
        ban_emoji = "🚫 " if user.is_banned else "✅ "
        username = f"@{user.username}" if user.username else "—"
        text += f"<b>{i}.</b> {ban_emoji}ID:{user.telegram_id} | {username} | {user.balance}₽\n"

    await callback.message.edit_text(
        text,
        reply_markup=get_users_list_kb(users, page, total_pages),
    )
    await callback.answer()


@router.callback_query(AdminCB.filter(F.action == "users_page"))
async def handle_users_pagination(callback: CallbackQuery, callback_data: AdminCB) -> None:
    """
    Пагинация списка пользователей.

    Args:
        callback: Callback query.
        callback_data: Данные callback.
    """
    page = int(callback_data.value)
    await show_users_page(callback, page=page)


@router.callback_query(AdminCB.filter(F.action == "user_detail"))
async def handle_user_detail(callback: CallbackQuery, callback_data: AdminCB) -> None:
    """
    Показать детали пользователя.

    Args:
        callback: Callback query.
        callback_data: Данные callback (user DB id).
    """
    user_db_id = int(callback_data.value)

    async with async_session_factory() as session:
        user = await UserRepository(session).get_by_id(user_db_id)

    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return

    # Получаем количество кампаний
    campaign_repo = CampaignRepository(session)
    campaign_count = await campaign_repo.count(CampaignRepository.model.user_id == user.id)

    ban_emoji = "🚫 Забанен" if user.is_banned else "✅ Активен"
    created_at = user.created_at.strftime("%d.%m.%Y") if user.created_at else "—"
    plan_value = user.plan.value if hasattr(user.plan, "value") else user.plan

    text = (
        f"👤 <b>Профиль пользователя</b>\n\n"
        f"Telegram ID: <code>{user.telegram_id}</code>\n"
        f"Username: @{user.username or '—'}\n"
        f"Имя: {user.full_name}\n\n"
        f"💳 Баланс: <b>{user.balance}₽</b>\n"
        f"📦 Тариф: <b>{plan_value}</b>\n"
        f"📊 Кампаний: <b>{campaign_count}</b>\n\n"
        f"📅 Регистрация: {created_at}\n"
        f"Статус: {ban_emoji}\n\n"
        f"Реферальный код: <code>{user.referral_code}</code>"
    )

    await callback.message.edit_text(
        text,
        reply_markup=get_user_actions_kb(user_db_id, user.is_banned),
    )
    await callback.answer()


# ==================== БАН / РАЗБАН ====================


@router.callback_query(AdminCB.filter(F.action == "ban_user"))
async def handle_ban_start(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Начать процесс бана пользователя.

    Args:
        callback: Callback query.
        state: FSM контекст.
    """
    await state.set_state(AdminBanStates.waiting_user_id)
    await callback.message.edit_text(
        "🚫 <b>Бан пользователя</b>\n\nВведите Telegram ID пользователя:",
        reply_markup=get_back_kb(),
    )
    await callback.answer()


@router.message(AdminBanStates.waiting_user_id)
async def handle_ban_user_id(message: Message, state: FSMContext) -> None:
    """
    Обработать ввод Telegram ID для бана.

    Args:
        message: Сообщение с ID.
        state: FSM контекст.
    """
    if not message.text.isdigit():
        await message.answer("❌ Введите числовой Telegram ID.")
        return

    telegram_id = int(message.text)

    async with async_session_factory() as session:
        user = await UserRepository(session).get_by_telegram_id(telegram_id)

    if not user:
        await message.answer("❌ Пользователь не найден.")
        await state.clear()
        return

    # Нельзя банить админа
    if user.telegram_id in settings.admin_ids:
        await message.answer("❌ Нельзя забанить администратора.")
        await state.clear()
        return

    await state.update_data(target_telegram_id=telegram_id, target_db_id=user.id)
    await state.set_state(AdminBanStates.waiting_reason)

    status = "🚫 Забанен" if user.is_banned else "✅ Активен"
    await message.answer(
        f"👤 <b>{user.full_name}</b>\n"
        f"Telegram ID: <code>{telegram_id}</code>\n"
        f"Статус: {status}\n\n"
        f"Введите причину {'бана' if not user.is_banned else 'разбана'}:"
    )


@router.message(AdminBanStates.waiting_reason)
async def handle_ban_reason(message: Message, state: FSMContext) -> None:
    """
    Обработать причину бана и выполнить бан.

    Args:
        message: Сообщение с причиной.
        state: FSM контекст.
    """
    data = await state.get_data()
    reason = message.text
    target_db_id = data["target_db_id"]
    target_telegram_id = data["target_telegram_id"]

    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_id(target_db_id)

        if not user:
            await message.answer("❌ Пользователь не найден.")
            await state.clear()
            return

        # Toggle ban
        new_status = not user.is_banned
        await user_repo.update(target_db_id, {"is_banned": new_status})

        action = "разбанен ✅" if new_status else "забанен 🚫"
        logger.warning(
            f"Admin {message.from_user.id} {action} user {target_telegram_id}. Reason: {reason}"
        )

    await message.answer(
        f"✅ Пользователь {action}\nПричина: {reason}",
        reply_markup=get_admin_main_kb(),
    )
    await state.clear()


# ==================== УПРАВЛЕНИЕ БАЛАНСОМ ====================


@router.callback_query(AdminCB.filter(F.action == "balance_manage"))
async def handle_balance_manage(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Начать изменение баланса пользователя.

    Args:
        callback: Callback query.
        state: FSM контекст.
    """
    await state.set_state(AdminBalanceStates.waiting_user_id)
    await callback.message.edit_text(
        "💰 <b>Изменение баланса пользователя</b>\n\nВведите Telegram ID пользователя:",
        reply_markup=get_back_kb(),
    )
    await callback.answer()


@router.message(AdminBalanceStates.waiting_user_id)
async def handle_balance_user_id(message: Message, state: FSMContext) -> None:
    """
    Обработать ввод Telegram ID для изменения баланса.

    Args:
        message: Сообщение с ID.
        state: FSM контекст.
    """
    if not message.text.isdigit():
        await message.answer("❌ Введите числовой Telegram ID.")
        return

    telegram_id = int(message.text)

    async with async_session_factory() as session:
        user = await UserRepository(session).get_by_telegram_id(telegram_id)

    if not user:
        await message.answer("❌ Пользователь не найден.")
        await state.clear()
        return

    await state.update_data(target_db_id=user.id, target_telegram_id=telegram_id)
    await state.set_state(AdminBalanceStates.waiting_amount)

    await message.answer(
        f"👤 <b>{user.full_name}</b>\n"
        f"Telegram ID: <code>{telegram_id}</code>\n"
        f"💳 Текущий баланс: <b>{user.balance}₽</b>\n\n"
        "Введите сумму изменения:\n"
        "<code>+500</code> — пополнить на 500₽\n"
        "<code>-200</code> — списать 200₽"
    )


@router.message(AdminBalanceStates.waiting_amount)
async def handle_balance_amount(message: Message, state: FSMContext) -> None:
    """
    Обработать сумму изменения баланса.

    Args:
        message: Сообщение с суммой.
        state: FSM контекст.
    """
    text = message.text.strip().replace(",", ".")

    try:
        amount = Decimal(text)
    except InvalidOperation:
        await message.answer("❌ Введите число, например: +500 или -200")
        return

    await state.update_data(amount=str(amount))
    await state.set_state(AdminBalanceStates.waiting_reason)
    await message.answer("Введите причину изменения (для лога):")


@router.message(AdminBalanceStates.waiting_reason)
async def handle_balance_reason(message: Message, state: FSMContext) -> None:
    """
    Обработать причину и выполнить изменение баланса.

    Args:
        message: Сообщение с причиной.
        state: FSM контекст.
    """
    data = await state.get_data()
    amount = Decimal(data["amount"])
    target_db_id = data["target_db_id"]
    reason = message.text

    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_id(target_db_id)

        if not user:
            await message.answer("❌ Пользователь не найден.")
            await state.clear()
            return

        # Обновляем баланс
        await user_repo.update_balance(target_db_id, amount)
        await user_repo.refresh(user)

        sign = "+" if amount > 0 else ""
        logger.info(
            f"Admin {message.from_user.id} changed balance of user "
            f"{user.telegram_id} by {sign}{amount}₽. Reason: {reason}"
        )

    await message.answer(
        f"✅ <b>Баланс изменён</b>\n\n"
        f"Изменение: <b>{sign}{amount}₽</b>\n"
        f"Новый баланс: <b>{user.balance}₽</b>\n"
        f"Причина: {reason}",
        reply_markup=get_admin_main_kb(),
    )
    await state.clear()


# ==================== BROADCAST РАССЫЛКА ====================


@router.callback_query(AdminCB.filter(F.action == "broadcast"))
async def handle_broadcast_start(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Начать broadcast рассылку.

    Args:
        callback: Callback query.
        state: FSM контекст.
    """
    await state.set_state(AdminBroadcastStates.waiting_message)
    await callback.message.edit_text(
        "📢 <b>Broadcast рассылка</b>\n\n"
        "Введите текст сообщения.\n"
        "Поддерживается HTML форматирование.\n\n"
        "⚠️ Сообщение получат <b>все</b> незабаненные пользователи.",
        reply_markup=get_back_kb(),
    )
    await callback.answer()


@router.message(AdminBroadcastStates.waiting_message)
async def handle_broadcast_message(message: Message, state: FSMContext) -> None:
    """
    Обработать текст рассылки.

    Args:
        message: Сообщение с текстом.
        state: FSM контекст.
    """
    await state.update_data(broadcast_text=message.text)
    await state.set_state(AdminBroadcastStates.waiting_confirm)

    async with async_session_factory() as session:
        total = await UserRepository(session).count(User.is_banned == False)  # noqa: E712

    await message.answer(
        f"📢 <b>Предпросмотр рассылки</b>\n\n"
        f"{message.text}\n\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Получателей: <b>{total}</b> пользователей",
        reply_markup=get_admin_confirm_kb("broadcast"),
    )


@router.callback_query(AdminCB.filter(F.action == "broadcast_confirm"))
async def handle_broadcast_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Выполнить broadcast рассылку.

    Args:
        callback: Callback query.
        state: FSM контекст.
    """
    data = await state.get_data()
    text = data["broadcast_text"]
    await state.clear()

    async with async_session_factory() as session:
        users = await UserRepository(session).find_many(
            User.is_banned == False,  # noqa: E712
            limit=1000,
        )

    sent = 0
    failed = 0

    for user in users:
        try:
            await callback.bot.send_message(user.telegram_id, text, parse_mode="HTML")
            sent += 1
        except Exception as e:
            logger.error(f"Failed to send broadcast to {user.telegram_id}: {e}")
            failed += 1

    await callback.message.edit_text(
        f"✅ <b>Broadcast завершён</b>\n\n📤 Отправлено: <b>{sent}</b>\n❌ Ошибок: <b>{failed}</b>",
        reply_markup=get_admin_main_kb(),
    )
    await callback.answer()


# ==================== БЕСПЛАТНАЯ КАМПАНИЯ (ДЛЯ АДМИНА) ====================


@router.callback_query(AdminCB.filter(F.action == "free_campaign"))
async def handle_free_campaign_start(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Начать создание бесплатной кампании для админа.

    Args:
        callback: Callback query.
        state: FSM контекст.
    """
    await state.clear()
    await state.update_data(is_free=True, admin_id=callback.from_user.id)
    await state.set_state(AdminFreeCampaignStates.waiting_title)

    await callback.message.edit_text(
        "📣 <b>Бесплатная кампания администратора</b>\n\nВведите название кампании:",
        reply_markup=get_back_kb(),
    )
    await callback.answer()


@router.message(AdminFreeCampaignStates.waiting_title)
async def handle_free_campaign_title(message: Message, state: FSMContext) -> None:
    """
    Обработать название кампании.

    Args:
        message: Сообщение с названием.
        state: FSM контекст.
    """
    title = message.text.strip()

    if len(title) < 3 or len(title) > 100:
        await message.answer("❌ Название должно быть от 3 до 100 символов.")
        return

    await state.update_data(title=title)
    await state.set_state(AdminFreeCampaignStates.waiting_text)
    await message.answer("Введите текст рекламного сообщения:")


@router.message(AdminFreeCampaignStates.waiting_text)
async def handle_free_campaign_text(message: Message, state: FSMContext) -> None:
    """
    Обработать текст кампании.

    Args:
        message: Сообщение с текстом.
        state: FSM контекст.
    """
    text = message.text.strip()

    # Content filter проверяет даже для админа
    filter_result = content_filter_check(text)
    if not filter_result.passed:
        await message.answer(
            f"⚠️ Текст не прошёл проверку: {', '.join(filter_result.categories)}\n"
            f"Фрагменты: {', '.join(filter_result.flagged_fragments)}\n\n"
            "Введите другой текст:"
        )
        return

    await state.update_data(text=text)
    await state.set_state(AdminFreeCampaignStates.waiting_topic)
    await message.answer("Выберите тематику:", reply_markup=get_topics_kb())


@router.callback_query(
    AdminFreeCampaignStates.waiting_topic, CampaignCB.filter(F.action == "topic")
)
async def handle_free_campaign_topic(
    callback: CallbackQuery,
    callback_data: CampaignCB,
    state: FSMContext,
) -> None:
    """
    Обработать выбор тематики.

    Args:
        callback: Callback query.
        callback_data: Данные callback.
        state: FSM контекст.
    """
    await state.update_data(topic=callback_data.value)
    await state.set_state(AdminFreeCampaignStates.waiting_member_count)
    await callback.message.edit_text(
        "Выберите размер аудитории:", reply_markup=get_member_count_kb()
    )
    await callback.answer()


@router.callback_query(
    AdminFreeCampaignStates.waiting_member_count,
    CampaignCB.filter(F.action == "members"),
)
async def handle_free_campaign_members(
    callback: CallbackQuery,
    callback_data: CampaignCB,
    state: FSMContext,
) -> None:
    """
    Обработать выбор размера аудитории.

    Args:
        callback: Callback query.
        callback_data: Данные callback.
        state: FSM контекст.
    """
    value = callback_data.value

    if value == "any":
        min_members, max_members = 0, 1000000
    else:
        parts = value.split("_")
        min_members, max_members = int(parts[0]), int(parts[1])

    await state.update_data(min_members=min_members, max_members=max_members)
    await state.set_state(AdminFreeCampaignStates.waiting_schedule)
    await callback.message.edit_text("Когда запустить кампанию?", reply_markup=get_schedule_kb())
    await callback.answer()


@router.callback_query(
    AdminFreeCampaignStates.waiting_schedule,
    CampaignCB.filter(F.action == "schedule_now"),
)
async def handle_free_campaign_schedule_now(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """
    Запустить кампанию немедленно.

    Args:
        callback: Callback query.
        state: FSM контекст.
    """
    await state.update_data(schedule="now")
    await show_free_campaign_confirm(callback, state)


@router.callback_query(
    AdminFreeCampaignStates.waiting_schedule,
    CampaignCB.filter(F.action == "schedule_later"),
)
async def handle_free_campaign_schedule_later(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """
    Запланировать кампанию на потом.

    Args:
        callback: Callback query.
        state: FSM контекст.
    """
    await state.update_data(schedule="later")
    await show_free_campaign_confirm(callback, state)


async def show_free_campaign_confirm(
    callback: CallbackQuery | Message,
    state: FSMContext,
) -> None:
    """
    Показать подтверждение кампании.

    Args:
        callback: Callback query или message.
        state: FSM контекст.
    """
    data = await state.get_data()

    text = (
        "✅ <b>Подтверждение кампании</b>\n\n"
        f"📋 Название: {data.get('title')}\n"
        f"📝 Текст: {data.get('text')[:200]}...\n"
        f"📌 Тематика: {data.get('topic')}\n"
        f"👥 Аудитория: {data.get('min_members')}-{data.get('max_members')}\n"
        f"⏰ Запуск: {'Немедленно' if data.get('schedule') == 'now' else 'По расписанию'}\n\n"
        f"💰 Стоимость: <b>0₽ (бесплатно)</b>"
    )

    builder = InlineKeyboardBuilder()
    builder.button(
        text="✅ Запустить бесплатно",
        callback_data=AdminCB(action="free_campaign_confirm"),
    )
    builder.button(text="❌ Отмена", callback_data=AdminCB(action="cancel"))
    builder.adjust(2)

    if isinstance(callback, CallbackQuery):
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    else:
        await callback.answer(text, reply_markup=builder.as_markup())


@router.callback_query(AdminCB.filter(F.action == "free_campaign_confirm"))
async def handle_free_campaign_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Создать и запустить бесплатную кампанию.

    Args:
        callback: Callback query.
        state: FSM контекст.
    """
    data = await state.get_data()
    admin_id = data.get("admin_id")

    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        admin_user = await user_repo.get_by_telegram_id(admin_id)

        if not admin_user:
            await callback.answer("❌ Администратор не найден", show_alert=True)
            return

        campaign_repo = CampaignRepository(session)

        # Создаём кампанию
        campaign = await campaign_repo.create(
            {
                "user_id": admin_user.id,
                "title": data.get("title"),
                "text": data.get("text"),
                "status": CampaignStatus.RUNNING,
                "filters_json": {
                    "topics": [data.get("topic")],
                    "min_members": data.get("min_members", 0),
                    "max_members": data.get("max_members", 1000000),
                },
                "cost": 0.0,  # Бесплатно
            }
        )

    # Запускаем рассылку
    send_campaign.delay(campaign.id)

    logger.info(f"Admin {admin_id} created free campaign {campaign.id}")

    await callback.message.edit_text(
        f"✅ <b>Кампания запущена!</b>\n\n"
        f"📋 {campaign.title}\n"
        f"💰 Стоимость: <b>0₽ (бесплатно)</b>\n\n"
        f"Вы получите уведомление о завершении.",
        reply_markup=get_admin_main_kb(),
    )
    await state.clear()
    await callback.answer()


# ==================== ПРОДОЛЖЕНИЕ AI-ГЕНЕРАЦИИ ====================


@router.callback_query(AdminAIGenerateStates.waiting_topic, CampaignCB.filter(F.action == "topic"))
async def handle_ai_generate_topic(
    callback: CallbackQuery,
    callback_data: CampaignCB,
    state: FSMContext,
) -> None:
    """
    Обработать выбор тематики для AI-кампании.

    Args:
        callback: Callback query.
        callback_data: Данные callback.
        state: FSM контекст.
    """
    await state.update_data(topic=callback_data.value)
    await state.set_state(AdminAIGenerateStates.waiting_member_count)
    await callback.message.edit_text(
        "Выберите размер чатов для рассылки:",
        reply_markup=get_member_count_kb(),
    )
    await callback.answer()


@router.callback_query(
    AdminAIGenerateStates.waiting_member_count, CampaignCB.filter(F.action == "members")
)
async def handle_ai_generate_member_count(
    callback: CallbackQuery,
    callback_data: CampaignCB,
    state: FSMContext,
) -> None:
    """
    Обработать выбор размера чатов.

    Args:
        callback: Callback query.
        callback_data: Данные callback.
        state: FSM контекст.
    """
    value = callback_data.value
    if value == "any":
        min_members = 0
        max_members = 1000000
    else:
        min_str, max_str = value.split("_")
        min_members = int(min_str)
        max_members = int(max_str)

    await state.update_data(
        min_members=min_members,
        max_members=max_members,
    )
    await state.set_state(AdminAIGenerateStates.waiting_schedule)
    await callback.message.edit_text(
        "Когда запустить кампанию?",
        reply_markup=get_schedule_kb(),
    )
    await callback.answer()


@router.callback_query(
    AdminAIGenerateStates.waiting_schedule, CampaignCB.filter(F.action.startswith("schedule_"))
)
async def handle_ai_generate_schedule(
    callback: CallbackQuery,
    callback_data: CampaignCB,
    state: FSMContext,
) -> None:
    """
    Обработать выбор расписания.

    Args:
        callback: Callback query.
        callback_data: Данные callback.
        state: FSM контекст.
    """
    schedule_value = "now" if callback_data.action == "schedule_now" else "later"
    await state.update_data(schedule=schedule_value)
    await state.set_state(AdminAIGenerateStates.waiting_confirm)
    await show_ai_campaign_confirm(callback, state)
    await callback.answer()


async def show_ai_campaign_confirm(
    callback: CallbackQuery | Message,
    state: FSMContext,
) -> None:
    """
    Показать подтверждение AI-кампании.

    Args:
        callback: Callback query или message.
        state: FSM контекст.
    """
    data = await state.get_data()

    text = (
        "✅ <b>Подтверждение AI-кампании</b>\n\n"
        f"📋 Название: {data.get('title')}\n"
        f"📝 Текст: {data.get('text')[:200]}...\n"
        f"📌 Тематика: {data.get('topic')}\n"
        f"👥 Аудитория: {data.get('min_members')}-{data.get('max_members')}\n"
        f"⏰ Запуск: {'Немедленно' if data.get('schedule') == 'now' else 'По расписанию'}\n\n"
        f"🤖 Сгенерировано через ИИ"
    )

    builder = InlineKeyboardBuilder()
    builder.button(
        text="✅ Запустить кампанию",
        callback_data=AdminCB(action="ai_campaign_confirm"),
    )
    builder.button(text="❌ Отмена", callback_data=AdminCB(action="cancel"))
    builder.adjust(2)

    if isinstance(callback, CallbackQuery):
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    else:
        await callback.answer(text, reply_markup=builder.as_markup())


@router.callback_query(AdminCB.filter(F.action == "ai_campaign_confirm"))
async def handle_ai_campaign_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Создать и запустить AI-кампанию.

    Args:
        callback: Callback query.
        state: FSM контекст.
    """
    data = await state.get_data()
    admin_id = callback.from_user.id

    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        admin_user = await user_repo.get_by_telegram_id(admin_id)

        if not admin_user:
            await callback.answer("❌ Администратор не найден", show_alert=True)
            return

        campaign_repo = CampaignRepository(session)

        # Создаём кампанию
        campaign = await campaign_repo.create(
            {
                "user_id": admin_user.id,
                "title": data.get("title"),
                "text": data.get("text"),
                "ai_description": data.get("ai_description"),
                "status": CampaignStatus.RUNNING,
                "filters_json": {
                    "topics": [data.get("topic")],
                    "min_members": data.get("min_members", 0),
                    "max_members": data.get("max_members", 1000000),
                },
                "cost": 0.0,  # Бесплатно для админа
            }
        )

    # Запускаем рассылку
    send_campaign.delay(campaign.id)

    logger.info(f"Admin {admin_id} created AI campaign {campaign.id}")

    await callback.message.edit_text(
        f"✅ <b>AI-кампания запущена!</b>\n\n"
        f"📋 {campaign.title}\n"
        f"🤖 Сгенерировано через ИИ\n"
        f"💰 Стоимость: <b>0₽ (бесплатно)</b>\n\n"
        f"Вы получите уведомление о завершении.",
        reply_markup=get_admin_main_kb(),
    )
    await state.clear()
    await callback.answer()


@router.callback_query(AdminCB.filter(F.action == "cancel"))
async def handle_admin_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Отменить создание кампании.

    Args:
        callback: Callback query.
        state: FSM контекст.
    """
    await state.clear()
    await callback.message.edit_text(
        "✖ Создание кампании отменено.",
        reply_markup=get_admin_main_kb(),
    )
    await callback.answer()


# ==================== НАЗАД В ГЛАВНОЕ МЕНЮ ====================


@router.callback_query(AdminCB.filter(F.action == "main"))
async def handle_admin_back(callback: CallbackQuery) -> None:
    """
    Вернуться в главное меню админки.

    Args:
        callback: Callback query.
    """
    await callback.message.edit_text(
        "🔐 <b>Панель администратора</b>",
        reply_markup=get_admin_main_kb(),
    )
    await callback.answer()


@router.callback_query(AdminCB.filter(F.action == "back_to_main"))
async def handle_back_to_main(callback: CallbackQuery) -> None:
    """
    Вернуться в главное меню бота.

    Args:
        callback: Callback query.
    """
    from src.bot.keyboards.main_menu import get_main_menu

    async with async_session_factory() as session:
        user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)

    credits = user.credits if user else 0

    await callback.message.edit_text(
        "🔙 Возврат в главное меню",
        reply_markup=get_main_menu(credits, user.id if user else None),
    )
    await callback.answer()


@router.callback_query(AdminCB.filter(F.action == "cancel"))
async def handle_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Отменить текущую операцию.

    Args:
        callback: Callback query.
        state: FSM контекст.
    """
    await state.clear()
    await callback.message.edit_text(
        "❌ Операция отменена",
        reply_markup=get_admin_main_kb(),
    )
    await callback.answer()
