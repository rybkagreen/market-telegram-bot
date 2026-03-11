"""
Celery задачи для SLA таймеров PlacementRequest флоу.

Задачи:
- check_owner_response_sla: Проверка истечения SLA ответа владельца (24ч)
- check_payment_sla: Проверка истечения SLA оплаты (24ч)
- check_counter_offer_sla: Проверка истечения SLA контр-предложения (24ч)
- publish_placement: Публикация поста в запланированное время
- retry_failed_publication: Повторная попытка публикации через 1ч
- schedule_placement_publication: Планирование публикации (хелпер)
"""

import asyncio
import logging
from decimal import Decimal
from typing import Any

from redis.asyncio import Redis

from src.config.settings import settings
from src.core.services.reputation_service import ReputationService
from src.db.models.placement_request import PlacementStatus
from src.db.models.user import User
from src.db.repositories.placement_request_repo import PlacementRequestRepo
from src.db.repositories.reputation_repo import ReputationRepo
from src.db.session import async_session_factory
from src.tasks.celery_app import BaseTask, celery_app

logger = logging.getLogger(__name__)

# Redis клиент для дедупликации задач
redis_client = Redis.from_url(settings.celery_broker_url, decode_responses=True)

# =============================================================================
# SLA КОНСТАНТЫ
# =============================================================================

SLA_OWNER_RESPONSE_HOURS: int = 24
SLA_PAYMENT_HOURS: int = 24
SLA_COUNTER_OFFER_HOURS: int = 24
SLA_PUBLISH_RETRY_HOURS: int = 1
SCORE_AFTER_BAN: float = 2.0
REFUND_AFTER_ESCROW_PCT: int = 50
BEAT_CHECK_INTERVAL_MINUTES: int = 5

# TTL для дедупликации задач (в секундах)
DEDUP_TTL = {
    "check_owner_response_sla": 3600,
    "check_payment_sla": 3600,
    "check_counter_offer_sla": 3600,
    "publish_placement": 300,
    "retry_failed_publication": 600,
}


# =============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =============================================================================


async def _notify_user(user_id: int, text: str) -> None:
    """
    Отправить уведомление пользователю через Telegram Bot.

    Args:
        user_id: ID пользователя в БД.
        text: Текст сообщения.
    """
    from aiogram import Bot

    from src.db.repositories.user_repo import UserRepository

    bot = Bot(token=settings.bot_token)

    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_id(user_id)

        if user and user.telegram_id:
            try:
                await bot.send_message(
                    chat_id=user.telegram_id,
                    text=text,
                    parse_mode="HTML",
                )
                logger.info(f"Notification sent to user {user_id}")
            except Exception as e:
                logger.error(f"Failed to send notification to user {user_id}: {e}")
            finally:
                await bot.session.close()


def _check_dedup(task_name: str, placement_id: int) -> bool:
    """
    Проверить дедупликацию задачи.

    Args:
        task_name: Имя задачи.
        placement_id: ID заявки.

    Returns:
        True если задача уже выполняется, False иначе.
    """
    task_key = f"placement_task:{task_name}:{placement_id}"
    ttl = DEDUP_TTL.get(task_name, 3600)

    if redis_client.exists(task_key):
        return True

    redis_client.setex(task_key, ttl, task_key)
    return False


# =============================================================================
# T1: CHECK OWNER RESPONSE SLA
# =============================================================================


@celery_app.task(bind=True, base=BaseTask, name="placement:check_owner_response_sla")
def check_owner_response_sla(self) -> dict[str, Any]:
    """
    Проверить истечение SLA ответа владельца (24ч).

    Запускается Beat каждые 5 минут.
    Сканирует все pending_owner с expires_at < now.

    Логика:
    1. placement.status → 'failed'
    2. Возврат advertiser 100% средств
    3. ReputationService: owner не получает штраф
    4. notify_advertiser('⏱ Владелец не ответил. Средства возвращены')
    5. notify_owner('⚠️ Заявка #{id} просрочена')

    Returns:
        Статистика обработанных заявок.
    """
    logger.info("Checking owner response SLA")

    try:
        stats = asyncio.run(_check_owner_response_sla_async())
        logger.info(f"Owner response SLA check completed: {stats}")
        return stats

    except Exception as e:
        logger.error(f"Error checking owner response SLA: {e}")
        return {"error": str(e)}


