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
from typing import Any

import redis as redis_sync

from src.config.settings import settings
from src.core.services.reputation_service import ReputationService
from src.db.models.placement_request import PlacementStatus
from src.db.models.user import User
from src.db.repositories.placement_request_repo import PlacementRequestRepository
from src.db.repositories.reputation_repo import ReputationRepo
from src.db.session import celery_async_session_factory as async_session_factory
from src.tasks.celery_app import BaseTask, celery_app

logger = logging.getLogger(__name__)

# Sync Redis для дедупликации задач
redis_sync_client = redis_sync.from_url(settings.celery_broker_url, decode_responses=True)

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

    if redis_sync_client.exists(task_key):
        return True

    redis_sync_client.setex(task_key, ttl, task_key)
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
        repo = PlacementRequestRepository(session)
        from datetime import UTC, datetime
        all_expired = await repo.get_expired(before=datetime.now(UTC))
        expired_placements = [p for p in all_expired if p.status == PlacementStatus.pending_owner]

        stats["total_checked"] = len(expired_placements)

        for placement in expired_placements:
            try:
                # Дедупликация
                if _check_dedup("check_owner_response_sla", placement.id):
                    logger.info(f"Placement {placement.id} already being processed, skipping")
                    continue

                # Обновляем статус
                await repo.update_status(placement.id, PlacementStatus.failed)

                # Возврат средств (100%, ещё не в эскроу)
                from src.core.services.billing_service import BillingService

                billing_service = BillingService()
                await billing_service.refund_failed_placement(
                    session=session,
                    placement_id=placement.id,
                )

                # Уведомления через новый сервис
                try:
                    from src.bot.handlers.shared.notifications import notify_sla_expired

                    advertiser = await session.get(User, placement.advertiser_id)
                    owner = await session.get(
                        User, placement.channel.owner_id if placement.channel else 0
                    )
                    channel_username = (
                        placement.channel.username
                        if placement.channel
                        else f"ID:{placement.channel_id}"
                    )
                    if advertiser and owner:
                        await notify_sla_expired(placement, advertiser, owner, channel_username)
                        stats["notified"] += 2
                except Exception as e:
                    logger.warning(
                        f"Failed to send SLA notification for placement {placement.id}: {e}"
                    )

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
        repo = PlacementRequestRepository(session)
        from datetime import UTC, datetime
        all_expired = await repo.get_expired(before=datetime.now(UTC))
        expired_placements = [p for p in all_expired if p.status == PlacementStatus.pending_payment]

        stats["total_checked"] = len(expired_placements)

        for placement in expired_placements:
            try:
                # Дедупликация
                if _check_dedup("check_payment_sla", placement.id):
                    logger.info(f"Placement {placement.id} already being processed, skipping")
                    continue

                # Обновляем статус
                await repo.update_status(placement.id, PlacementStatus.cancelled)

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
                    f"⏱ Время оплаты истекло.\nЗаявка #{placement.id} отменена.\nРепутация -20.",
                )

                await _notify_user(
                    placement.channel.owner_id,
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
        repo = PlacementRequestRepository(session)
        from datetime import UTC, datetime

        from sqlalchemy import select as _select

        from src.db.models.placement_request import PlacementRequest
        _expired_result = await session.execute(
            _select(PlacementRequest).where(
                PlacementRequest.status == PlacementStatus.counter_offer,
                PlacementRequest.expires_at < datetime.now(UTC),
            )
        )
        expired_placements = list(_expired_result.scalars().all())

        stats["total_checked"] = len(expired_placements)

        for placement in expired_placements:
            try:
                # Дедупликация
                if _check_dedup("check_counter_offer_sla", placement.id):
                    logger.info(f"Placement {placement.id} already being processed, skipping")
                    continue

                # Обновляем статус
                await repo.update_status(placement.id, PlacementStatus.failed)

                # Возврат средств
                from src.core.services.billing_service import BillingService

                billing_service = BillingService()
                await billing_service.refund_failed_placement(
                    session=session,
                    placement_id=placement.id,
                )

                # Уведомления
                await _notify_user(
                    placement.advertiser_id,
                    f"⏱ Переговоры истекли.\n"
                    f"Заявка #{placement.id} отменена.\n"
                    f"Средства возвращены.",
                )

                await _notify_user(
                    placement.channel.owner_id,
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
       - Эскроу освобождается в publication_service.delete_published_post() (ESCROW-001)
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
    """Асинхронная реализация публикации через PublicationService."""
    from aiogram import Bot

    from src.core.services.publication_service import PublicationService

    result: dict[str, Any] = {"success": False, "status": "failed", "message": ""}

    async with async_session_factory() as session:
        repo = PlacementRequestRepository(session)
        placement = await repo.get_by_id(placement_id)

        if not placement:
            result["message"] = "Placement not found"
            return result

        if placement.status != PlacementStatus.escrow:
            result["message"] = f"Invalid status: {placement.status}"
            return result

        # Проверка по БД — защита от повторной публикации после перезапуска воркера.
        # Redis-дедуп эфемерен; message_id в БД — единственный надёжный источник истины.
        if placement.message_id:
            logger.info(
                f"Placement {placement_id} already published "
                f"(message_id={placement.message_id}), skipping"
            )
            result["success"] = True
            result["status"] = "already_published"
            result["message"] = f"Already published, message_id={placement.message_id}"
            return result

        if _check_dedup("publish_placement", placement_id):
            result["message"] = "Already being processed"
            return result

        bot = Bot(token=settings.bot_token)
        pub_service = PublicationService()

        try:
            # publish_placement сохраняет message_id отдельным коммитом (идемпотентность),
            # затем flush для статуса — итоговый commit здесь
            await pub_service.publish_placement(session=session, bot=bot, placement_id=placement_id)
            await session.commit()

            # Репутация +1
            updated = await repo.get_by_id(placement_id)
            if updated:
                channel_id = updated.channel_id
                from src.db.models.telegram_chat import TelegramChat
                channel = await session.get(TelegramChat, channel_id)
                rep_service = ReputationService(session, ReputationRepo(session))
                await rep_service.on_publication(
                    advertiser_id=placement.advertiser_id,
                    owner_id=channel.owner_id if channel else placement.owner_id,
                    placement_request_id=placement_id,
                )
                await session.commit()

                await _notify_user(
                    placement.advertiser_id,
                    f"✅ Пост опубликован в @{channel.username if channel else '?'}!",
                )
                await _notify_user(
                    placement.owner_id,
                    "✅ Пост опубликован. Выплата будет начислена после удаления поста.",
                )

            result["success"] = True
            result["status"] = "published"
            result["message"] = "Success"

        except Exception as e:
            logger.error(f"Error publishing placement {placement_id}: {e}")
            await session.rollback()
            await repo.update_status(placement_id, PlacementStatus.failed)
            await session.commit()
            await _notify_user(
                placement.advertiser_id,
                f"❌ Ошибка публикации. Возврат {REFUND_AFTER_ESCROW_PCT}%.",
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
        repo = PlacementRequestRepository(session)
        placement = await repo.get_by_id(placement_id)

        if not placement:
            return {"error": "Placement not found"}

        # Проверка статуса
        if placement.status != PlacementStatus.failed:
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
        placement.status = PlacementStatus.escrow

        await session.flush()

    # Вызываем публикацию
    return await _publish_placement_async(placement_id)


# =============================================================================
# T5b: CHECK PUBLISHED POSTS HEALTH (monitoring)
# =============================================================================


@celery_app.task(bind=True, base=BaseTask, name="placement:check_published_posts_health")
def check_published_posts_health(self) -> dict[str, Any]:
    """
    Периодическая задача — проверить здоровье опубликованных постов.

    Для каждого активного размещения (status='published'):
    - Проверить что бот ещё является администратором канала
    - Логировать bot_removed если права утеряны
    - Логировать monitoring_ok если всё в порядке
    - Логировать deleted_early если сообщение удалено раньше срока

    Запускается Beat каждые 6 часов.

    Returns:
        Статистика проверок.
    """
    logger.info("Checking published posts health")

    try:
        stats = asyncio.run(_check_published_posts_health_async())
        logger.info(f"Published posts health check completed: {stats}")
        return stats
    except Exception as e:
        logger.error(f"Error checking published posts health: {e}")
        return {"error": str(e)}


async def _check_published_posts_health_async() -> dict[str, Any]:
    """Асинхронная реализация проверки здоровья опубликованных постов."""
    from datetime import UTC, datetime

    from aiogram import Bot
    from sqlalchemy import select

    from src.db.models.placement_request import PlacementStatus
    from src.db.models.telegram_chat import TelegramChat
    from src.db.repositories.publication_log_repo import PublicationLogRepo

    stats: dict[str, Any] = {
        "checked": 0,
        "monitoring_ok": 0,
        "deleted_early": 0,
        "bot_removed": 0,
        "errors": 0,
    }

    bot = Bot(token=settings.bot_token)
    try:
        async with async_session_factory() as session:
            from src.db.models.placement_request import PlacementRequest

            now = datetime.now(UTC)
            result = await session.execute(
                select(PlacementRequest).where(
                    PlacementRequest.status == PlacementStatus.published,
                    PlacementRequest.scheduled_delete_at > now,
                    PlacementRequest.message_id.isnot(None),
                )
            )
            placements = list(result.scalars().all())
            stats["checked"] = len(placements)

            for placement in placements:
                try:
                    pub_log_repo = PublicationLogRepo(session)
                    channel = await session.get(TelegramChat, placement.channel_id)
                    if not channel or not channel.telegram_id:
                        continue

                    # Check bot is still admin
                    try:
                        member = await bot.get_chat_member(channel.telegram_id, bot.id)
                        if member.status not in ("administrator", "creator"):
                            await pub_log_repo.log_event(
                                placement_id=placement.id,
                                channel_id=channel.telegram_id,
                                event_type="bot_removed",
                                message_id=placement.message_id,
                                extra={"member_status": member.status},
                            )
                            await session.commit()
                            stats["bot_removed"] += 1
                            continue
                    except Exception as e:
                        await pub_log_repo.log_event(
                            placement_id=placement.id,
                            channel_id=channel.telegram_id,
                            event_type="bot_removed",
                            message_id=placement.message_id,
                            extra={"error": str(e)},
                        )
                        await session.commit()
                        stats["bot_removed"] += 1
                        continue

                    # Check message still exists by trying to forward it
                    message_exists = True
                    if placement.message_id is None:
                        continue
                    try:
                        await bot.forward_message(
                            chat_id=bot.id,
                            from_chat_id=channel.telegram_id,
                            message_id=placement.message_id,
                        )
                    except Exception:
                        message_exists = False

                    if not message_exists:
                        await pub_log_repo.log_event(
                            placement_id=placement.id,
                            channel_id=channel.telegram_id,
                            event_type="deleted_early",
                            message_id=placement.message_id,
                            extra={
                                "scheduled_end": (
                                    placement.scheduled_delete_at.isoformat()
                                    if placement.scheduled_delete_at
                                    else None
                                )
                            },
                        )
                        stats["deleted_early"] += 1
                    else:
                        await pub_log_repo.log_event(
                            placement_id=placement.id,
                            channel_id=channel.telegram_id,
                            event_type="monitoring_ok",
                            message_id=placement.message_id,
                        )
                        stats["monitoring_ok"] += 1

                    await session.commit()

                except Exception as e:
                    logger.error(
                        f"Error checking health for placement {placement.id}: {e}"
                    )
                    stats["errors"] += 1

    finally:
        await bot.session.close()

    return stats


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
