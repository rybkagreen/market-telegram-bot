"""
Notification tasks для уведомлений пользователей.
"""

import asyncio
import hashlib
import logging
from datetime import UTC
from decimal import Decimal
from typing import Any

from redis.asyncio import Redis

from src.config.settings import settings
from src.db.repositories.user_repo import UserRepository
from src.db.session import celery_async_session_factory as async_session_factory
from src.tasks.celery_app import BaseTask, celery_app

logger = logging.getLogger(__name__)

CHAT_NOT_FOUND = "chat not found"

# Redis клиент для дедупликации уведомлений
redis_client = Redis.from_url(settings.celery_broker_url, decode_responses=True)


@celery_app.task(bind=True, base=BaseTask, name="mailing:check_low_balance")
def check_low_balance(self) -> dict[str, Any]:
    """
    Проверить баланс пользователей и отправить уведомления о низком балансе.

    Returns:
        Статистика проверенных пользователей.
    """
    logger.info("Checking low balance users")

    try:
        stats = asyncio.run(_check_low_balance_async())
        logger.info(f"Low balance check completed: {stats}")
        return stats

    except Exception as e:
        logger.error(f"Error checking low balance: {e}")
        return {"error": str(e)}


async def _check_low_balance_async() -> dict[str, Any]:
    """
    Асинхронная проверка низкого баланса.

    Returns:
        Статистика.
    """

    async with async_session_factory() as session:
        from sqlalchemy import select as _select

        from src.db.models.user import User as _User

        # Получаем пользователей с балансом < 50 RUB
        _stmt = _select(_User).where(
            _User.is_active.is_(True),
            _User.balance_rub >= Decimal("0.00"),
            _User.balance_rub <= Decimal("50.00"),
        )
        _result = await session.execute(_stmt)
        users = list(_result.scalars().all())

        stats = {
            "total_checked": len(users),
            "notified": 0,
            "errors": 0,
        }

        for user in users:
            try:
                # Проверяем настройку уведомлений
                if not user.notifications_enabled:
                    logger.debug(f"Notifications disabled for user {user.telegram_id}, skipping")
                    continue

                # Отправляем уведомление
                await _notify_low_balance(user.telegram_id, user.balance_rub)
                stats["notified"] += 1

            except Exception as e:
                logger.error(f"Error notifying user {user.telegram_id}: {e}")
                stats["errors"] += 1

        return stats


async def _notify_low_balance(telegram_id: int, balance_rub: Decimal) -> None:
    """
    Отправить уведомление о низком балансе.

    Args:
        telegram_id: Telegram ID пользователя.
        balance_rub: Текущий баланс в рублях.
    """
    from aiogram.exceptions import TelegramForbiddenError

    from src.tasks._bot_factory import get_bot

    bot = get_bot()

    message = (
        f"⚠️ <b>Низкий баланс</b>\n\n"
        f"Ваш баланс: <b>{balance_rub:.2f} ₽</b>\n"
        f"Пополните баланс для продолжения использования бота.\n\n"
        f"Используйте команду /billing для пополнения."
    )

    try:
        await bot.send_message(telegram_id, message, parse_mode="HTML")
    except TelegramForbiddenError:
        logger.warning(f"User {telegram_id} blocked the bot, skipping low balance notification")
        raise
    except Exception as e:
        error_str = str(e).lower()
        if CHAT_NOT_FOUND in error_str or "blocked" in error_str:
            logger.warning(f"User {telegram_id} blocked the bot: {e}")
        else:
            logger.error(f"Error sending low balance notification to {telegram_id}: {e}")
        raise


@celery_app.task(
    name="notifications:notify_campaign_status", bind=True, max_retries=3, queue="notifications"
)
def notify_campaign_status(
    self,
    user_id: int,
    campaign_id: int,
    status: str,
    error_message: str = "",
) -> None:
    """
    Уведомить пользователя об изменении статуса кампании.

    Args:
        user_id: Telegram ID пользователя.
        campaign_id: ID кампании.
        status: Статус кампании (paused, banned, completed, error).
        error_message: Сообщение об ошибке (опционально).
    """

    async def _send() -> None:
        # НОВОЕ: проверяем настройку перед отправкой
        async with async_session_factory() as session:
            user_repo = UserRepository(session)
            user = await user_repo.get_by_telegram_id(user_id)

            if not user or not user.notifications_enabled:
                logger.debug(f"Notifications disabled for user {user_id}, skipping")
                return

        text = _get_campaign_message(campaign_id, status, error_message)
        try:
            asyncio.run(_notify_user_async(user_id, text, "HTML"))
        except Exception as exc:
            error_str = str(exc).lower()
            # Не повторяем попыток если пользователь заблокировал бота
            if CHAT_NOT_FOUND in error_str or "blocked" in error_str:
                logger.warning(f"User {user_id} blocked the bot, skipping campaign notification")
                return
            logger.warning(f"Failed to notify user {user_id} about campaign {campaign_id}: {exc}")
            raise self.retry(countdown=60, exc=exc) from exc

    asyncio.run(_send())