async def _check_owner_response_sla_async() -> dict[str, Any]:
    """Асинхронная реализация проверки SLA ответа владельца."""
    stats = {
        "total_checked": 0,
        "expired": 0,
        "refunded": 0,
        "notified": 0,
        "errors": 0,
    }

    async with async_session_factory() as session:
        repo = PlacementRequestRepo(session)
        expired_placements = await repo.get_expired_pending_owner()

        stats["total_checked"] = len(expired_placements)

        for placement in expired_placements:
            try:
                # Дедупликация
                if _check_dedup("check_owner_response_sla", placement.id):
                    logger.info(f"Placement {placement.id} already being processed, skipping")
                    continue

                # Обновляем статус
                await repo.update_status(placement.id, PlacementStatus.FAILED)

                # Возврат средств (100%, ещё не в эскроу)
                from src.core.services.billing_service import BillingService

                billing_service = BillingService(session)
                await billing_service.refund(
                    user_id=placement.advertiser_id,
                    amount=placement.proposed_price,
                    reference_id=placement.id,
                )

                # Уведомления через новый сервис
                try:
                    from src.bot.handlers.shared.notifications import notify_sla_expired
                    advertiser = await session.get(User, placement.advertiser_id)
                    owner = await session.get(User, placement.channel.owner_user_id if placement.channel else 0)
                    channel_username = placement.channel.username if placement.channel else f"ID:{placement.channel_id}"
                    if advertiser and owner:
                        await notify_sla_expired(placement, advertiser, owner, channel_username)
                        stats["notified"] += 2
                except Exception as e:
                    logger.warning(f"Failed to send SLA notification for placement {placement.id}: {e}")

            except Exception as e:
                logger.error(f"Error processing placement {placement.id}: {e}")
                stats["errors"] += 1

    return stats


# =============================================================================
# T2: CHECK PAYMENT SLA
# =============================================================================


@celery_app.task(bind=True, base=BaseTask, name="placement:check_payment_sla")
def check_payment_sla(self) -> dict[str, Any]:
    """
    Проверить истечение SLA оплаты рекламодателем (24ч).

    Запускается Beat каждые 5 минут.
    Сканирует pending_payment с expires_at < now.

    Логика:
    1. placement.status → 'cancelled'
    2. ReputationService.on_cancel_after_confirmation → -20 к репутации
    3. notify_advertiser('⏱ Время оплаты истекло. Заявка отменена. Репутация -20')
    4. notify_owner('ℹ️ Рекламодатель не оплатил заявку #{id} вовремя')

    Returns:
        Статистика обработанных заявок.
    """
    logger.info("Checking payment SLA")

    try:
        stats = asyncio.run(_check_payment_sla_async())
        logger.info(f"Payment SLA check completed: {stats}")
        return stats

    except Exception as e:
        logger.error(f"Error checking payment SLA: {e}")
        return {"error": str(e)}


