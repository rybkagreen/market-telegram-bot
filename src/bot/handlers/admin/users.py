"""
Admin Users Handlers — управление пользователями.
"""

import logging
from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from src.bot.filters.admin import AdminFilter
from src.bot.keyboards.admin.admin import (
    AdminCB,
    get_admin_confirm_kb,
    get_admin_main_kb,
    get_back_kb,
    get_blacklist_kb,
    get_user_actions_kb,
    get_users_list_kb,
)
from src.bot.states.admin import AdminBalanceStates, AdminBanStates, AdminBroadcastStates
from src.bot.utils.safe_callback import safe_callback_edit
from src.db.models.user import User
from src.db.repositories.campaign_repo import CampaignRepository
from src.db.repositories.chat_analytics import ChatAnalyticsRepository
from src.db.repositories.user_repo import UserRepository
from src.db.session import async_session_factory

logger = logging.getLogger(__name__)

router = Router()
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())


# ==================== СПИСОК ПОЛЬЗОВАТЕЛЕЙ ====================


@router.callback_query(AdminCB.filter(F.action == "users"))
async def handle_users_list(callback: CallbackQuery) -> None:
    """Показать список пользователей."""
    await show_users_page(callback, page=1)


async def show_users_page(callback: CallbackQuery, page: int = 1) -> None:
    """Показать страницу списка пользователей."""
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

        # Формируем отображаемое имя
        display_name_parts = []
        if user.first_name:
            display_name_parts.append(user.first_name)
        if user.last_name:
            display_name_parts.append(user.last_name)
        display_name = " ".join(display_name_parts).strip() or f"ID:{user.telegram_id}"

        # Формируем username или ссылку на профиль
        if user.username:
            username_display = f"@{user.username}"
        else:
            username_display = f"tg://user?id={user.telegram_id}"

        # Показываем три баланса
        text += f"<b>{i}.</b> {ban_emoji}{display_name} | {username_display}\n"
        text += f"    💵 {user.balance_rub:.0f} ₽  🎯 {user.credits} кр  💸 {user.earned_rub:.0f} ₽\n"

    await safe_callback_edit(
        callback, text, reply_markup=get_users_list_kb(users, page, total_pages)
    )
    await callback.answer()


@router.callback_query(AdminCB.filter(F.action == "users_page"))
async def handle_users_pagination(callback: CallbackQuery, callback_data: AdminCB) -> None:
    """Пагинация списка пользователей."""
    page = int(callback_data.value)
    await show_users_page(callback, page=page)


@router.callback_query(AdminCB.filter(F.action == "user_detail"))
async def handle_user_detail(callback: CallbackQuery, callback_data: AdminCB) -> None:
    """Показать детали пользователя."""
    user_db_id = int(callback_data.value)

    async with async_session_factory() as session:
        user = await UserRepository(session).get_by_id(user_db_id)

    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return

    async with async_session_factory() as session:
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
            f"💳 Баланс: <b>{user.credits} кр</b>\n"
            f"📦 Тариф: <b>{plan_value}</b>\n"
            f"📊 Кампаний: <b>{campaign_count}</b>\n\n"
            f"📅 Регистрация: {created_at}\n"
            f"Статус: {ban_emoji}\n\n"
            f"Реферальный код: <code>{user.referral_code}</code>"
        )

        await safe_callback_edit(
            callback,
            text,
            reply_markup=get_user_actions_kb(
                user_db_id, user.is_banned, user.notifications_enabled
            ),
        )
    await callback.answer()


# ==================== БАН / РАЗБАН ====================


@router.callback_query(AdminCB.filter(F.action == "toggle_ban"))
async def handle_toggle_ban(
    callback: CallbackQuery, callback_data: AdminCB, state: FSMContext
) -> None:
    """Быстрый бан/разбан пользователя из профиля."""
    user_db_id = int(callback_data.value)

    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_id(user_db_id)

    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return

    if user.is_admin:
        await callback.answer("❌ Нельзя забанить администратора", show_alert=True)
        return

    new_status = not user.is_banned
    await user_repo.update(user_db_id, {"is_banned": new_status})

    action = "забанен 🚫" if new_status else "разбанен ✅"
    logger.warning(f"Admin {callback.from_user.id} {action} user {user.telegram_id}")

    await handle_user_detail(callback, AdminCB(action="user_detail", value=str(user_db_id)), state)
    await callback.answer(f"✅ Пользователь {action}")


