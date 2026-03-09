"""
Mailing Celery tasks.

Использует asyncio.run() для запуска async кода в синхронных Celery задачах.
asyncio.run() создаёт новый event loop для каждого вызова и закрывает его,
что гарантирует корректную работу в Celery worker контексте без конфликтов.

ВАЖНО: Каждая задача создаёт свою сессию и закрывает её корректно.
"""

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

from redis.asyncio import Redis

from src.config.settings import settings
from src.db.models.mailing_log import MailingLog, MailingStatus
from src.db.repositories.campaign_repo import CampaignRepository
from src.db.session import async_session_factory
from src.tasks.celery_app import BaseTask, celery_app

logger = logging.getLogger(__name__)

# Redis клиент для проверки дубликатов задач
redis_client = Redis.from_url(settings.celery_broker_url, decode_responses=True)


@celery_app.task(bind=True, base=BaseTask, name="mailing:send_campaign")
def send_campaign(self, campaign_id: int) -> dict[str, Any]:
    """
    Отправить кампанию по чатам.

    Args:
        campaign_id: ID кампании.

    Returns:
        Статистика отправки.
    """
    # ✅ ПРОВЕРКА НА ДУБЛИКАТ — предотвращаем повторный запуск
    task_key = f"campaign_running:{campaign_id}"
    existing_task_id = redis_client.get(task_key)

    if existing_task_id:
        logger.warning(
            f"Campaign {campaign_id} already running (task: {existing_task_id})"
        )
        return {"skipped": "Already running"}

    # Установить блокировку на 2 часа (максимальное время кампании)
    redis_client.setex(task_key, 7200, self.request.id)

    logger.info(f"Starting campaign {campaign_id}")

    try:
        return _execute_campaign(campaign_id)
    finally:
        # Очистить блокировку после завершения
        redis_client.delete(task_key)