async def _check_payment_sla_async() -> dict[str, Any]:
    """Асинхронная реализация проверки SLA оплаты."""
    stats = {
        "total_checked": 0,
        "expired": 0,
        "penalized": 0,
        "notified": 0,
        "errors": 0,
    }

    async with async_session_factory() as session:
        repo = PlacementRequestRepo(session)
        expired_placements = await repo.get_expired_pending_payment()

        stats["total_checked"] = len(expired_placements)

        for placement in expired_placements:
            try:
                # Дедупликация
                if _check_dedup("check_payment_sla", placement.id):
                    logger.info(f"Placement {placement.id} already being processed, skipping")
                    continue

                # Обновляем статус
                await repo.update_status(placement.id, PlacementStatus.CANCELLED)

                # Штраф репутации
                rep_service = ReputationService(session, ReputationRepo(session))
                await rep_service.on_advertiser_cancel(
                    advertiser_id=placement.advertiser_id,
                    placement_request_id=placement.id,
                    after_confirmation=True,
                )

                # Уведомления
                await _notify_user(
                    placement.advertiser_id,
                    f"⏱ Время оплаты истекло.\n"
                    f"Заявка #{placement.id} отменена.\n"
                    f"Репутация -20.",
                )

                await _notify_user(
                    placement.channel.owner_user_id,
                    f"ℹ️ Рекламодатель не оплатил заявку #{placement.id} вовремя.",
                )

                stats["expired"] += 1
                stats["penalized"] += 1
                stats["notified"] += 2

            except Exception as e:
                logger.error(f"Error processing placement {placement.id}: {e}")
                stats["errors"] += 1

    return stats


# =============================================================================
# T3: CHECK COUNTER OFFER SLA
# =============================================================================


@celery_app.task(bind=True, base=BaseTask, name="placement:check_counter_offer_sla")
def check_counter_offer_sla(self) -> dict[str, Any]:
    """
    Проверить истечение SLA ответа на контр-предложение (24ч).

    Запускается Beat каждые 5 минут.
    Сканирует counter_offer с expires_at < now.

    Логика:
    1. placement.status → 'failed'
    2. Возврат advertiser 100% (не в эскроу)
    3. Репутация не меняется
    4. notify_advertiser('⏱ Переговоры истекли. Заявка отменена')
    5. notify_owner('⏱ Контр-предложение по заявке #{id} не было принято вовремя')

    Returns:
        Статистика обработанных заявок.
    """
    logger.info("Checking counter offer SLA")

    try:
        stats = asyncio.run(_check_counter_offer_sla_async())
        logger.info(f"Counter offer SLA check completed: {stats}")
        return stats

    except Exception as e:
        logger.error(f"Error checking counter offer SLA: {e}")
        return {"error": str(e)}


async def _check_counter_offer_sla_async() -> dict[str, Any]:
    """Асинхронная реализация проверки SLA контр-предложения."""
    stats = {
        "total_checked": 0,
        "expired": 0,
        "refunded": 0,
        "notified": 0,
        "errors": 0,
    }

    async with async_session_factory() as session:
        repo = PlacementRequestRepo(session)
        expired_placements = await repo.get_expired_counter_offer()

        stats["total_checked"] = len(expired_placements)

        for placement in expired_placements:
            try:
                # Дедупликация
                if _check_dedup("check_counter_offer_sla", placement.id):
                    logger.info(f"Placement {placement.id} already being processed, skipping")
                    continue

                # Обновляем статус
                await repo.update_status(placement.id, PlacementStatus.FAILED)

                # Возврат средств
                from src.core.services.billing_service import BillingService

                billing_service = BillingService(session)
                await billing_service.refund(
                    user_id=placement.advertiser_id,
                    amount=placement.final_price or placement.proposed_price,
                    reference_id=placement.id,
                )

                # Уведомления
                await _notify_user(
                    placement.advertiser_id,
                    f"⏱ Переговоры истекли.\n"
                    f"Заявка #{placement.id} отменена.\n"
                    f"Средства возвращены.",
                )

                await _notify_user(
                    placement.channel.owner_user_id,
                    f"⏱ Контр-предложение по заявке #{placement.id} не было принято вовремя.",
                )

                stats["expired"] += 1
                stats["refunded"] += 1
                stats["notified"] += 2

            except Exception as e:
                logger.error(f"Error processing placement {placement.id}: {e}")
                stats["errors"] += 1

    return stats