def _get_campaign_message(campaign_id: int, status: str, error_message: str = "") -> str:
    """Получить текст уведомления о кампании."""
    messages = {
        "paused": (
            f"⏸ <b>Кампания #{campaign_id} приостановлена</b>\n\n"
            f"Telegram ограничил отправку. Кампания продолжится автоматически."
        ),
        "banned": (
            f"🚫 <b>Кампания #{campaign_id} остановлена</b>\n\n"
            f"Telegram-аккаунт рассылки заблокирован. Обратитесь в поддержку."
        ),
        "completed": f"✅ <b>Кампания #{campaign_id} завершена!</b>",
        "error": (f"❌ <b>Ошибка в кампании #{campaign_id}</b>\n\n{error_message}"),
    }
    return messages.get(status, f"Статус кампании #{campaign_id}: {status}")


@celery_app.task(bind=True, base=BaseTask, name="mailing:notify_user")
def notify_user(
    self,
    telegram_id: int,
    message: str,
    parse_mode: str = "HTML",
) -> bool:
    """
    Отправить уведомление пользователю.

    Args:
        telegram_id: Telegram ID пользователя.
        message: Текст сообщения.
        parse_mode: Режим парсинга (HTML/Markdown).

    Returns:
        True если отправлено успешно.
    """
    # ✅ ПРОВЕРКА НА ДУБЛИКАТ — предотвращаем повторную отправку
    # Дедупликация в течение 5 минут по (telegram_id, hash(message))
    message_hash = hashlib.sha256(message.encode()).hexdigest()
    dedup_key = f"notification:{telegram_id}:{message_hash}"

    if asyncio.run(redis_client.exists(dedup_key)):
        logger.debug(f"Duplicate notification skipped: {dedup_key}")
        return False

    # Установить блокировку на 5 минут
    asyncio.run(redis_client.setex(dedup_key, 300, "1"))

    async def _send() -> bool:
        # Check notifications_enabled via DB lookup
        async with async_session_factory() as session:
            user_repo = UserRepository(session)
            user = await user_repo.get_by_telegram_id(telegram_id)

        if user is not None and not user.notifications_enabled:
            logger.info(
                "mailing:notify_user: notifications disabled for telegram_id=%s, skipping",
                telegram_id,
            )
            return False

        try:
            await _notify_user_async(telegram_id, message, parse_mode)
            return True
        except Exception as e:
            error_str = str(e).lower()
            if CHAT_NOT_FOUND in error_str or "blocked" in error_str:
                logger.warning(
                    f"User {telegram_id} blocked the bot or chat is inaccessible, "
                    f"skipping notification: {e}"
                )
                return False
            logger.error(f"Error notifying user {telegram_id}: {e}")
            return False

    return asyncio.run(_send())


async def _notify_user_async(
    telegram_id: int,
    message: str,
    parse_mode: str = "HTML",
    reply_markup: Any = None,
) -> None:
    """
    Low-level notification send. No notifications_enabled check.
    Use _notify_user_checked for user-facing notifications.

    Args:
        telegram_id: Telegram ID пользователя.
        message: Текст сообщения.
        parse_mode: Режим парсинга.
        reply_markup: Optional InlineKeyboardMarkup.
    """
    from aiogram.exceptions import TelegramForbiddenError

    from src.tasks._bot_factory import get_bot

    bot = get_bot()

    try:
        await bot.send_message(
            telegram_id, message, parse_mode=parse_mode, reply_markup=reply_markup
        )
    except TelegramForbiddenError:
        logger.warning(f"User {telegram_id} blocked the bot")
        raise
    except Exception as e:
        error_str = str(e).lower()
        if CHAT_NOT_FOUND in error_str or "blocked" in error_str:
            logger.warning(f"User {telegram_id} blocked the bot or chat is inaccessible: {e}")
        else:
            logger.error(f"Error sending notification to {telegram_id}: {e}")
        raise


async def _notify_user_checked(
    user_id: int,
    message: str,
    parse_mode: str = "HTML",
    reply_markup: Any = None,
) -> bool:
    """Send notification only if user.notifications_enabled is True.

    Args:
        user_id: Internal DB user.id (NOT telegram_id).
        message: Message text.
        parse_mode: Parse mode.
        reply_markup: Optional InlineKeyboardMarkup.

    Returns:
        True if message was sent, False if skipped or user not found.
    """
    from aiogram.exceptions import TelegramForbiddenError

    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_id(user_id)

    if user is None:
        logger.warning("_notify_user_checked: user_id=%s not found, skipping", user_id)
        return False

    if not user.notifications_enabled:
        logger.info("_notify_user_checked: notifications disabled for user_id=%s, skipping", user_id)
        return False

    try:
        await _notify_user_async(user.telegram_id, message, parse_mode, reply_markup)
        return True
    except TelegramForbiddenError:
        logger.warning(
            "_notify_user_checked: user %s (tg=%s) blocked the bot",
            user_id,
            user.telegram_id,
        )
        return False
    except Exception as e:
        logger.error("_notify_user_checked: failed for user_id=%s: %s", user_id, e)
        return False


# ─────────────────────────────────────────────
# Уведомления владельца о заявках (Спринт 1)
# ─────────────────────────────────────────────