@router.callback_query(AdminCB.filter(F.action == "toggle_user_notif"))
async def admin_toggle_user_notif(
    callback: CallbackQuery, callback_data: AdminCB, state: FSMContext
) -> None:
    """Админ переключает уведомления конкретного пользователя."""
    user_db_id = int(callback_data.value)

    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        new_state = await user_repo.toggle_notifications_by_db_id(user_db_id)

    status = "включены 🔔" if new_state else "выключены 🔕"
    await callback.answer(f"Уведомления {status}")
    await handle_user_detail(callback, AdminCB(action="user_detail", value=str(user_db_id)), state)


@router.callback_query(AdminCB.filter(F.action == "ban_user"))
async def handle_ban_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Начать процесс бана пользователя (ручной ввод ID)."""
    await state.set_state(AdminBanStates.waiting_user_id)
    await safe_callback_edit(
        callback,
        "🚫 <b>Бан пользователя</b>\n\nВведите Telegram ID пользователя:",
        reply_markup=get_back_kb(),
    )
    await callback.answer()


@router.message(AdminBanStates.waiting_user_id)
async def handle_ban_user_id(message: Message, state: FSMContext) -> None:
    """Обработать ввод Telegram ID для бана."""
    if not message.text or not message.text.isdigit():
        await message.answer("❌ Введите числовой Telegram ID.")
        return

    telegram_id = int(message.text)

    async with async_session_factory() as session:
        user = await UserRepository(session).get_by_telegram_id(telegram_id)

    if not user:
        await message.answer("❌ Пользователь не найден.")
        await state.clear()
        return

    if user.is_admin:
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
    """Обработать причину бана и выполнить бан."""
    if message.text and message.text.strip().lower() in ["/cancel", "отмена", "cancel"]:
        await state.clear()
        await message.answer("✖ Бан отменен.", reply_markup=get_admin_main_kb())
        return

    data = await state.get_data()
    reason = message.text
    target_db_id = data["target_db_id"]

    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_id(target_db_id)

        if not user:
            await message.answer("❌ Пользователь не найден.")
            await state.clear()
            return

        # mypy type narrowing: user is guaranteed non-None after the check
        new_status = not user.is_banned
        await user_repo.update(target_db_id, {"is_banned": new_status})

        action = "забанен 🚫" if new_status else "разбанен ✅"
        logger.info(
            f"Admin {message.from_user.id} {action} user {user.telegram_id}. Reason: {reason}"  # type: ignore[union-attr]
        )

    await message.answer(
        f"✅ Пользователь {action}\nПричина: {reason}", reply_markup=get_admin_main_kb()
    )
    await state.clear()


# ==================== УПРАВЛЕНИЕ БАЛАНСОМ ====================


@router.callback_query(AdminCB.filter(F.action == "edit_balance"))
async def handle_edit_balance(
    callback: CallbackQuery, callback_data: AdminCB, state: FSMContext
) -> None:
    """Начать изменение баланса пользователя из профиля."""
    user_db_id = int(callback_data.value)

    async with async_session_factory() as session:
        user = await UserRepository(session).get_by_id(user_db_id)

    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return

    await state.update_data(target_db_id=user_db_id, target_telegram_id=user.telegram_id)
    await state.set_state(AdminBalanceStates.waiting_amount)

    await safe_callback_edit(
        callback,
        f"💰 <b>Изменение баланса пользователя</b>\n\n"
        f"👤 {user.full_name} (Telegram ID: <code>{user.telegram_id}</code>)\n"
        f"💳 Текущий баланс: <b>{user.credits} кр</b>\n\n"
        "Введите сумму изменения:\n"
        "<code>+500</code> — пополнить на 500 кр\n"
        "<code>-200</code> — списать 200 кр\n\n"
        "Или введите /cancel для отмены",
        reply_markup=get_back_kb(),
    )
    await callback.answer()


@router.callback_query(AdminCB.filter(F.action == "balance_manage"))
async def handle_balance_manage(callback: CallbackQuery, state: FSMContext) -> None:
    """Начать изменение баланса пользователя (ручной ввод ID)."""
    await state.set_state(AdminBalanceStates.waiting_user_id)
    await safe_callback_edit(
        callback,
        "💰 <b>Изменение баланса пользователя</b>\n\nВведите Telegram ID пользователя:",
        reply_markup=get_back_kb(),
    )
    await callback.answer()


@router.message(AdminBalanceStates.waiting_user_id)
async def handle_balance_user_id(message: Message, state: FSMContext) -> None:
    """Обработать ввод Telegram ID для изменения баланса."""
    if not message.text or not message.text.isdigit():
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
        f"💳 Текущий баланс: <b>{user.credits} кр</b>\n\n"
        "Введите сумму изменения:\n"
        "<code>+500</code> — пополнить на 500 кр\n"
        "<code>-200</code> — списать 200 кр"
    )


@router.message(AdminBalanceStates.waiting_amount)
async def handle_balance_amount(message: Message, state: FSMContext) -> None:
    """Обработать сумму изменения баланса."""
    if not message.text:
        await message.answer("Пожалуйста, введите сумму.")
        return
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
    """Обработать причину и выполнить изменение баланса."""
    if message.text and message.text.strip().lower() in ["/cancel", "отмена", "cancel"]:
        await state.clear()
        await message.answer("✖ Изменение баланса отменено.", reply_markup=get_admin_main_kb())
        return

    data = await state.get_data()
    amount = int(Decimal(data["amount"]))
    target_db_id = data["target_db_id"]
    reason = message.text

    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_id(target_db_id)

        if not user:
            await message.answer("❌ Пользователь не найден.")
            await state.clear()
            return

        # mypy type narrowing: user is guaranteed non-None after the check
        new_credits = await user_repo.update_credits(target_db_id, amount)
        await session.commit()

        sign = "+" if amount > 0 else ""
        logger.info(
            f"Admin {message.from_user.id} changed credits of user {user.telegram_id} by {sign}{amount} кр. Reason: {reason}"  # type: ignore[union-attr]
        )

    await message.answer(
        f"✅ <b>Баланс изменён</b>\n\n"
        f"Изменение: <b>{sign}{amount} кр</b>\n"
        f"Новый баланс: <b>{new_credits} кр</b>\n"
        f"Причина: {reason}",
        reply_markup=get_admin_main_kb(),
    )
    await state.clear()


# ==================== BROADCAST РАССЫЛКА ====================


@router.callback_query(AdminCB.filter(F.action == "broadcast"))
async def handle_broadcast_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Начать broadcast рассылку."""
    await state.set_state(AdminBroadcastStates.waiting_message)
    await safe_callback_edit(
        callback,
        "📢 <b>Broadcast рассылка</b>\n\n"
        "Введите текст сообщения.\n"
        "Поддерживается HTML форматирование.\n\n"
        "⚠️ Сообщение получат <b>все</b> незабаненные пользователи.",
        reply_markup=get_back_kb(),
    )
    await callback.answer()