# =============================================================================
# T4: PUBLISH PLACEMENT
# =============================================================================


@celery_app.task(bind=True, base=BaseTask, name="placement:publish_placement")
def publish_placement(self, placement_id: int) -> dict[str, Any]:
    """
    Выполнить публикацию поста в канале в запланированное время.

    Args:
        placement_id: ID заявки.

    Логика:
    1. Проверить status == 'escrow' — иначе skip
    2. Отправить пост через bot.send_message / bot.send_photo
    3. Если успех:
       - status → 'published'
       - ReputationService.on_publication()
       - BillingService.release_escrow_for_placement() → owner 80%
       - notify_advertiser / notify_owner
    4. Если ошибка Telegram:
       - status → 'failed'
       - refund 50%
       - notify_advertiser / notify_owner

    Returns:
        Результат публикации.
    """
    logger.info(f"Publishing placement {placement_id}")

    try:
        result = asyncio.run(_publish_placement_async(placement_id))
        logger.info(f"Placement {placement_id} published: {result}")
        return result

    except Exception as e:
        logger.error(f"Error publishing placement {placement_id}: {e}")
        return {"error": str(e)}


async def _publish_placement_async(placement_id: int) -> dict[str, Any]:
    """Асинхронная реализация публикации."""
    from aiogram import Bot

    from src.db.models.analytics import TelegramChat

    result = {
        "success": False,
        "status": "failed",
        "message": "",
    }

    async with async_session_factory() as session:
        repo = PlacementRequestRepo(session)
        placement = await repo.get_by_id(placement_id)

        if not placement:
            result["message"] = "Placement not found"
            return result

        # Проверка статуса
        if placement.status != PlacementStatus.ESCROW:
            result["message"] = f"Invalid status: {placement.status}"
            return result

        # Дедупликация
        if _check_dedup("publish_placement", placement_id):
            result["message"] = "Already being processed"
            return result

        # Получаем канал
        channel = await session.get(TelegramChat, placement.channel_id)
        if not channel:
            result["message"] = "Channel not found"
            await repo.update_status(placement_id, PlacementStatus.FAILED)
            return result

        bot = Bot(token=settings.bot_token)

        try:
            # Отправляем пост
            if placement.media_file_id:
                await bot.send_photo(
                    chat_id=channel.telegram_id,
                    photo=placement.media_file_id,
                    caption=placement.final_text,
                    parse_mode="HTML",
                )
            else:
                await bot.send_message(
                    chat_id=channel.telegram_id,
                    text=placement.final_text,
                    parse_mode="HTML",
                )

            # Успех
            await repo.update_status(placement_id, PlacementStatus.PUBLISHED)

            # Репутация +1
            rep_service = ReputationService(session, ReputationRepo(session))
            await rep_service.on_publication(
                advertiser_id=placement.advertiser_id,
                owner_id=channel.owner_user_id,
                placement_request_id=placement_id,
            )

            # Выплата 80% владельцу
            from src.core.services.billing_service import BillingService

            billing_service = BillingService(session)
            owner_payout = (placement.final_price or placement.proposed_price) * Decimal("0.80")
            await billing_service.release_escrow_for_placement(
                placement_id=placement_id,
                owner_id=channel.owner_user_id,
                total_amount=placement.final_price or placement.proposed_price,
            )

            # Уведомления
            await _notify_user(
                placement.advertiser_id,
                f"✅ Пост опубликован в @{channel.username}!",
            )

            await _notify_user(
                channel.owner_user_id,
                f"✅ Пост опубликован. Начислено {owner_payout} кр.",
            )

            result["success"] = True
            result["status"] = "published"
            result["message"] = "Success"

        except Exception as e:
            logger.error(f"Telegram error publishing placement {placement_id}: {e}")

            # Ошибка публикации
            await repo.update_status(placement_id, PlacementStatus.FAILED)

            # Возврат 50%
            from src.core.services.billing_service import BillingService

            billing_service = BillingService(session)
            refund_amount = (placement.final_price or placement.proposed_price) * Decimal(
                str(REFUND_AFTER_ESCROW_PCT / 100)
            )
            await billing_service.refund(
                user_id=placement.advertiser_id,
                amount=refund_amount,
                reference_id=placement_id,
            )

            # Уведомления
            await _notify_user(
                placement.advertiser_id,
                f"❌ Ошибка публикации. Возврат {REFUND_AFTER_ESCROW_PCT}%.",
            )

            await _notify_user(
                channel.owner_user_id,
                f"❌ Не удалось опубликовать пост #{placement_id}.",
            )

            result["message"] = str(e)

        finally:
            await bot.session.close()

    return result