def _build_placement_keyboard(placement_id: int) -> Any:
    """Собрать клавиатуру одобрения/отклонения заявки."""
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Одобрить",
                    callback_data=f"approve_placement:{placement_id}",
                ),
                InlineKeyboardButton(
                    text="❌ Отклонить",
                    callback_data=f"reject_placement:{placement_id}",
                ),
            ],
        ],
    )


def _build_placement_message(placement: Any, channel: Any, payout_amount: float) -> str:
    """Собрать текст уведомления о новой заявке."""
    ad_preview = placement.ad_text[:500] + ("..." if len(placement.ad_text) > 500 else "")
    channel_ref = channel.username or channel.title
    return (
        f"📢 <b>Новая заявка на размещение в @{channel_ref}</b>\n\n"
        f"💬 Текст объявления:\n{ad_preview}\n\n"
        f"📅 Дата публикации: {placement.created_at.strftime('%d.%m.%Y %H:%M')}\n"
        f"💸 Выплата: {payout_amount:.0f} ₽\n\n"
        f"⏰ Автоодобрение через 24 часа если не ответите"
    )


async def _send_owner_placement_notification(
    placement_id: int,
    owner_telegram_id: int,
    message: str,
    keyboard: Any,
) -> bool:
    """Отправить уведомление владельцу о новой заявке."""
    from aiogram.exceptions import TelegramForbiddenError

    from src.tasks._bot_factory import get_bot

    bot = get_bot()
    try:
        await bot.send_message(
            owner_telegram_id,
            message,
            parse_mode="HTML",
            reply_markup=keyboard,
        )
        return True
    except TelegramForbiddenError:
        logger.warning(
            f"Owner {owner_telegram_id} blocked the bot, skipping placement notification"
        )
        return False
    except Exception as e:
        error_str = str(e).lower()
        if CHAT_NOT_FOUND in error_str or "blocked" in error_str:
            logger.warning(f"Owner {owner_telegram_id} blocked the bot: {e}")
            return False
        logger.error(f"Error notifying owner about placement {placement_id}: {e}")
        return False


@celery_app.task(name="notifications:notify_owner_new_placement", queue="notifications")
def notify_owner_new_placement_task(placement_id: int) -> bool:
    """
    Уведомляет владельца канала о новой заявке на размещение.
    Celery-обёртка для async функции.
    """
    import asyncio

    async def _notify_async() -> bool:
        from src.db.models.placement_request import PlacementRequest
        from src.db.models.telegram_chat import TelegramChat
        from src.db.models.user import User

        async with async_session_factory() as session:
            placement = await session.get(PlacementRequest, placement_id)
            if not placement:
                return False

            channel = await session.get(TelegramChat, placement.channel_id)
            if not channel or not channel.owner_id:
                return False

            owner = await session.get(User, channel.owner_id)
            if not owner or not owner.notifications_enabled:
                return False

            payout_amount = 0.0
            keyboard = _build_placement_keyboard(placement_id)
            message = _build_placement_message(placement, channel, payout_amount)

            return await _send_owner_placement_notification(
                placement_id, owner.telegram_id, message, keyboard
            )

    try:
        return asyncio.run(_notify_async())
    except Exception as e:
        logger.error(f"Error notifying owner about placement {placement_id}: {e}")
        return False


# ─────────────────────────────────────────────
# Уведомления о выплатах (Спринт 1)
# ─────────────────────────────────────────────


@celery_app.task(name="notifications:notify_owner_xp_for_publication", queue="notifications")
def notify_owner_xp_for_publication(
    owner_id: int,
    channel_id: int,
    placement_id: int,
) -> bool:
    """
    Спринт 5: Начислить XP владельцу за публикацию поста.

    Args:
        owner_id: ID владельца канала.
        channel_id: ID канала.
        placement_id: ID размещения.
    """

    async def _add_xp() -> bool:
        from src.core.services.xp_service import xp_service

        # 30 XP за каждую публикацию
        new_level, leveled_up = await xp_service.add_owner_xp(
            user_id=owner_id,
            amount=30,
            reason=f"publication:{placement_id}",
        )

        if leveled_up:
            logger.info(f"Owner {owner_id} leveled up to {new_level} (owner XP)")
            # Можно отправить уведомление о повышении уровня
            from src.tasks.notification_tasks import notify_level_up

            notify_level_up.delay(owner_id, new_level)

        return True

    try:
        return asyncio.run(_add_xp())
    except Exception as e:
        logger.error(f"Error adding owner XP: {e}")
        return False


async def _send_payout_message(
    payout_id: int, owner_telegram_id: int, message: str, log_label: str
) -> bool:
    """Отправить уведомление о выплате владельцу."""
    from aiogram.exceptions import TelegramForbiddenError

    from src.tasks._bot_factory import get_bot

    bot = get_bot()
    try:
        await bot.send_message(owner_telegram_id, message, parse_mode="HTML")
        return True
    except TelegramForbiddenError:
        logger.warning(f"Owner {owner_telegram_id} blocked the bot, skipping payout notification")
        return False
    except Exception as e:
        error_str = str(e).lower()
        if CHAT_NOT_FOUND in error_str or "blocked" in error_str:
            logger.warning(f"Owner {owner_telegram_id} blocked the bot: {e}")
            return False
        logger.error(f"Error notifying {log_label} {payout_id}: {e}")
        return False