def _execute_campaign(campaign_id: int) -> dict[str, Any]:
    """
    Основная логика выполнения кампании.

    Args:
        campaign_id: ID кампании.

    Returns:
        Статистика отправки.
    """
    async def _send_async() -> dict[str, Any]:
        from aiogram import Bot
        from sqlalchemy import select

        from src.db.models.analytics import TelegramChat
        from src.db.models.campaign import CampaignStatus
        from src.utils.telegram.sender import (
            AccountBannedError,
            CampaignSender,
            ChatBlockedError,
            ChatInvalidError,
        )

        async with async_session_factory() as session:
            campaign_repo = CampaignRepository(session)
            bot = Bot(token=settings.bot_token)
            sender = CampaignSender(bot=bot)

            # Получаем кампанию
            campaign = await campaign_repo.get_by_id(campaign_id)

            if not campaign:
                logger.error(f"Campaign {campaign_id} not found")
                return {"error": "Campaign not found"}

            if campaign.status not in [CampaignStatus.RUNNING, CampaignStatus.QUEUED]:
                logger.warning(f"Campaign {campaign_id} is not in running/queued state")
                return {"skipped": "Campaign not in running/queued state"}

            # Получаем чаты для рассылки
            chats = await sender.get_chats_for_campaign(campaign)

            if not chats:
                logger.warning(f"No chats found for campaign {campaign_id}")
                return {"no_chats": True}

            stats = {
                "total": len(chats),
                "sent": 0,
                "failed": 0,
                "skipped": 0,
            }

            complaint_thresholds = {
                "pause_24h": 3,
                "blacklist": 10,
            }

            for chat in chats:
                try:
                    # Отправляем сообщение
                    success = await sender.send_to_chat(
                        chat=chat,
                        text=campaign.text,
                        image_file_id=campaign.image_file_id,
                    )

                    if success:
                        stats["sent"] += 1

                        # ⚠️ ИСПРАВЛЕНИЕ: рассчитываем стоимость из цены канала
                        placement_cost = chat.price_per_post or 0

                        # Создаём запись в mailing_logs для начисления XP и выплаты
                        mailing_log = MailingLog(
                            campaign_id=campaign.id,
                            chat_id=chat.id,
                            chat_telegram_id=chat.telegram_id,
                            status=MailingStatus.SENT,
                            sent_at=datetime.now(UTC),
                            cost=placement_cost,  # Реальная цена канала
                        )
                        session.add(mailing_log)
                        await session.flush()  # Получаем mailing_log.id

                        # Task 1 & 2: Освобождаем средства эскроу после успешной публикации
                        from src.core.services.billing_service import billing_service

                        released = await billing_service.release_escrow_funds(mailing_log.id)
                        if not released:
                            logger.warning(f"Failed to release escrow for placement {mailing_log.id}")

                        # Спринт 5: Начисляем XP владельцу канала за публикацию
                        if chat.owner_user_id and mailing_log.id:
                            from src.tasks.notification_tasks import notify_owner_xp_for_publication

                            # 30 XP за публикацию поста
                            notify_owner_xp_for_publication.delay(
                                owner_id=chat.owner_user_id,
                                channel_id=chat.id,
                                placement_id=mailing_log.id,  # РЕАЛЬНЫЙ ID размещения
                            )

                        # TASK 3: Отправить запрос отзыва владельцу о рекламодателе
                        if chat.owner_user_id:
                            from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

                            from src.bot.main import bot as telegram_bot

                            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                                [InlineKeyboardButton(text="⭐⭐⭐⭐⭐", callback_data=f"owner_review:{mailing_log.id}:5")],
                                [InlineKeyboardButton(text="⭐⭐⭐⭐", callback_data=f"owner_review:{mailing_log.id}:4")],
                                [InlineKeyboardButton(text="⭐⭐⭐", callback_data=f"owner_review:{mailing_log.id}:3")],
                                [InlineKeyboardButton(text="⭐⭐", callback_data=f"owner_review:{mailing_log.id}:2")],
                                [InlineKeyboardButton(text="⭐", callback_data=f"owner_review:{mailing_log.id}:1")],
                                [InlineKeyboardButton(text="⏭ Пропустить", callback_data="owner_review_skip")],
                            ])

                            try:
                                await telegram_bot.send_message(
                                    chat_id=chat.owner_user_id,
                                    text=(
                                        "📋 <b>Оцените рекламодателя</b>\n\n"
                                        "Рекламный пост был размещён в вашем канале.\n"
                                        "Оцените качество рекламного контента:"
                                    ),
                                    reply_markup=keyboard,
                                    parse_mode="HTML",
                                )
                            except Exception as e:
                                logger.warning(f"Failed to send owner review request: {e}")
                    else:
                        stats["failed"] += 1

                        # ⚠️ ИСПРАВЛЕНИЕ: рассчитываем стоимость для возврата
                        placement_cost = chat.price_per_post or 0

                        # Создаём запись о неудачной отправке
                        mailing_log = MailingLog(
                            campaign_id=campaign.id,
                            chat_id=chat.id,
                            chat_telegram_id=chat.telegram_id,
                            status=MailingStatus.FAILED,
                            cost=placement_cost,  # Цена для возврата
                        )
                        session.add(mailing_log)
                        await session.flush()

                        # Task 3: Возврат средств за несостоявшееся размещение
                        from src.core.services.billing_service import billing_service

                        refunded = await billing_service.refund_failed_placement(mailing_log.id)
                        if not refunded:
                            logger.warning(f"Failed to refund placement {mailing_log.id}")

                except AccountBannedError as e:
                    # КРИТИЧНО: весь аккаунт забанен — останавливаем кампанию
                    campaign.status = CampaignStatus.ACCOUNT_BANNED
                    campaign.error_message = f"Account banned: {e}"
                    await session.commit()

                    logger.error(f"Campaign {campaign_id} stopped: account banned")

                    # Уведомить пользователя
                    try:
                        from src.tasks.notification_tasks import notify_campaign_status

                        notify_campaign_status.delay(
                            user_id=campaign.user_id,
                            campaign_id=campaign.id,
                            status="banned",
                        )
                    except Exception as notify_err:
                        logger.warning(f"Failed to send notification: {notify_err}")

                    return {"error": "Account banned", "campaign_id": campaign_id}

                except ChatBlockedError as e:
                    # Чат заблокировал бота — фиксируем жалобу
                    logger.warning(f"Chat {e.chat_id} blocked bot: {e}")
                    await _handle_chat_complaint(
                        e.chat_id, "ChatWriteForbidden", session, complaint_thresholds
                    )
                    stats["failed"] += 1

                    # Создаём запись о неудачной отправке
                    mailing_log = MailingLog(
                        campaign_id=campaign.id,
                        chat_id=chat.id,
                        chat_telegram_id=chat.telegram_id,
                        status=MailingStatus.FAILED,
                        error_msg=f"ChatBlocked: {e}",
                    )
                    session.add(mailing_log)
                    await session.flush()

                except ChatInvalidError as e:
                    # Чат не существует — деактивируем без жалобы
                    logger.warning(f"Chat {e.chat_id} invalid: {e}")
                    stmt = select(TelegramChat).where(TelegramChat.telegram_id == e.chat_id)
                    result = await session.execute(stmt)
                    chat_obj = result.scalar_one_or_none()
                    if chat_obj:
                        chat_obj.is_active = False
                        await session.commit()
                    stats["failed"] += 1

                    # Создаём запись о неудачной отправке
                    mailing_log = MailingLog(
                        campaign_id=campaign.id,
                        chat_id=chat.id,
                        chat_telegram_id=chat.telegram_id,
                        status=MailingStatus.FAILED,
                        error_msg=f"ChatInvalid: {e}",
                    )
                    session.add(mailing_log)
                    await session.flush()

                except Exception as e:
                    logger.error(f"Error sending to chat {chat.telegram_id}: {e}")
                    stats["failed"] += 1

                    # Создаём запись о неудачной отправке
                    mailing_log = MailingLog(
                        campaign_id=campaign.id,
                        chat_id=chat.id,
                        chat_telegram_id=chat.telegram_id,
                        status=MailingStatus.FAILED,
                        error_msg=str(e),
                    )
                    session.add(mailing_log)
                    await session.flush()

            # Обновляем статистику кампании
            await campaign_repo.update_statistics(
                campaign_id=campaign.id,
                sent_count=stats["sent"],
                failed_count=stats["failed"],
                total_chats=stats["total"],
            )

            # Завершаем кампанию
            await campaign_repo.update_status(campaign.id, CampaignStatus.DONE)

            # Спринт 5: Начисляем XP рекламодателю за завершение кампании
            from src.core.services.xp_service import xp_service

            # XP за завершение кампании (50 XP) + XP за каждую успешную отправку (1 XP за 10 отправок)
            campaign_xp = 50 + (stats["sent"] // 10)
            await xp_service.add_advertiser_xp(
                user_id=campaign.user_id,
                amount=campaign_xp,
                reason=f"campaign_completed:{campaign_id}",
            )

            # TASK 8.5: Триггер проверки достижений после завершения кампании
            from src.tasks.badge_tasks import trigger_after_campaign_complete
            trigger_after_campaign_complete.delay(campaign.user_id)

            logger.info(
                f"Campaign {campaign_id} completed: "
                f"sent={stats['sent']}, failed={stats['failed']}, total={stats['total']}, "
                f"xp_awarded={campaign_xp}"
            )

            return stats

    try:
        # asyncio.run() создаёт новый event loop и закрывает его после выполнения
        # Это правильный способ запуска async кода в синхронном контексте
        return asyncio.run(_send_async())

    except RuntimeError as e:
        # Обрабатываем ошибки закрытия event loop
        if "Event loop is closed" in str(e) or "handler is closed" in str(e):
            logger.warning(
                f"Event loop closed during campaign {campaign_id} (non-critical): {e}"
            )
            return {"error": "Event loop closed", "recovered": True}
        logger.error(f"Error in _execute_campaign: {e}")
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Error in _execute_campaign: {e}")
        return {"error": str(e)}


async def _handle_chat_complaint(
    chat_telegram_id: int,
    reason: str,
    session,
    complaint_thresholds: dict,
) -> None:
    """
    Зафиксировать жалобу на чат и при необходимости заблокировать его.

    Args:
        chat_telegram_id: Telegram ID чата.
        reason: Причина жалобы.
        session: AsyncSession для работы с БД.
        complaint_thresholds: Пороги для блокировки.
    """
    from datetime import datetime

    from sqlalchemy import select

    from src.db.models.analytics import TelegramChat

    stmt = select(TelegramChat).where(TelegramChat.telegram_id == chat_telegram_id)
    result = await session.execute(stmt)
    chat = result.scalar_one_or_none()

    if not chat:
        return

    chat.complaint_count += 1
    chat.last_complaint_at = datetime.now(UTC)
    chat.consecutive_failures += 1

    if chat.complaint_count >= complaint_thresholds["blacklist"]:
        chat.is_blacklisted = True
        chat.blacklisted_reason = f"Too many errors ({chat.complaint_count}): {reason}"
        chat.blacklisted_at = datetime.now(UTC)
        logger.warning(f"Chat {chat_telegram_id} blacklisted after {chat.complaint_count} errors")

    elif chat.complaint_count >= complaint_thresholds["pause_24h"]:
        chat.is_active = False
        logger.warning(f"Chat {chat_telegram_id} paused: {chat.complaint_count} complaints")

    await session.commit()


@celery_app.task(bind=True, base=BaseTask, name="mailing:check_scheduled_campaigns")
def check_scheduled_campaigns(self) -> dict[str, Any]:
    """
    Проверить и запустить запланированные кампании.

    Returns:
        Статистика.
    """
    logger.info("Checking scheduled campaigns")

    async def _check_async() -> dict[str, Any]:
        from datetime import datetime

        from src.db.models.campaign import CampaignStatus

        async with async_session_factory() as session:
            campaign_repo = CampaignRepository(session)

            # Получаем кампании, готовые к запуску
            now = datetime.now(UTC)
            campaigns = await campaign_repo.get_scheduled_due(now)

            stats = {
                "total_checked": len(campaigns),
                "launched": 0,
                "errors": 0,
            }

            for campaign in campaigns:
                try:
                    # Обновляем статус на running
                    await campaign_repo.update_status(campaign.id, CampaignStatus.RUNNING)

                    # Запускаем рассылку
                    send_campaign.delay(campaign.id)
                    stats["launched"] += 1

                    logger.info(f"Launched scheduled campaign {campaign.id}")

                except Exception as e:
                    logger.error(f"Error launching scheduled campaign {campaign.id}: {e}")
                    stats["errors"] += 1

                    # Обновляем статус на error
                    await campaign_repo.update_status(campaign.id, CampaignStatus.ERROR, str(e))

            return stats

    try:
        # asyncio.run() создаёт новый event loop и закрывает его после выполнения
        # Это корректный способ запуска async кода в синхронном Celery task
        result = asyncio.run(_check_async())
        logger.info(f"Scheduled campaigns check completed: {result}")
        return result

    except RuntimeError as e:
        # Обрабатываем ошибки закрытия event loop
        if "Event loop is closed" in str(e) or "handler is closed" in str(e):
            logger.warning(
                f"Event loop closed during scheduled campaigns check (non-critical): {e}"
            )
            return {"error": "Event loop closed", "recovered": True}
        logger.error(f"Error checking scheduled campaigns: {e}")
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Error checking scheduled campaigns: {e}")
        return {"error": str(e)}


# ─────────────────────────────────────────────
# Задача автоодобрения заявок (Спринт 1)
# ─────────────────────────────────────────────

@celery_app.task(name="mailing:auto_approve_pending_placements")
def auto_approve_pending_placements() -> dict:
    """
    Автоматически одобряет заявки которые не получили ответа от владельца за 24 часа.
    Запускается каждый час через Celery Beat.

    Логика:
    - Найти все размещения в статусе PENDING_APPROVAL
    - Если created_at + 24ч < now() → перевести в QUEUED
    """
    import asyncio
    from datetime import datetime, timedelta

    logger.info("Starting auto-approve pending placements")

    async def _auto_approve_async() -> dict:
        from src.db.models.mailing_log import MailingLog, MailingStatus

        deadline = datetime.now(UTC) - timedelta(hours=24)
        approved_count = 0
        failed_count = 0

        async with async_session_factory() as session:
            # Найдем все PENDING_APPROVAL размещения старше 24 часов
            from sqlalchemy import select

            stmt = (
                select(MailingLog)
                .where(
                    MailingLog.status == MailingStatus.PENDING_APPROVAL,
                    MailingLog.created_at < deadline,
                )
            )
            result = await session.execute(stmt)
            placements = result.scalars().all()

            for placement in placements:
                try:
                    placement.status = MailingStatus.QUEUED
                    approved_count += 1
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
        logger.error(f"auto_approve_pending_placements failed: {e}")
        return {"status": "error", "error": str(e)}


# ─────────────────────────────────────────────
# Публикация отдельного placement (для автоодобрения)
# ─────────────────────────────────────────────

@celery_app.task(name="mailing:publish_single_placement")
def publish_single_placement(placement_id: int) -> dict:
    """
    Опубликовать отдельное placement после одобрения.
    Вызывается из auto_approve_placements после перевода в QUEUED.

    Args:
        placement_id: ID размещения.

    Returns:
        Статистика публикации.
    """
    import asyncio

    async def _publish_async() -> dict:
        from aiogram import Bot
        from sqlalchemy import select

        from src.config.settings import settings
        from src.db.models.campaign import Campaign
        from src.db.models.mailing_log import MailingLog, MailingStatus

        async with async_session_factory() as session:
            # Получить placement
            stmt = select(MailingLog).where(MailingLog.id == placement_id)
            result = await session.execute(stmt)
            placement = result.scalar_one_or_none()

            if not placement:
                logger.error(f"publish_single_placement: placement {placement_id} not found")
                return {"error": "Placement not found"}

            if placement.status != MailingStatus.QUEUED:
                logger.warning(f"publish_single_placement: placement {placement_id} status is {placement.status}, expected QUEUED")
                return {"skipped": f"Status is {placement.status}"}

            # Получить кампанию
            stmt = select(Campaign).where(Campaign.id == placement.campaign_id)
            result = await session.execute(stmt)
            campaign = result.scalar_one_or_none()

            if not campaign:
                logger.error(f"publish_single_placement: campaign {placement.campaign_id} not found")
                return {"error": "Campaign not found"}

            # Отправить пост в канал
            bot = Bot(token=settings.bot_token)

            try:
                # Получить chat_id канала
                from src.db.models.analytics import TelegramChat

                stmt = select(TelegramChat).where(TelegramChat.id == placement.chat_id)
                result = await session.execute(stmt)
                chat = result.scalar_one_or_none()

                if not chat or not chat.telegram_id:
                    logger.error(f"publish_single_placement: channel {placement.chat_id} not found")
                    return {"error": "Channel not found"}

                # Отправить сообщение
                if campaign.image_file_id:
                    await bot.send_photo(
                        chat_id=chat.telegram_id,
                        photo=campaign.image_file_id,
                        caption=campaign.text,
                        parse_mode="HTML",
                    )
                else:
                    await bot.send_message(
                        chat_id=chat.telegram_id,
                        text=campaign.text,
                        parse_mode="HTML",
                    )

                # Обновить статус на SENT
                from datetime import datetime

                placement.status = MailingStatus.SENT
                placement.sent_at = datetime.now(UTC)
                placement.message_id = None  # Можно сохранить ID сообщения если нужно
                await session.flush()

                logger.info(f"publish_single_placement: published placement {placement_id} to channel {chat.telegram_id}")

                return {"success": True, "placement_id": placement_id}

            except Exception as e:
                logger.error(f"publish_single_placement: failed to publish placement {placement_id}: {e}")
                placement.status = MailingStatus.FAILED
                placement.error_msg = str(e)
                await session.flush()

                return {"error": str(e)}

            finally:
                await bot.session.close()

    try:
        return asyncio.run(_publish_async())
    except Exception as e:
        logger.error(f"publish_single_placement failed: {e}")
        return {"error": str(e)}
