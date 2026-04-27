"""
Celery задачи для SLA таймеров PlacementRequest флоу.

Задачи:
- check_owner_response_sla: Проверка истечения SLA ответа владельца (24ч)
- check_payment_sla: Проверка истечения SLA оплаты (24ч)
- check_counter_offer_sla: Проверка истечения SLA контр-предложения (24ч)
- check_escrow_sla: Проверка зависших размещений в эскроу
- publish_placement: Публикация поста в запланированное время
- schedule_placement_publication: Планирование публикации (хелпер)
"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from redis.asyncio import Redis
from sqlalchemy.orm import selectinload

from src.config.settings import settings
from src.core.services.placement_transition_service import PlacementTransitionService
from src.core.services.reputation_service import ReputationService
from src.db.models.placement_request import PlacementRequest, PlacementStatus
from src.db.models.user import User
from src.db.repositories.placement_request_repo import PlacementRequestRepository
from src.db.repositories.reputation_repo import ReputationRepo
from src.db.session import celery_async_session_factory as async_session_factory
from src.tasks.celery_app import QUEUE_WORKER_CRITICAL, BaseTask, celery_app

logger = logging.getLogger(__name__)

# Async Redis for task deduplication — D-10 fully resolved in S-40
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

# TTL для дедупликации задач (в секундах).
# Правило выбора: TTL ≤ max retry window задачи. Слишком большой TTL
# удерживает placement в «обрабатывается» при успешном падении retries.
DEDUP_TTL = {
    "check_owner_response_sla": 3600,
    "check_payment_sla": 3600,
    "check_counter_offer_sla": 3600,
    "publish_placement": 300,
    # A.6: короткий TTL для защиты от одновременного диспатча на двух
    # pool-воркерах (task_acks_late + retry). 180 с покрывает окно
    # max_retries=5 с exponential backoff до retry_backoff_max=600.
    "delete_published_post": 180,
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
    from src.db.repositories.user_repo import UserRepository
    from src.tasks._bot_factory import ephemeral_bot

    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_id(user_id)

        if not user or not user.telegram_id:
            return

        if not user.notifications_enabled:
            logger.debug(f"Notifications disabled for user_id={user_id}, skipping")
            return

        try:
            async with ephemeral_bot() as bot:
                await bot.send_message(
                    chat_id=user.telegram_id,
                    text=text,
                    parse_mode="HTML",
                )
            logger.info(f"Notification sent to user {user_id}")
        except Exception as e:
            logger.error(f"Failed to send notification to user {user_id}: {e}")


async def _check_dedup_async(task_name: str, placement_id: int) -> bool:
    """
    Проверить дедупликацию задачи (async, non-blocking).

    Returns:
        True если задача уже выполняется, False иначе.
    """
    task_key = f"placement_task:{task_name}:{placement_id}"
    ttl = DEDUP_TTL.get(task_name, 3600)

    if await redis_client.exists(task_key):
        return True

    await redis_client.setex(task_key, ttl, task_key)
    return False


# =============================================================================
# T1: CHECK OWNER RESPONSE SLA
# =============================================================================


@celery_app.task(
    bind=True, base=BaseTask, name="placement:check_owner_response_sla", queue=QUEUE_WORKER_CRITICAL
)
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
                if await _check_dedup_async("check_owner_response_sla", placement.id):
                    logger.info(f"Placement {placement.id} already being processed, skipping")
                    continue

                # pending_owner -> cancelled per Decision 1 canonical state machine
                # (pending_owner allow-list: counter_offer, pending_payment, cancelled).
                transition_service = PlacementTransitionService(session)
                await transition_service.transition(
                    placement=placement,
                    to_status=PlacementStatus.cancelled,
                    actor_user_id=None,
                    reason="owner_response_sla_timeout",
                    trigger="celery_beat",
                )

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


@celery_app.task(
    bind=True, base=BaseTask, name="placement:check_payment_sla", queue=QUEUE_WORKER_CRITICAL
)
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
                if await _check_dedup_async("check_payment_sla", placement.id):
                    logger.info(f"Placement {placement.id} already being processed, skipping")
                    continue

                # pending_payment -> cancelled (Decision 1 allow-list).
                transition_service = PlacementTransitionService(session)
                await transition_service.transition(
                    placement=placement,
                    to_status=PlacementStatus.cancelled,
                    actor_user_id=None,
                    reason="payment_sla_timeout",
                    trigger="celery_beat",
                )

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


@celery_app.task(
    bind=True, base=BaseTask, name="placement:check_counter_offer_sla", queue=QUEUE_WORKER_CRITICAL
)
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
                if await _check_dedup_async("check_counter_offer_sla", placement.id):
                    logger.info(f"Placement {placement.id} already being processed, skipping")
                    continue

                # counter_offer -> cancelled per Decision 1 canonical state machine
                # (counter_offer allow-list: pending_owner, pending_payment, cancelled).
                transition_service = PlacementTransitionService(session)
                await transition_service.transition(
                    placement=placement,
                    to_status=PlacementStatus.cancelled,
                    actor_user_id=None,
                    reason="counter_offer_sla_timeout",
                    trigger="celery_beat",
                )

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


@celery_app.task(
    bind=True, base=BaseTask, name="placement:publish_placement", queue=QUEUE_WORKER_CRITICAL
)
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
    from src.core.services.publication_service import PublicationService
    from src.tasks._bot_factory import ephemeral_bot

    result: dict[str, Any] = {"success": False, "status": "failed", "message": ""}

    async with ephemeral_bot() as bot, async_session_factory() as session:
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

        if await _check_dedup_async("publish_placement", placement_id):
            result["message"] = "Already being processed"
            return result

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

            # Возврат средств — публикация не состоялась, возвращаем 100%
            final_price = placement.final_price or placement.proposed_price
            try:
                from src.core.services.billing_service import BillingService

                billing_svc = BillingService()
                async with async_session_factory() as refund_session:
                    await billing_svc.refund_escrow(
                        refund_session,
                        placement_id=placement_id,
                        final_price=final_price,
                        advertiser_id=placement.advertiser_id,
                        owner_id=placement.owner_id,
                        scenario="after_escrow_before_confirmation",
                    )
                    await refund_session.commit()
            except Exception as refund_err:
                logger.critical(
                    f"CRITICAL: Failed to refund escrow for placement {placement_id} "
                    f"after publish failure: {refund_err}"
                )

            # Re-fetch placement after rollback so the transition runs on a
            # session-tracked instance.
            refreshed = await repo.get_by_id(placement_id)
            if refreshed is not None:
                transition_service = PlacementTransitionService(session)
                await transition_service.transition(
                    placement=refreshed,
                    to_status=PlacementStatus.failed,
                    actor_user_id=None,
                    reason="publication_failure",
                    trigger="celery_signal",
                )
            await session.commit()
            await _notify_user(
                placement.advertiser_id,
                f"❌ Ошибка публикации размещения #{placement_id}.\n"
                f"Средства {final_price:.0f} ₽ возвращены на баланс.",
            )
            result["message"] = str(e)

    return result


# =============================================================================
# T5b: CHECK PUBLISHED POSTS HEALTH (monitoring)
# =============================================================================


@celery_app.task(
    bind=True,
    base=BaseTask,
    name="placement:check_published_posts_health",
    queue=QUEUE_WORKER_CRITICAL,
)
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


async def _check_published_posts_health_async() -> dict[str, Any]:  # NOSONAR: python:S3776
    """Асинхронная реализация проверки здоровья опубликованных постов."""
    from sqlalchemy import select

    from src.db.models.placement_request import PlacementStatus
    from src.db.models.telegram_chat import TelegramChat
    from src.db.repositories.publication_log_repo import PublicationLogRepo
    from src.tasks._bot_factory import ephemeral_bot

    stats: dict[str, Any] = {
        "checked": 0,
        "monitoring_ok": 0,
        "deleted_early": 0,
        "bot_removed": 0,
        "errors": 0,
    }

    async with ephemeral_bot() as bot, async_session_factory() as session:
        from src.db.models.placement_request import PlacementRequest

        # A.6: previous filter `scheduled_delete_at > now` skipped the very
        # stuck placements we need to audit. Now we check both active (future)
        # and already-expired posts — the health monitor's job is to surface
        # inconsistencies regardless of timing.
        result = await session.execute(
            select(PlacementRequest).where(
                PlacementRequest.status.in_([
                    PlacementStatus.published,
                    PlacementStatus.completed,
                ]),
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
                except Exception as exc:
                    logger.warning(
                        "Placement audit: failed to forward message %d from channel %d: %s",
                        placement.message_id,
                        channel.telegram_id,
                        exc,
                    )
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
                logger.error(f"Error checking health for placement {placement.id}: {e}")
                stats["errors"] += 1

    return stats


# =============================================================================
# T5b: CHECK ESCROW SLA — stalled placements that should have been published
# =============================================================================


@celery_app.task(
    bind=True, base=BaseTask, name="placement:check_escrow_sla", queue=QUEUE_WORKER_CRITICAL
)
def check_escrow_sla(self) -> dict[str, Any]:
    """
    Find placements in escrow where scheduled time has passed but no message sent.
    If final_schedule (or scheduled_for) has passed and message_id is None → mark as
    failed + refund advertiser.

    Запускается Beat каждые 5 минут.

    Returns:
        Статистика обработанных заявок.
    """
    logger.info("Checking escrow SLA for stalled placements")

    try:
        stats = asyncio.run(_check_escrow_sla_async())
        logger.info(f"Escrow SLA check completed: {stats}")
        return stats

    except Exception as e:
        logger.error(f"Error checking escrow SLA: {e}")
        return {"error": str(e)}


async def _check_escrow_sla_async() -> dict[str, Any]:
    """Асинхронная реализация проверки escrow SLA."""
    from datetime import UTC, datetime

    from sqlalchemy import select

    from src.core.services.billing_service import BillingService

    stats: dict[str, Any] = {
        "total_checked": 0,
        "stalled": 0,
        "refunded": 0,
        "errors": 0,
    }

    async with async_session_factory() as session:
        now = datetime.now(UTC)
        # Find escrow placements where scheduled time has passed but no message sent
        stmt = (
            select(PlacementRequest)
            .where(
                PlacementRequest.status == PlacementStatus.escrow,
                PlacementRequest.message_id.is_(None),
                PlacementRequest.final_schedule.isnot(None),
                PlacementRequest.final_schedule <= now,
            )
            .options(selectinload(PlacementRequest.channel))
        )
        result = await session.execute(stmt)
        stalled_placements = list(result.scalars().all())

        stats["total_checked"] = len(stalled_placements)

        billing_svc = BillingService()

        for placement in stalled_placements:
            try:
                # Дедупликация
                if await _check_dedup_async("check_escrow_sla", placement.id):
                    logger.info(f"Placement {placement.id} already being processed, skipping")
                    continue

                final_price = placement.final_price or placement.proposed_price

                # Refund через BillingService — обновляет platform_account.escrow_reserved.
                # refund_escrow работает в рамках переданной сессии; commit обязан вызывающий.
                async with async_session_factory() as refund_session:
                    await billing_svc.refund_escrow(
                        refund_session,
                        placement_id=placement.id,
                        final_price=final_price,
                        advertiser_id=placement.advertiser_id,
                        owner_id=placement.owner_id,
                        scenario="after_escrow_before_confirmation",
                    )
                    await refund_session.commit()

                # Mark as failed (per-item commit)
                if placement.meta_json is None:
                    placement.meta_json = {}
                placement.meta_json["sla_error"] = (
                    "Publication SLA violated: scheduled time passed without publication"
                )
                transition_service = PlacementTransitionService(session)
                await transition_service.transition(
                    placement=placement,
                    to_status=PlacementStatus.failed,
                    actor_user_id=None,
                    reason="escrow_sla_violation",
                    trigger="celery_beat",
                )
                await session.commit()

                stats["stalled"] += 1
                stats["refunded"] += 1

                # Notify both parties
                await _notify_user(
                    placement.advertiser_id,
                    f"❌ Ошибка публикации размещения #{placement.id}.\n"
                    f"Средства {final_price:.0f} ₽ возвращены на баланс.",
                )

                channel = placement.channel
                if channel:
                    await _notify_user(
                        channel.owner_id,
                        f"⚠️ Размещение #{placement.id} не было опубликовано в срок и отменено.",
                    )

            except Exception as e:
                logger.error(f"Error processing stalled placement {placement.id}: {e}")
                await session.rollback()
                stats["errors"] += 1

    return stats


# =============================================================================
# T6: SCHEDULE PLACEMENT PUBLICATION
# =============================================================================


@celery_app.task(
    bind=True,
    base=BaseTask,
    name="placement:schedule_placement_publication",
    queue=QUEUE_WORKER_CRITICAL,
)
def schedule_placement_publication(
    self,
    placement_id: int,
    scheduled_iso: str | None = None,
) -> dict[str, Any]:
    """
    Хелпер: планирует публикацию на нужное время.

    Вызывается из PlacementRequestService / camp_pay_balance при переходе в escrow.

    Args:
        placement_id: ID заявки.
        scheduled_iso: ISO формат datetime (UTC). Если None — публикуем через 5 минут.

    Returns:
        Результат планирования.
    """
    logger.info(f"Scheduling placement {placement_id} for {scheduled_iso}")

    try:
        from datetime import UTC, datetime, timedelta

        if scheduled_iso:
            eta = datetime.fromisoformat(scheduled_iso.replace("Z", "+00:00"))
        else:
            # Default: publish in 5 minutes if no schedule provided
            eta = datetime.now(UTC) + timedelta(minutes=5)

        # Планируем задачу
        publish_placement.apply_async(
            args=[placement_id],
            eta=eta,
            task_id=f"publish:{placement_id}",
        )

        return {
            "success": True,
            "placement_id": placement_id,
            "scheduled_at": eta.isoformat(),
            "task_id": f"publish:{placement_id}",
        }

    except Exception as e:
        logger.error(f"Error scheduling placement {placement_id}: {e}")
        return {"error": str(e)}


# =============================================================================
# T7: DELETE PUBLISHED POST (consolidated from publication_tasks.py)
# =============================================================================


@celery_app.task(
    bind=True,
    base=BaseTask,
    name="placement:delete_published_post",
    queue=QUEUE_WORKER_CRITICAL,
    autoretry_for=(Exception,),
    max_retries=5,
    retry_backoff=True,
    retry_backoff_max=600,
)
def delete_published_post(self, placement_id: int) -> dict[str, Any]:
    """
    Удалить опубликованный пост и освободить эскроу.

    Args:
        placement_id: ID заявки.

    Returns:
        Результат удаления.

    Autoretry: 5 попыток с экспоненциальным backoff до 10 мин.
    Идемпотентность обеспечена BillingService.release_escrow + status guard
    в PublicationService.delete_published_post.

    Dedup: Redis-ключ с TTL 180 с защищает от гонки task_acks_late,
    когда один task_id попадает на два pool-воркера одновременно.
    """
    if asyncio.run(_check_dedup_async("delete_published_post", placement_id)):
        logger.info(
            f"Placement {placement_id} deletion already in-flight (dedup hit), skipping"
        )
        return {"success": True, "skipped": True, "reason": "dedup"}

    logger.info(f"Deleting placement post {placement_id}")
    result = asyncio.run(_delete_published_post_async(placement_id))
    logger.info(f"Placement {placement_id} deletion: {result}")
    return result


async def _delete_published_post_async(placement_id: int) -> dict[str, Any]:
    """Асинхронная реализация удаления опубликованного поста. Бросает исключение при ошибке.

    Bot создаётся локально через ephemeral_bot(): asyncio.run() создаёт
    свежий event loop на каждый вызов задачи, а aiohttp-сессия singleton-бота
    привязана к первому loop и после его закрытия падает с
    RuntimeError('Event loop is closed') при повторной инвокации.
    """
    from src.core.services.publication_service import PublicationService
    from src.tasks._bot_factory import ephemeral_bot

    async with ephemeral_bot() as bot, async_session_factory() as session:
        pub_service = PublicationService()
        await pub_service.delete_published_post(
            bot=bot, session=session, placement_id=placement_id
        )
        await session.commit()

    return {"success": True, "message": "Success"}


# =============================================================================
# T8: CHECK SCHEDULED DELETIONS (Beat task — replaces publication:check_scheduled_deletions)
# =============================================================================


@celery_app.task(
    bind=True,
    base=BaseTask,
    name="placement:check_scheduled_deletions",
    queue=QUEUE_WORKER_CRITICAL,
)
def check_scheduled_deletions(self) -> dict[str, Any]:
    """
    Периодическая задача — найти посты с истёкшим scheduled_delete_at.

    Запускается каждые 5 минут через Celery Beat.

    Returns:
        Статистика удалений.
    """
    logger.info("Checking scheduled deletions")

    try:
        stats = asyncio.run(_check_scheduled_deletions_async())
        logger.info(f"Scheduled deletions check completed: {stats}")
        return stats

    except Exception as e:
        logger.error(f"Error checking scheduled deletions: {e}")
        return {"error": str(e)}


async def _check_scheduled_deletions_async() -> dict[str, Any]:
    """Асинхронная реализация проверки запланированных удалений."""
    from datetime import UTC, datetime

    from sqlalchemy import select

    from src.db.models.placement_request import PlacementStatus

    stats: dict[str, Any] = {
        "total_found": 0,
        "scheduled": 0,
        "errors": 0,
    }

    async with async_session_factory() as session:
        now = datetime.now(UTC)
        result = await session.execute(
            select(PlacementRequest).where(
                PlacementRequest.status == PlacementStatus.published,
                PlacementRequest.scheduled_delete_at <= now,
                PlacementRequest.scheduled_delete_at.isnot(None),
            )
        )
        placements = list(result.scalars().all())

        stats["total_found"] = len(placements)

        for placement in placements:
            try:
                if await _check_dedup_async("check_scheduled_deletions", placement.id):
                    logger.info(f"Placement {placement.id} deletion already scheduled, skipping")
                    continue

                # A.6: dispatch immediately — no countdown buffer.
                # The old 60s buffer opened a race window where task_acks_late
                # could deliver the same task_id to a second pool worker; the
                # task-level dedup (DEDUP_TTL['delete_published_post']=180s)
                # now closes that window at the handler.
                delete_published_post.apply_async(args=[placement.id])
                stats["scheduled"] += 1

            except Exception as e:
                logger.error(f"Failed to schedule deletion for placement {placement.id}: {e}")
                stats["errors"] += 1

    return stats


# =============================================================================
# T8: ESCROW STUCK DETECTION (D-03 monitoring)
# =============================================================================


@celery_app.task(
    bind=True, base=BaseTask, name="placement:check_escrow_stuck", queue=QUEUE_WORKER_CRITICAL
)
def check_escrow_stuck(self) -> dict[str, Any]:
    """
    Detect placements in ESCROW status where scheduled_delete_at passed >48h ago.
    These are 'stuck' — the delete task may have failed silently.
    Alerts admin for manual intervention.
    """
    logger.info("Checking for stuck escrow placements")

    try:
        stats = asyncio.run(_check_escrow_stuck_async())
        logger.info(f"Escrow stuck check completed: {stats}")
        return stats

    except Exception as e:
        logger.error(f"Error checking escrow stuck: {e}")
        return {"error": str(e)}


async def _check_escrow_stuck_async() -> dict[str, Any]:
    """Async implementation of escrow stuck detection with recovery actions."""

    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from src.config.settings import settings
    from src.core.services.billing_service import BillingService
    from src.db.models.placement_request import PlacementRequest, PlacementStatus
    from src.tasks._bot_factory import ephemeral_bot

    stats: dict[str, Any] = {
        "total_checked": 0,
        "stuck": 0,
        "group_a_dispatched": 0,
        "group_b_refunded": 0,
        "group_c_dispatched": 0,
        "alerted": 0,
        "errors": 0,
    }

    threshold = datetime.now(UTC) - timedelta(hours=48)
    # A.6 group C: опубликованные placements, где scheduled_delete_at прошёл
    # больше часа назад. Это ловит случай, когда delete_published_post
    # упал по любой причине (Event loop is closed, IntegrityError и т.п.),
    # и check_scheduled_deletions перестал передиспатчить из-за Redis-дедупа.
    published_stuck_threshold = datetime.now(UTC) - timedelta(hours=1)
    billing_svc = BillingService()

    async with ephemeral_bot() as bot, async_session_factory() as session:
        # Group A/B: status=escrow >48h
        stmt = (
            select(PlacementRequest)
            .where(
                PlacementRequest.status == PlacementStatus.escrow,
                PlacementRequest.scheduled_delete_at.isnot(None),
                PlacementRequest.scheduled_delete_at < threshold,
            )
            .options(selectinload(PlacementRequest.channel))
        )
        result = await session.execute(stmt)
        stuck_placements = list(result.scalars().all())

        # Group C: status=published + expired >1h — deletion pipeline failed.
        stmt_c = (
            select(PlacementRequest)
            .where(
                PlacementRequest.status == PlacementStatus.published,
                PlacementRequest.scheduled_delete_at.isnot(None),
                PlacementRequest.scheduled_delete_at < published_stuck_threshold,
                PlacementRequest.message_id.isnot(None),
            )
            .options(selectinload(PlacementRequest.channel))
        )
        result_c = await session.execute(stmt_c)
        stuck_published = list(result_c.scalars().all())

        stats["total_checked"] = len(stuck_placements) + len(stuck_published)

        for placement in stuck_placements:
            try:
                stats["stuck"] += 1
                group = "A" if placement.message_id else "B"
                channel_name = placement.channel.username if placement.channel else "unknown"

                logger.critical(
                    f"STUCK ESCROW: placement #{placement.id}, group={group}, "
                    f"scheduled_delete_at={placement.scheduled_delete_at}, "
                    f"channel={channel_name}"
                )

                if placement.meta_json is None:
                    placement.meta_json = {}
                placement.meta_json["escrow_stuck_detected"] = datetime.now(UTC).isoformat()
                placement.meta_json["escrow_stuck_group"] = group

                if group == "A":
                    # Пост существует в Telegram — dispatch delete task (которая сделает release_escrow)
                    delete_published_post.apply_async(args=[placement.id])
                    stats["group_a_dispatched"] += 1
                else:
                    # Публикации не было — прямой возврат через BillingService.
                    # refund_escrow работает в рамках переданной сессии; commit обязан вызывающий.
                    final_price = placement.final_price or placement.proposed_price
                    async with async_session_factory() as refund_session:
                        await billing_svc.refund_escrow(
                            refund_session,
                            placement_id=placement.id,
                            final_price=final_price,
                            advertiser_id=placement.advertiser_id,
                            owner_id=placement.owner_id,
                            scenario="after_escrow_before_confirmation",
                        )
                        await refund_session.commit()
                    transition_service = PlacementTransitionService(session)
                    await transition_service.transition(
                        placement=placement,
                        to_status=PlacementStatus.failed,
                        actor_user_id=None,
                        reason="escrow_stuck_cleanup",
                        trigger="celery_beat",
                    )
                    stats["group_b_refunded"] += 1

                # Commit per-item
                await session.commit()

                # Admin alert
                alert_text = (
                    f"🚨 STUCK ESCROW action\n"
                    f"placement_id={placement.id}, group={group}\n"
                    f"channel={channel_name}\n"
                    f"action={'dispatch delete_published_post' if group == 'A' else 'refund executed'}"
                )
                for admin_id in settings.admin_ids:
                    try:
                        await bot.send_message(chat_id=admin_id, text=alert_text)
                        stats["alerted"] += 1
                    except Exception as alert_err:
                        logger.warning(f"Failed to alert admin {admin_id}: {alert_err}")

            except Exception as e:
                logger.error(f"Failed to process stuck escrow #{placement.id}: {e}")
                await session.rollback()
                stats["errors"] += 1

        # Group C: stuck published — deletion pipeline failed, re-dispatch.
        for placement in stuck_published:
            try:
                stats["stuck"] += 1
                channel_name = placement.channel.username if placement.channel else "unknown"

                logger.critical(
                    f"STUCK PUBLISHED: placement #{placement.id}, group=C, "
                    f"scheduled_delete_at={placement.scheduled_delete_at}, "
                    f"channel={channel_name}"
                )

                if placement.meta_json is None:
                    placement.meta_json = {}
                placement.meta_json["published_stuck_detected"] = datetime.now(UTC).isoformat()
                placement.meta_json["escrow_stuck_group"] = "C"
                await session.commit()

                delete_published_post.apply_async(args=[placement.id])
                stats["group_c_dispatched"] += 1

                alert_text = (
                    f"🚨 STUCK PUBLISHED action\n"
                    f"placement_id={placement.id}, group=C\n"
                    f"channel={channel_name}\n"
                    f"action=dispatch delete_published_post (deletion pipeline recovery)"
                )
                for admin_id in settings.admin_ids:
                    try:
                        await bot.send_message(chat_id=admin_id, text=alert_text)
                        stats["alerted"] += 1
                    except Exception as alert_err:
                        logger.warning(f"Failed to alert admin {admin_id}: {alert_err}")

            except Exception as e:
                logger.error(f"Failed to process stuck escrow #{placement.id}: {e}")
                await session.rollback()
                stats["errors"] += 1

    return stats