@celery_app.task(name="notifications:notify_payout_created", queue="notifications")
def notify_payout_created_task(payout_id: int) -> bool:
    """
    Уведомляет владельца о создании выплаты.
    """
    import asyncio

    async def _notify_async() -> bool:
        from src.db.models.payout import PayoutRequest
        from src.db.models.user import User

        async with async_session_factory() as session:
            payout = await session.get(PayoutRequest, payout_id)
            if not payout:
                return False

            owner = await session.get(User, payout.owner_id)
            if not owner or not owner.notifications_enabled:
                return False

            message = (
                f"💰 <b>Начислена выплата</b>\n\n"
                f"Сумма: {payout.net_amount:.0f} ₽\n"
                f"Статус: ожидает выплаты\n\n"
                f"Выплата будет обработана в ближайшее время."
            )
            return await _send_payout_message(
                payout_id, owner.telegram_id, message, "payout created"
            )

    try:
        return asyncio.run(_notify_async())
    except Exception as e:
        logger.error(f"Error notifying payout created {payout_id}: {e}")
        return False


@celery_app.task(name="notifications:notify_payout_paid", queue="notifications")
def notify_payout_paid_task(payout_id: int) -> bool:
    """
    Уведомляет владельца о выплате.
    """
    import asyncio

    async def _notify_async() -> bool:
        from src.db.models.payout import PayoutRequest
        from src.db.models.user import User

        async with async_session_factory() as session:
            payout = await session.get(PayoutRequest, payout_id)
            if not payout:
                return False

            owner = await session.get(User, payout.owner_id)
            if not owner or not owner.notifications_enabled:
                return False

            message = (
                f"✅ <b>Выплата произведена!</b>\n\n"
                f"Сумма: {payout.net_amount:.0f} ₽\n"
                f"Статус: выплачено\n\n"
                f"Средства зачислены на ваш счёт."
            )
            return await _send_payout_message(payout_id, owner.telegram_id, message, "payout paid")

    try:
        return asyncio.run(_notify_async())
    except Exception as e:
        logger.error(f"Error notifying payout paid {payout_id}: {e}")
        return False


# ─────────────────────────────────────────────
# Уведомления для рекламодателей (Спринт 5)
# ─────────────────────────────────────────────


@celery_app.task(name="notifications:notify_post_published", queue="notifications")
def notify_post_published(
    advertiser_id: int,
    channel_username: str,
    expected_views: int,
) -> bool:
    """
    Задача 9.2: Уведомление после публикации поста.

    Args:
        advertiser_id: ID рекламодателя.
        channel_username: Username канала.
        expected_views: Ожидаемый охват.
    """

    async def _notify() -> bool:
        text = (
            f"✅ <b>Пост опубликован в @{channel_username}</b>.\n\n"
            f"Ожидаемый охват: ~{expected_views:,} просмотров."
        )
        await _notify_user_checked(advertiser_id, text)
        return True

    try:
        return asyncio.run(_notify())
    except Exception as e:
        logger.error(f"Error notifying post published: {e}")
        return False


@celery_app.task(name="notifications:notify_campaign_finished", queue="notifications")
def notify_campaign_finished(
    advertiser_id: int,
    campaign_title: str,
    published_count: int,
    total_count: int,
    total_views: int,
    campaign_id: int,
) -> bool:
    """
    Задача 9.2: Уведомление о завершении кампании.

    Args:
        advertiser_id: ID рекламодателя.
        campaign_title: Название кампании.
        published_count: Количество опубликованных.
        total_count: Всего планировалось.
        total_views: Суммарный охват.
        campaign_id: ID кампании для кнопки.
    """

    async def _notify() -> bool:
        from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

        text = (
            f"📊 <b>Кампания '{campaign_title}' завершена</b>.\n\n"
            f"Опубликовано: {published_count}/{total_count}\n"
            f"Суммарный охват: ~{total_views:,} просмотров\n\n"
            f"Отчёт готов."
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📊 Посмотреть аналитику",
                        callback_data=f"analytics:by_campaign:{campaign_id}",
                    )
                ]
            ]
        )

        await _notify_user_checked(advertiser_id, text, reply_markup=keyboard)
        return True

    try:
        return asyncio.run(_notify())
    except Exception as e:
        logger.error(f"Error notifying campaign finished: {e}")
        return False


@celery_app.task(name="notifications:notify_placement_rejected", queue="notifications")
def notify_placement_rejected(
    advertiser_id: int,
    channel_username: str,
    reason_code: str,
    refund_amount: int,
    campaign_id: int,
) -> bool:
    """
    Задача 9.2: Уведомление об отклонении заявки.

    Args:
        advertiser_id: ID рекламодателя.
        channel_username: Username канала.
        reason_code: Код причины.
        refund_amount: Сумма возврата.
        campaign_id: ID кампании.
    """
    reason_texts = {
        "topic": "не подходящая тематика",
        "text_quality": "качество текста",
        "timing": "неудобное время",
        "price": "низкая цена",
        "paused": "канал временно не принимает рекламу",
        "other": "другая причина",
    }

    async def _notify() -> bool:
        reason = reason_texts.get(reason_code, reason_code)
        text = (
            f"❌ <b>@{channel_username} отклонил заявку</b>.\n\n"
            f"Причина: {reason}\n"
            f"Средства {refund_amount} кр вернулись на ваш баланс."
        )
        await _notify_user_checked(advertiser_id, text)
        return True

    try:
        return asyncio.run(_notify())
    except Exception as e:
        logger.error(f"Error notifying placement rejected: {e}")
        return False