# =============================================================================
# T5: RETRY FAILED PUBLICATION
# =============================================================================


@celery_app.task(bind=True, base=BaseTask, name="placement:retry_failed_publication")
def retry_failed_publication(self, placement_id: int) -> dict[str, Any]:
    """
    Повторная попытка публикации через 1ч после неудачи.

    Args:
        placement_id: ID заявки.

    Логика:
    1. Проверить status == 'failed' и retry_count < 1
    2. Повторить логику publish_placement
    3. Если снова неудача → финальный 'failed', refund 50%

    Returns:
        Результат публикации.
    """
    logger.info(f"Retrying failed publication {placement_id}")

    try:
        result = asyncio.run(_retry_failed_publication_async(placement_id))
        logger.info(f"Retry placement {placement_id}: {result}")
        return result

    except Exception as e:
        logger.error(f"Error retrying placement {placement_id}: {e}")
        return {"error": str(e)}


async def _retry_failed_publication_async(placement_id: int) -> dict[str, Any]:
    """Асинхронная реализация повторной публикации."""
    async with async_session_factory() as session:
        repo = PlacementRequestRepo(session)
        placement = await repo.get_by_id(placement_id)

        if not placement:
            return {"error": "Placement not found"}

        # Проверка статуса
        if placement.status != PlacementStatus.FAILED:
            return {"skipped": "Status is not failed"}

        # Проверка retry_count
        retry_count = placement.meta_json.get("retry_count", 0) if placement.meta_json else 0
        if retry_count >= 1:
            return {"skipped": "Max retries reached"}

        # Обновляем retry_count
        if placement.meta_json is None:
            placement.meta_json = {}
        placement.meta_json["retry_count"] = retry_count + 1

        # Восстанавливаем статус для повторной попытки
        placement.status = PlacementStatus.ESCROW

        await session.flush()

    # Вызываем публикацию
    return await _publish_placement_async(placement_id)


# =============================================================================
# T6: SCHEDULE PLACEMENT PUBLICATION
# =============================================================================


@celery_app.task(bind=True, base=BaseTask, name="placement:schedule_placement_publication")
def schedule_placement_publication(
    self,
    placement_id: int,
    scheduled_at: str,
) -> dict[str, Any]:
    """
    Хелпер: планирует публикацию на нужное время.

    Вызывается из PlacementRequestService при переходе в escrow.

    Args:
        placement_id: ID заявки.
        scheduled_at: ISO формат datetime (UTC).

    Returns:
        Результат планирования.
    """
    logger.info(f"Scheduling placement {placement_id} for {scheduled_at}")

    try:
        from datetime import datetime

        eta = datetime.fromisoformat(scheduled_at.replace("Z", "+00:00"))

        # Планируем задачу
        publish_placement.apply_async(
            args=[placement_id],
            eta=eta,
            task_id=f"publish:{placement_id}",
        )

        return {
            "success": True,
            "placement_id": placement_id,
            "scheduled_at": scheduled_at,
            "task_id": f"publish:{placement_id}",
        }

    except Exception as e:
        logger.error(f"Error scheduling placement {placement_id}: {e}")
        return {"error": str(e)}