@router.message(AdminBroadcastStates.waiting_message)
async def handle_broadcast_message(message: Message, state: FSMContext) -> None:
    """Обработать текст рассылки."""
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
    """Выполнить broadcast рассылку."""

    data = await state.get_data()
    text = data["broadcast_text"]
    await state.clear()

    async with async_session_factory() as session:
        users = await UserRepository(session).find_many(User.is_banned == False, limit=1000)  # noqa: E712

    sent = 0
    failed = 0
    bot = callback.bot
    if bot is None:
        logger.error("Bot instance is None in admin broadcast handler")
        await callback.answer("Ошибка. Попробуйте позже.", show_alert=True)
        return

    for user in users:
        try:
            await bot.send_message(user.telegram_id, text, parse_mode="HTML")
            sent += 1
        except Exception as e:
            logger.error(f"Failed to send broadcast to {user.telegram_id}: {e}")
            failed += 1

    await safe_callback_edit(
        callback,
        f"✅ <b>Broadcast завершён</b>\n\n📤 Отправлено: <b>{sent}</b>\n❌ Ошибок: <b>{failed}</b>",
        reply_markup=get_admin_main_kb(),
    )
    await callback.answer()


# ==================== ЧЁРНЫЙ СПИСОК КАНАЛОВ ====================