@celery_app.task(name="notifications:notify_changes_requested", queue="notifications")
def notify_changes_requested(
    advertiser_id: int,
    channel_username: str,
    campaign_title: str,
) -> bool:
    """
    Задача 9.2: Уведомление о запросе правок.

    Args:
        advertiser_id: ID рекламодателя.
        channel_username: Username канала.
        campaign_title: Название кампании.
    """

    async def _notify() -> bool:
        text = (
            f"✏️ <b>Владелец @{channel_username} просит исправить текст</b>.\n\n"
            f"Кампания: '{campaign_title}'\n"
            f"Канал: @{channel_username}\n\n"
            f"Отредактируйте текст кампании и отправьте заявку повторно."
        )
        await _notify_user_checked(advertiser_id, text)
        return True

    try:
        return asyncio.run(_notify())
    except Exception as e:
        logger.error(f"Error notifying changes requested: {e}")
        return False


@celery_app.task(name="notifications:notify_low_balance_enhanced", queue="notifications")
def notify_low_balance_enhanced(
    advertiser_id: int,
    current_balance: int,
    campaign_title: str,
    campaign_cost: int,
) -> bool:
    """
    Задача 9.2: Уведомление о низком балансе для кампании.

    Args:
        advertiser_id: ID рекламодателя.
        current_balance: Текущий баланс.
        campaign_title: Название кампании.
        campaign_cost: Стоимость кампании.
    """

    async def _notify() -> bool:
        from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

        deficit = campaign_cost - current_balance

        text = (
            f"⚠️ <b>Баланс заканчивается</b>.\n\n"
            f"Текущий баланс: {current_balance} кр\n"
            f"Запланирована кампания '{campaign_title}' на {campaign_cost} кр\n"
            f"❌ Не хватает: {deficit} кр"
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="💰 Пополнить баланс", callback_data="main:balance")]
            ]
        )

        await _notify_user_checked(advertiser_id, text, reply_markup=keyboard)
        return True

    try:
        return asyncio.run(_notify())
    except Exception as e:
        logger.error(f"Error notifying low balance enhanced: {e}")
        return False


@celery_app.task(name="notifications:notify_plan_expiring", queue="notifications")
def notify_plan_expiring(
    advertiser_id: int,
    plan_name: str,
    expires_at_str: str,
    renewal_cost: int,
    current_balance: int,
) -> bool:
    """
    Задача 9.2: Уведомление об истечении тарифа.

    Args:
        advertiser_id: ID рекламодателя.
        plan_name: Название тарифа.
        expires_at_str: Дата истечения.
        renewal_cost: Стоимость продления.
        current_balance: Текущий баланс.
    """

    async def _notify() -> bool:
        text = (
            f"📦 <b>Тариф {plan_name} истекает {expires_at_str}</b>.\n\n"
            f"Продление: {renewal_cost} кр\n"
            f"Баланс сейчас: {current_balance} кр"
        )
        await _notify_user_checked(advertiser_id, text)
        return True

    try:
        return asyncio.run(_notify())
    except Exception as e:
        logger.error(f"Error notifying plan expiring: {e}")
        return False


# ─────────────────────────────────────────────
# Уведомления геймификации (Спринт 5)
# ─────────────────────────────────────────────


@celery_app.task(name="notifications:notify_badge_earned", queue="notifications")
def notify_badge_earned(
    user_id: int,
    badge_name: str,
    xp_bonus: int,
    remaining_to_next_level: int,
) -> bool:
    """
    Задача 9.2: Уведомление о получении значка.

    Args:
        user_id: ID пользователя.
        badge_name: Название значка.
        xp_bonus: Бонус XP.
        remaining_to_next_level: Остаток до следующего уровня.
    """

    async def _notify() -> bool:
        text = (
            f"🏅 <b>Новый значок '{badge_name}'!</b>\n\n"
            f"+{xp_bonus} XP.\n"
            f"Осталось до уровня {remaining_to_next_level} XP."
        )
        await _notify_user_checked(user_id, text)
        return True

    try:
        return asyncio.run(_notify())
    except Exception as e:
        logger.error(f"Error notifying badge earned: {e}")
        return False


