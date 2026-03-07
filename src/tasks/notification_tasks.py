"""
Notification tasks для уведомлений пользователей.
"""

import asyncio
import logging
from decimal import Decimal
from typing import Any

from src.db.repositories.user_repo import UserRepository
from src.db.session import async_session_factory
from src.tasks.celery_app import BaseTask, celery_app

logger = logging.getLogger(__name__)


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
        user_repo = UserRepository(session)

        # Получаем пользователей с балансом < 50 RUB
        users = await user_repo.get_users_for_notification(
            min_balance=Decimal("0.00"),
            max_balance=Decimal("50.00"),
        )

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
                await _notify_low_balance(user.telegram_id, user.credits)
                stats["notified"] += 1

            except Exception as e:
                logger.error(f"Error notifying user {user.telegram_id}: {e}")
                stats["errors"] += 1

        return stats


async def _notify_low_balance(telegram_id: int, credits: int) -> None:
    """
    Отправить уведомление о низком балансе.

    Args:
        telegram_id: Telegram ID пользователя.
        credits: Текущий баланс в кредитах.
    """
    # Импортируем aiogram Bot
    from aiogram import Bot
    from aiogram.exceptions import TelegramForbiddenError

    from src.config.settings import settings

    bot = Bot(token=settings.bot_token)

    message = (
        f"⚠️ <b>Низкий баланс</b>\n\n"
        f"Ваш баланс: {credits} кр\n"
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
        if "chat not found" in error_str or "blocked" in error_str:
            logger.warning(f"User {telegram_id} blocked the bot: {e}")
        else:
            logger.error(f"Error sending low balance notification to {telegram_id}: {e}")
        raise
    finally:
        await bot.session.close()


@celery_app.task(name="notifications:notify_campaign_status", bind=True, max_retries=3)
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
            if "chat not found" in error_str or "blocked" in error_str:
                logger.warning(
                    f"User {user_id} blocked the bot, skipping campaign notification"
                )
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
    try:
        asyncio.run(_notify_user_async(telegram_id, message, parse_mode))
        return True
    except Exception as e:
        # Игнорируем ожидаемые ошибки (пользователь заблокировал бота)
        error_str = str(e).lower()
        if "chat not found" in error_str or "blocked" in error_str:
            logger.warning(
                f"User {telegram_id} blocked the bot or chat is inaccessible, "
                f"skipping notification: {e}"
            )
            return False
        logger.error(f"Error notifying user {telegram_id}: {e}")
        return False


async def _notify_user_async(
    telegram_id: int,
    message: str,
    parse_mode: str = "HTML",
) -> None:
    """
    Асинхронная отправка уведомления.

    Args:
        telegram_id: Telegram ID пользователя.
        message: Текст сообщения.
        parse_mode: Режим парсинга.
    """
    from aiogram import Bot
    from aiogram.exceptions import TelegramForbiddenError

    from src.config.settings import settings

    bot = Bot(token=settings.bot_token)

    try:
        await bot.send_message(telegram_id, message, parse_mode=parse_mode)
    except TelegramForbiddenError:
        # Пользователь заблокировал бота — это нормальная ситуация
        logger.warning(f"User {telegram_id} blocked the bot")
        raise  # Пробрасываем выше для обработки в notify_user
    except Exception as e:
        # Другие ошибки (chat not found, network issues)
        error_str = str(e).lower()
        if "chat not found" in error_str or "blocked" in error_str:
            logger.warning(f"User {telegram_id} blocked the bot or chat is inaccessible: {e}")
        else:
            logger.error(f"Error sending notification to {telegram_id}: {e}")
        raise
    finally:
        await bot.session.close()


# ─────────────────────────────────────────────
# Уведомления владельца о заявках (Спринт 1)
# ─────────────────────────────────────────────

@celery_app.task(name="notifications:notify_owner_new_placement")
def notify_owner_new_placement_task(placement_id: int) -> bool:
    """
    Уведомляет владельца канала о новой заявке на размещение.
    Celery-обёртка для async функции.
    """
    import asyncio

    async def _notify_async() -> bool:
        from aiogram import Bot
        from aiogram.exceptions import TelegramForbiddenError
        from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

        from src.config.settings import settings
        from src.db.models.analytics import TelegramChat
        from src.db.models.campaign import Campaign
        from src.db.models.mailing_log import MailingLog
        from src.db.models.user import User

        async with async_session_factory() as session:
            placement = await session.get(MailingLog, placement_id)
            if not placement:
                return False

            channel = await session.get(TelegramChat, placement.chat_id)
            if not channel or not channel.owner_user_id:
                return False

            campaign = await session.get(Campaign, placement.campaign_id)
            if not campaign:
                return False

            owner = await session.get(User, channel.owner_user_id)
            if not owner or not owner.notifications_enabled:
                return False

            payout_amount = float(channel.price_per_post or 0) * 0.8

            keyboard_markup = InlineKeyboardMarkup(
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

            message = (
                f"📢 <b>Новая заявка на размещение в @{channel.username or channel.title}</b>\n\n"
                f"💬 Текст объявления:\n{campaign.text[:500]}{'...' if len(campaign.text) > 500 else ''}\n\n"
                f"📅 Дата публикации: {placement.created_at.strftime('%d.%m.%Y %H:%M')}\n"
                f"💸 Выплата: {payout_amount:.0f} ₽\n\n"
                f"⏰ Автоодобрение через 24 часа если не ответите"
            )

            bot = Bot(token=settings.bot_token)
            try:
                await bot.send_message(
                    owner.telegram_id,
                    message,
                    parse_mode="HTML",
                    reply_markup=keyboard_markup,
                )
                return True
            except TelegramForbiddenError:
                logger.warning(
                    f"Owner {owner.telegram_id} blocked the bot, skipping placement notification"
                )
                return False
            except Exception as e:
                error_str = str(e).lower()
                if "chat not found" in error_str or "blocked" in error_str:
                    logger.warning(
                        f"Owner {owner.telegram_id} blocked the bot: {e}"
                    )
                    return False
                logger.error(f"Error notifying owner about placement {placement_id}: {e}")
                return False
            finally:
                await bot.session.close()

    try:
        return asyncio.run(_notify_async())
    except Exception as e:
        logger.error(f"Error notifying owner about placement {placement_id}: {e}")
        return False


# ─────────────────────────────────────────────
# Уведомления о выплатах (Спринт 1)
# ─────────────────────────────────────────────

@celery_app.task(name="notifications:notify_payout_created")
def notify_payout_created_task(payout_id: int) -> bool:
    """
    Уведомляет владельца о создании выплаты.
    """
    import asyncio

    async def _notify_async() -> bool:
        from aiogram import Bot
        from aiogram.exceptions import TelegramForbiddenError

        from src.config.settings import settings
        from src.db.models.payout import Payout
        from src.db.models.user import User

        async with async_session_factory() as session:
            payout = await session.get(Payout, payout_id)
            if not payout:
                return False

            owner = await session.get(User, payout.owner_id)
            if not owner or not owner.notifications_enabled:
                return False

            message = (
                f"💰 <b>Начислена выплата</b>\n\n"
                f"Сумма: {payout.amount:.0f} ₽\n"
                f"Статус: ожидает выплаты\n\n"
                f"Выплата будет обработана в ближайшее время."
            )

            bot = Bot(token=settings.bot_token)
            try:
                await bot.send_message(
                    owner.telegram_id,
                    message,
                    parse_mode="HTML",
                )
                return True
            except TelegramForbiddenError:
                logger.warning(
                    f"Owner {owner.telegram_id} blocked the bot, skipping payout notification"
                )
                return False
            except Exception as e:
                error_str = str(e).lower()
                if "chat not found" in error_str or "blocked" in error_str:
                    logger.warning(
                        f"Owner {owner.telegram_id} blocked the bot: {e}"
                    )
                    return False
                logger.error(f"Error notifying payout created {payout_id}: {e}")
                return False
            finally:
                await bot.session.close()

    try:
        return asyncio.run(_notify_async())
    except Exception as e:
        logger.error(f"Error notifying payout created {payout_id}: {e}")
        return False


@celery_app.task(name="notifications:notify_payout_paid")
def notify_payout_paid_task(payout_id: int) -> bool:
    """
    Уведомляет владельца о выплате.
    """
    import asyncio

    async def _notify_async() -> bool:
        from aiogram import Bot
        from aiogram.exceptions import TelegramForbiddenError

        from src.config.settings import settings
        from src.db.models.payout import Payout
        from src.db.models.user import User

        async with async_session_factory() as session:
            payout = await session.get(Payout, payout_id)
            if not payout:
                return False

            owner = await session.get(User, payout.owner_id)
            if not owner or not owner.notifications_enabled:
                return False

            tx_info = f"\nTX: {payout.tx_hash[:10]}..." if payout.tx_hash else ""

            message = (
                f"✅ <b>Выплата произведена!</b>\n\n"
                f"Сумма: {payout.amount:.0f} ₽\n"
                f"Статус: выплачено{tx_info}\n\n"
                f"Средства зачислены на ваш счёт."
            )

            bot = Bot(token=settings.bot_token)
            try:
                await bot.send_message(
                    owner.telegram_id,
                    message,
                    parse_mode="HTML",
                )
                return True
            except TelegramForbiddenError:
                logger.warning(
                    f"Owner {owner.telegram_id} blocked the bot, skipping payout notification"
                )
                return False
            except Exception as e:
                error_str = str(e).lower()
                if "chat not found" in error_str or "blocked" in error_str:
                    logger.warning(
                        f"Owner {owner.telegram_id} blocked the bot: {e}"
                    )
                    return False
                logger.error(f"Error notifying payout paid {payout_id}: {e}")
                return False
            finally:
                await bot.session.close()

    try:
        return asyncio.run(_notify_async())
    except Exception as e:
        logger.error(f"Error notifying payout paid {payout_id}: {e}")
        return False


# ─────────────────────────────────────────────
# Уведомления для рекламодателей (Спринт 5)
# ─────────────────────────────────────────────

@celery_app.task(name="notifications:notify_post_published")
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
        return await _notify_user_async(advertiser_id, text, "HTML")

    try:
        return asyncio.run(_notify())
    except Exception as e:
        logger.error(f"Error notifying post published: {e}")
        return False


@celery_app.task(name="notifications:notify_campaign_finished")
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
        from aiogram import Bot
        from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

        from src.config.settings import settings

        text = (
            f"📊 <b>Кампания '{campaign_title}' завершена</b>.\n\n"
            f"Опубликовано: {published_count}/{total_count}\n"
            f"Суммарный охват: ~{total_views:,} просмотров\n\n"
            f"Отчёт готов."
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📊 Посмотреть аналитику", callback_data=f"analytics:by_campaign:{campaign_id}")]
            ]
        )

        bot = Bot(token=settings.bot_token)
        try:
            await bot.send_message(
                advertiser_id,
                text,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
            return True
        finally:
            await bot.session.close()

    try:
        return asyncio.run(_notify())
    except Exception as e:
        logger.error(f"Error notifying campaign finished: {e}")
        return False


@celery_app.task(name="notifications:notify_placement_rejected")
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
        return await _notify_user_async(advertiser_id, text, "HTML")

    try:
        return asyncio.run(_notify())
    except Exception as e:
        logger.error(f"Error notifying placement rejected: {e}")
        return False


@celery_app.task(name="notifications:notify_changes_requested")
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
        return await _notify_user_async(advertiser_id, text, "HTML")

    try:
        return asyncio.run(_notify())
    except Exception as e:
        logger.error(f"Error notifying changes requested: {e}")
        return False


@celery_app.task(name="notifications:notify_low_balance_enhanced")
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
        from aiogram import Bot
        from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

        from src.config.settings import settings

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

        bot = Bot(token=settings.bot_token)
        try:
            await bot.send_message(
                advertiser_id,
                text,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
            return True
        finally:
            await bot.session.close()

    try:
        return asyncio.run(_notify())
    except Exception as e:
        logger.error(f"Error notifying low balance enhanced: {e}")
        return False


@celery_app.task(name="notifications:notify_plan_expiring")
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
        return await _notify_user_async(advertiser_id, text, "HTML")

    try:
        return asyncio.run(_notify())
    except Exception as e:
        logger.error(f"Error notifying plan expiring: {e}")
        return False


# ─────────────────────────────────────────────
# Уведомления геймификации (Спринт 5)
# ─────────────────────────────────────────────

@celery_app.task(name="notifications:notify_badge_earned")
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
        return await _notify_user_async(user_id, text, "HTML")

    try:
        return asyncio.run(_notify())
    except Exception as e:
        logger.error(f"Error notifying badge earned: {e}")
        return False


@celery_app.task(name="notifications:notify_level_up")
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
    LEVEL_NAMES = {
        1: "Новичок 🌱",
        2: "Участник ⭐",
        3: "Активный 🔥",
        4: "Опытный 💎",
        5: "Профи 🚀",
        6: "Эксперт 🎯",
        7: "Мастер 👑",
    }

    LEVEL_NEXT_PRIVILEGE = {
        1: "расширенные фильтры в каталоге каналов",
        2: "скидка 3% на все размещения",
        3: "скидка 7% + персональный менеджер",
        4: "скидка 10% + ранний доступ к B2B",
        5: "скидка 15% + белый лейбл отчётов",
        6: "API-доступ",
        7: None,
    }

    async def _notify() -> bool:
        level_name = LEVEL_NAMES.get(new_level, f"Уровень {new_level}")
        privilege = LEVEL_NEXT_PRIVILEGE.get(new_level - 1)

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

        return await _notify_user_async(user_id, text, "HTML")

    try:
        return asyncio.run(_notify())
    except Exception as e:
        logger.error(f"Error notifying level up: {e}")
        return False


@celery_app.task(name="notifications:notify_channel_top10")
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
        return await _notify_user_async(owner_id, text, "HTML")

    try:
        return asyncio.run(_notify())
    except Exception as e:
        logger.error(f"Error notifying channel top10: {e}")
        return False


@celery_app.task(name="notifications:notify_referral_bonus")
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
        return await _notify_user_async(referrer_id, text, "HTML")

    try:
        return asyncio.run(_notify())
    except Exception as e:
        logger.error(f"Error notifying referral bonus: {e}")
        return False


# ─────────────────────────────────────────────
# Еженедельный дайджест (Спринт 5)
# ─────────────────────────────────────────────

@celery_app.task(name="notifications:send_weekly_digest")
def send_weekly_digest() -> dict[str, int]:
    """
    Задача 9.3: Еженедельный дайджест для пользователей.
    Запускается каждый понедельник в 09:00 UTC.
    """
    from datetime import datetime, timedelta

    stats = {"sent": 0, "errors": 0}

    async def _send_digests() -> dict[str, int]:
        from sqlalchemy import func, select

        async with async_session_factory() as session:
            user_repo = UserRepository(session)

            # Получаем всех пользователей с включёнными уведомлениями
            from src.db.models.user import User
            stmt = select(User).where(User.is_active == True, User.notifications_enabled == True)
            result = await session.execute(stmt)
            users = list(result.scalars().all())

            for user in users:
                try:
                    # Определяем роль
                    from src.core.services.user_role_service import UserRoleService
                    user_role_service = UserRoleService()
                    user_context = await user_role_service.get_user_context(user.id)
                    role = user_context.role

                    # Получаем данные за последние 7 дней
                    from src.db.models.campaign import Campaign

                    seven_days_ago = datetime.now() - timedelta(days=7)

                    if role in ("advertiser", "both"):
                        # Дайджест рекламодателя
                        campaigns_count = await session.execute(
                            select(func.count(Campaign.id)).where(
                                Campaign.user_id == user.id,
                                Campaign.created_at >= seven_days_ago,
                            )
                        )
                        campaigns_count = campaigns_count.scalar_one() or 0

                        if campaigns_count == 0:
                            continue  # Не отправляем если нет кампаний

                        text = (
                            f"📊 <b>Итоги недели — RekHarborBot</b>\n\n"
                            f"Кампаний: {campaigns_count}\n"
                        )

                        # TODO: получить total_views и total_spent из БД
                        # if total_views:
                        #     text += f"Суммарный охват: {total_views:,}\n"
                        # if total_spent:
                        #     text += f"Потрачено: {total_spent} кр\n"

                        text += (
                            f"\n💳 Баланс: {user.credits} кр\n"
                            f"📦 Тариф: {user.plan.value if hasattr(user.plan, 'value') else user.plan}"
                        )

                        from aiogram import Bot
                        from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

                        from src.config.settings import settings

                        keyboard = InlineKeyboardMarkup(
                            inline_keyboard=[
                                [InlineKeyboardButton(text="📣 Создать кампанию", callback_data="main:create_menu")]
                            ]
                        )

                        bot = Bot(token=settings.bot_token)
                        try:
                            await bot.send_message(
                                user.telegram_id,
                                text,
                                parse_mode="HTML",
                                reply_markup=keyboard,
                            )
                            stats["sent"] += 1
                        finally:
                            await bot.session.close()

                    elif role == "owner":
                        # Дайджест владельца
                        # TODO: получить данные из БД
                        requests_count = 0  # Заглушка
                        approved_count = 0  # Заглушка
                        earned_credits = 0  # Заглушка

                        if requests_count == 0:
                            continue  # Не отправляем если нет заявок

                        text = (
                            f"📺 <b>Итоги недели</b>\n\n"
                            f"Заявок: {requests_count}\n"
                            f"Одобрено: {approved_count}\n"
                            f"Заработано: {earned_credits} кр\n"
                        )

                        # TODO: получить available_payout
                        available_payout = 0

                        text += f"\n💸 К выводу: {available_payout} кр"

                        from aiogram import Bot
                        from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

                        from src.config.settings import settings

                        keyboard = InlineKeyboardMarkup(
                            inline_keyboard=[
                                [InlineKeyboardButton(text="💸 Вывести средства", callback_data="main:payouts")]
                            ]
                        )

                        bot = Bot(token=settings.bot_token)
                        try:
                            await bot.send_message(
                                user.telegram_id,
                                text,
                                parse_mode="HTML",
                                reply_markup=keyboard,
                            )
                            stats["sent"] += 1
                        finally:
                            await bot.session.close()

                except Exception as e:
                    logger.error(f"Error sending digest to user {user.id}: {e}")
                    stats["errors"] += 1

            return stats

    try:
        result = asyncio.run(_send_digests())
        logger.info(f"Weekly digest completed: {result}")
        return result
    except Exception as e:
        logger.error(f"Error sending weekly digest: {e}")
        return {"sent": 0, "errors": 1}