@router.callback_query(AdminCB.filter(F.action.in_({"blacklist", "blacklist_page"})))
async def show_blacklist(callback: CallbackQuery, callback_data: AdminCB) -> None:
    """Список заблокированных каналов с пагинацией."""
    page = int(callback_data.value) if callback_data.value else 1
    per_page = 15

    async with async_session_factory() as session:
        chat_repo = ChatAnalyticsRepository(session)
        chats, total = await chat_repo.get_blacklisted(offset=(page - 1) * per_page, limit=per_page)

    total_pages = max(1, (total + per_page - 1) // per_page)

    if not chats:
        await safe_callback_edit(
            callback, "🚫 <b>Чёрный список каналов</b>\n\nСписок пуст.", reply_markup=get_back_kb()
        )
        return

    lines = [f"🚫 <b>Чёрный список</b> (всего: {total})\n"]
    for ch in chats:
        username = f"@{ch.username}" if ch.username else f"id:{ch.telegram_id}"
        reason = (ch.blacklisted_reason or "—")[:40]
        lines.append(f"• <code>{ch.id}</code> {username}\n  └ {reason}")

    await safe_callback_edit(
        callback, "\n".join(lines), reply_markup=get_blacklist_kb(page, total_pages)
    )
    await callback.answer()


@router.callback_query(AdminCB.filter(F.action == "unblacklist"))
async def unblacklist_channel(callback: CallbackQuery, callback_data: AdminCB) -> None:
    """Разблокировать канал — убрать из чёрного списка."""
    chat_db_id = int(callback_data.value)

    async with async_session_factory() as session:
        chat_repo = ChatAnalyticsRepository(session)
        await chat_repo.unblacklist(chat_db_id)

    await callback.answer("✅ Канал разблокирован", show_alert=False)


# ══════════════════════════════════════════════════════════════
# S-13: /platform — Dashboard счёта платформы
# ══════════════════════════════════════════════════════════════


@router.message(F.command == "platform")
async def cmd_platform(message: Message) -> None:
    """
    S-13: Показать счёт платформы (только для admin).

    Отображает:
    - escrow_reserved
    - payout_reserved
    - profit_accumulated
    - total_topups
    - total_payouts
    """
    async with async_session_factory() as session:
        from src.db.models.platform_account import PlatformAccount
        from src.db.repositories.platform_account_repo import PlatformAccountRepo

        # Получаем platform_account (singleton id=1)
        platform = await session.get(PlatformAccount, 1)

        if not platform:
            await message.answer("❌ PlatformAccount не найден")
            return

        text = (
            "🏦 <b>Счёт платформы</b>\n\n"
            f"🔒 Эскроу: <b>{platform.escrow_reserved:.2f} ₽</b>\n"
            f"⏳ К выплате: <b>{platform.payout_reserved:.2f} ₽</b>\n"
            f"💰 Прибыль: <b>{platform.profit_accumulated:.2f} ₽</b>\n\n"
            f"📊 Исторические данные:\n"
            f"Пополнений: <b>{platform.total_topups:.2f} ₽</b>\n"
            f"Выплачено: <b>{platform.total_payouts:.2f} ₽</b>\n\n"
            f"🕐 Обновлено: <b>{platform.updated_at.strftime('%d.%m.%Y %H:%M')}</b>"
        )

        await message.answer(text)