@celery_app.task(name="notifications:notify_level_up", queue="notifications")
def notify_level_up(
    user_id: int,
    new_level: int,
) -> bool:
    """
    Задача 9.2: Уведомление о новом уровне.

    Args:
        user_id: ID пользователя.
        new_level: Новый уровень.
    """
    # Импортируем словари из cabinet.py
    level_names = {
        1: "Новичок 🌱",
        2: "Участник ⭐",
        3: "Активный 🔥",
        4: "Опытный 💎",
        5: "Профи 🚀",
        6: "Эксперт 🎯",
        7: "Мастер 👑",
    }

    level_next_privilege = {
        1: "расширенные фильтры в каталоге каналов",
        2: "скидка 3% на все размещения",
        3: "скидка 7% + персональный менеджер",
        4: "скидка 10% + ранний доступ к B2B",
        5: "скидка 15% + белый лейбл отчётов",
        6: "API-доступ",
        7: None,
    }

    async def _notify() -> bool:
        level_name = level_names.get(new_level, f"Уровень {new_level}")
        privilege = level_next_privilege.get(new_level - 1)

        if privilege:
            text = (
                f"🎉 <b>Новый уровень {new_level} — {level_name}!</b>\n\n"
                f"<b>Новая привилегия:</b>\n"
                f"→ {privilege}"
            )
        else:
            text = (
                f"🎉 <b>Новый уровень {new_level} — {level_name}!</b>\n\n"
                f"Это максимальный уровень. Поздравляем!"
            )

        await _notify_user_checked(user_id, text)
        return True

    try:
        return asyncio.run(_notify())
    except Exception as e:
        logger.error(f"Error notifying level up: {e}")
        return False


@celery_app.task(name="notifications:notify_channel_top10", queue="notifications")
def notify_channel_top10(
    owner_id: int,
    channel_username: str,
    position: int,
    topic: str,
    total_in_topic: int,
) -> bool:
    """
    Задача 9.2: Уведомление о попадании в топ-10 каналов.

    Args:
        owner_id: ID владельца.
        channel_username: Username канала.
        position: Позиция в топе.
        topic: Тематика.
        total_in_topic: Всего каналов в тематике.
    """

    async def _notify() -> bool:
        text = (
            f"🏆 <b>@{channel_username} вошёл в топ-{position}!</b>\n\n"
            f"Тематика: {topic}\n"
            f"Всего каналов: {total_in_topic}\n\n"
            f"Метка 🏆 теперь отображается в карточке канала.\n"
            f"Ожидайте больше заявок от рекламодателей."
        )
        await _notify_user_checked(owner_id, text)
        return True

    try:
        return asyncio.run(_notify())
    except Exception as e:
        logger.error(f"Error notifying channel top10: {e}")
        return False


@celery_app.task(name="notifications:notify_referral_bonus", queue="notifications")
def notify_referral_bonus(
    referrer_id: int,
    referred_name: str,
    bonus_amount: int,
) -> bool:
    """
    Задача 9.2: Уведомление о реферальном бонусе.

    Args:
        referrer_id: ID реферера.
        referred_name: Имя реферала.
        bonus_amount: Сумма бонуса.
    """

    async def _notify() -> bool:
        text = (
            f"💰 <b>Ваш реферал {referred_name} пополнил баланс!</b>\n\n"
            f"Ваш бонус: +{bonus_amount} кр на баланс."
        )
        await _notify_user_checked(referrer_id, text)
        return True

    try:
        return asyncio.run(_notify())
    except Exception as e:
        logger.error(f"Error notifying referral bonus: {e}")
        return False


# ─────────────────────────────────────────────
# TASK 6: Автоодобрение заявок и напоминания
# ─────────────────────────────────────────────


@celery_app.task(name="notifications:auto_approve_placements", queue="mailing")
def auto_approve_placements() -> dict:
    """
    Автоодобрение заявок старше 24 часов.
    Запускать каждый час через Celery Beat.

    Логика:
    1. Найти все placements где:
       - status == "pending_approval"
       - created_at < now() - 24 часа
    2. Для каждого: установить status = "queued"
    3. Запустить задачу публикации
    4. Логировать: "Auto-approved placement {id} for channel {channel_id}"
    5. Вернуть {"approved": N}
    """
    import asyncio

    async def _auto_approve_async() -> dict:
        from datetime import datetime, timedelta

        from sqlalchemy import select

        from src.db.models.placement_request import PlacementRequest, PlacementStatus

        deadline = datetime.now(UTC) - timedelta(hours=24)
        approved_count = 0
        failed_count = 0

        async with async_session_factory() as session:
            stmt = (
                select(PlacementRequest)
                .where(
                    PlacementRequest.status == PlacementStatus.pending_owner,
                    PlacementRequest.created_at < deadline,
                )
                .with_for_update()
            )
            result = await session.execute(stmt)
            placements = result.scalars().all()

            for placement in placements:
                try:
                    placement.status = PlacementStatus.pending_payment
                    await session.flush()
                    approved_count += 1
                    logger.info(
                        f"Auto-approved placement {placement.id} for channel {placement.channel_id}"
                    )
                except Exception as e:
                    logger.error(f"Auto-approve failed for placement {placement.id}: {e}")
                    failed_count += 1

            await session.commit()

        return {
            "status": "ok",
            "approved": approved_count,
            "failed": failed_count,
        }

    try:
        return asyncio.run(_auto_approve_async())
    except Exception as e:
        logger.error(f"auto_approve_placements failed: {e}")
        return {"status": "error", "error": str(e), "approved": 0}


async def _send_placement_reminder(placement: Any, session: Any, bot: Any, now: Any) -> bool:
    """
    Отправить одно напоминание владельцу о заявке.

    Returns True если напоминание отправлено, False если пропущено.
    Raises TelegramForbiddenError / Exception при ошибке отправки.
    """
    from datetime import timedelta

    from src.db.models.telegram_chat import TelegramChat
    from src.db.models.user import User

    meta = placement.meta_json or {}
    if meta.get("reminder_sent"):
        logger.debug(f"Reminder already sent for placement {placement.id}")
        return False

    channel = await session.get(TelegramChat, placement.channel_id)
    if not channel or not channel.owner_id:
        return False

    owner = await session.get(User, channel.owner_id)
    if not owner or not owner.notifications_enabled:
        return False

    time_left = placement.created_at + timedelta(hours=24) - now
    hours_left = max(0, int(time_left.total_seconds() // 3600))

    message = (
        f"⏰ <b>Напоминание о заявке</b>\n\n"
        f"Заявка #{placement.id} ожидает решения.\n"
        f"Канал: @{channel.username or channel.title}\n"
        f"До автоодобрения: ~{hours_left} ч\n\n"
        f"Откройте «Мои каналы» → «Заявки»"
    )

    await bot.send_message(owner.telegram_id, message, parse_mode="HTML")

    meta["reminder_sent"] = True
    placement.meta_json = meta
    await session.flush()

    logger.info(f"Sent placement reminder to owner {owner.id} for placement {placement.id}")
    return True


@celery_app.task(name="notifications:notify_pending_placement_reminders", queue="mailing")
def notify_pending_placement_reminders() -> dict:
    """
    Напоминать владельцам о заявках старше 20 часов.
    Запускать каждые 2 часа через Celery Beat.

    Логика:
    1. Найти placements где:
       - status == "pending_approval"
       - created_at между (now()-24ч) и (now()-20ч)
       - напоминание ещё не отправлялось
    2. Отправить владельцу уведомление
    3. Вернуть {"sent": N}
    """
    import asyncio

    async def _notify_reminders_async() -> dict:
        from datetime import datetime, timedelta

        from aiogram.exceptions import TelegramForbiddenError
        from sqlalchemy import select

        from src.db.models.placement_request import PlacementRequest, PlacementStatus
        from src.tasks._bot_factory import get_bot

        now = datetime.now(UTC)
        older_than = now - timedelta(hours=24)
        newer_than = now - timedelta(hours=20)

        sent_count = 0
        error_count = 0

        async with async_session_factory() as session:
            stmt = select(PlacementRequest).where(
                PlacementRequest.status == PlacementStatus.pending_owner,
                PlacementRequest.created_at > older_than,
                PlacementRequest.created_at < newer_than,
            )
            result = await session.execute(stmt)
            placements = result.scalars().all()

            bot = get_bot()

            for placement in placements:
                try:
                    sent = await _send_placement_reminder(placement, session, bot, now)
                    if sent:
                        sent_count += 1
                except TelegramForbiddenError:
                    logger.warning(
                        f"Owner blocked bot, skipping reminder for placement {placement.id}"
                    )
                    error_count += 1
                except Exception as e:
                    logger.error(f"Error sending placement reminder: {e}")
                    error_count += 1

        return {
            "status": "ok",
            "sent": sent_count,
            "errors": error_count,
        }

    try:
        return asyncio.run(_notify_reminders_async())
    except Exception as e:
        logger.error(f"notify_pending_placement_reminders failed: {e}")
        return {"status": "error", "error": str(e), "sent": 0}


# ─────────────────────────────────────────────
# TASK 8: Уведомления об истечении тарифа
# ─────────────────────────────────────────────

_RENEWAL_COSTS: dict[str, int] = {
    "starter": 490,
    "pro": 1490,
    "business": 4990,
}


async def _notify_expiring_user(user: Any, bot: Any, session: Any, now: Any) -> bool:
    """
    Отправить уведомление об истекающем тарифе одному пользователю.

    Returns True если уведомление отправлено.
    """
    if not user.notifications_enabled:
        return False

    # ⚠️ ЗАЩИТА: пропускаем если уже отправляли сегодня
    if user.plan_expiry_notified_at and user.plan_expiry_notified_at.date() == now.date():
        logger.debug(f"User {user.id} already notified today, skipping")
        return False

    if user.plan_expires_at is None:
        logger.debug(f"User {user.id} has no plan expiry date, skipping")
        return False

    days_left = (user.plan_expires_at - now).days
    plan_name = user.plan.value if hasattr(user.plan, "value") else user.plan
    renewal_cost = _RENEWAL_COSTS.get(plan_name, 0)
    expires_str = user.plan_expires_at.strftime("%d.%m.%Y")

    message = (
        f"⚠️ <b>Ваш тариф {plan_name} истекает через {days_left} дн.</b>\n\n"
        f"Дата окончания: {expires_str}\n"
        f"Стоимость продления: {renewal_cost} ₽\n"
        f"Текущий баланс: {user.credits} ₽\n\n"
        f"Продлите тариф чтобы не потерять доступ к функциям.\n"
        f"Кабинет → Сменить тариф"
    )

    await bot.send_message(user.telegram_id, message, parse_mode="HTML")

    # ⚠️ Устанавливаем флаг что отправили уведомление
    user.plan_expiry_notified_at = now
    await session.flush()

    logger.info(f"Sent plan expiring notification to user {user.id}")
    return True


async def _downgrade_expired_user(user: Any, bot: Any, session: Any, now: Any) -> bool:
    """
    Сбросить тариф истёкшего пользователя и отправить уведомление.

    Returns True если пользователь был понижен в тарифе.
    """
    from src.db.models.user import UserPlan

    # ⚠️ ЗАЩИТА: если expires_at обновился (пользователь продлил) — не трогаем
    if user.plan_expires_at is None or user.plan_expires_at >= now:
        logger.info(f"User {user.id} renewed plan or has no expiry, skipping")
        return False

    old_plan = user.plan.value if hasattr(user.plan, "value") else user.plan
    user.plan = UserPlan.FREE
    user.plan_expires_at = None
    user.ai_uses_count = 0
    await session.flush()

    if user.notifications_enabled:
        message = (
            f"📦 <b>Ваш тариф {old_plan} истёк</b>\n\n"
            f"Тариф автоматически изменён на <b>FREE</b>.\n\n"
            f"Для доступа к расширенным функциям:\n"
            f"Кабинет → Сменить тариф"
        )
        await bot.send_message(user.telegram_id, message, parse_mode="HTML")

    logger.info(f"Downgraded user {user.id} from {old_plan} to FREE")
    return True


@celery_app.task(name="notifications:notify_expiring_plans", queue="mailing")
def notify_expiring_plans() -> dict:
    """
    Уведомить пользователей у кого тариф истекает через 3 дня.
    Запускать раз в день в 10:00 UTC.

    Логика:
    1. Найти users где:
       - plan != "free"
       - plan_expires_at между now() и now() + 3 дня
       - уведомление ещё не отправлялось сегодня
    2. Отправить уведомление
    3. Установить plan_expiry_notified_at = now
    4. Вернуть {"notified": N}
    """
    import asyncio

    async def _notify_expiring_async() -> dict:
        from datetime import datetime, timedelta

        from aiogram.exceptions import TelegramForbiddenError
        from sqlalchemy import select

        from src.db.models.user import User, UserPlan
        from src.tasks._bot_factory import get_bot

        now = datetime.now(UTC)
        three_days_later = now + timedelta(days=3)

        notified_count = 0
        error_count = 0

        async with async_session_factory() as session:
            stmt = select(User).where(
                User.plan != UserPlan.FREE,
                User.plan_expires_at != None,  # noqa: E711
                User.plan_expires_at <= three_days_later,
                User.plan_expires_at >= now,
            )
            result = await session.execute(stmt)
            users = result.scalars().all()

            bot = get_bot()

            for user in users:
                try:
                    sent = await _notify_expiring_user(user, bot, session, now)
                    if sent:
                        notified_count += 1
                except TelegramForbiddenError:
                    logger.warning(
                        f"User blocked bot, skipping plan expiring notification for user {user.id}"
                    )
                    error_count += 1
                except Exception as e:
                    logger.error(f"Error sending plan expiring notification: {e}")
                    error_count += 1

        return {
            "status": "ok",
            "notified": notified_count,
            "errors": error_count,
        }

    try:
        return asyncio.run(_notify_expiring_async())
    except Exception as e:
        logger.error(f"notify_expiring_plans failed: {e}")
        return {"status": "error", "error": str(e), "notified": 0}


@celery_app.task(name="notifications:notify_expired_plans", queue="mailing")
def notify_expired_plans() -> dict:
    """
    Уведомить пользователей у кого тариф только что истёк.
    Запускать раз в день в 10:05 UTC.

    Логика:
    1. Найти users где:
       - plan != "free"
       - plan_expires_at < now()
       - plan ещё не сброшен до "free"
    2. Сбросить plan = "free"
    3. Отправить уведомление о сбросе
    4. Вернуть {"downgraded": N}
    """
    import asyncio

    async def _notify_expired_async() -> dict:
        from datetime import datetime

        from aiogram.exceptions import TelegramForbiddenError
        from sqlalchemy import select

        from src.db.models.user import User, UserPlan
        from src.tasks._bot_factory import get_bot

        now = datetime.now(UTC)
        downgraded_count = 0
        error_count = 0

        async with async_session_factory() as session:
            stmt = select(User).where(
                User.plan != UserPlan.FREE,
                User.plan_expires_at != None,  # noqa: E711
                User.plan_expires_at < now,
            )
            result = await session.execute(stmt)
            users = result.scalars().all()

            bot = get_bot()

            for user in users:
                try:
                    downgraded = await _downgrade_expired_user(user, bot, session, now)
                    if downgraded:
                        downgraded_count += 1
                except TelegramForbiddenError:
                    logger.warning(
                        f"User blocked bot, skipping plan expired notification for user {user.id}"
                    )
                    # Всё равно сбрасываем тариф
                    downgraded_count += 1
                except Exception as e:
                    logger.error(f"Error expiring plan for user {user.id}: {e}")
                    error_count += 1

        return {
            "status": "ok",
            "downgraded": downgraded_count,
            "errors": error_count,
        }

    try:
        return asyncio.run(_notify_expired_async())
    except Exception as e:
        logger.error(f"notify_expired_plans failed: {e}")
        return {"status": "error", "error": str(e), "downgraded": 0}
