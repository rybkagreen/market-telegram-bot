"""
Publication Service для публикации и удаления постов.
S-07: публикация размещений, управление закрепами, удаление по расписанию.
"""

import logging
from contextlib import suppress
from datetime import UTC, datetime, timedelta

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import ChatMemberAdministrator, ChatMemberOwner, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.config.settings import settings
from src.constants.payments import FORMAT_DURATIONS_SECONDS
from src.core.exceptions import (
    BotNotAdminError,
    InsufficientPermissionsError,
    PostDeletionError,
    PublicationBlockedError,
    TransitionBlockedError,
)
from src.core.services.billing_service import BillingService
from src.core.services.placement_transition_service import PlacementTransitionService
from src.db.models.placement_request import PlacementRequest, PlacementStatus
from src.db.repositories.placement_request_repo import PlacementRequestRepo
from src.db.repositories.publication_log_repo import PublicationLogRepo
from src.utils.telegram_limits import TELEGRAM_CAPTION_LIMIT, truncate_ad_text

logger = logging.getLogger(__name__)


class PublicationService:
    """
    Сервис для публикации и удаления постов.

    Методы:
        check_bot_permissions: Проверить права бота в канале
        publish_placement: Опубликовать размещение
        delete_published_post: Удалить опубликованный пост
    """

    def __init__(self) -> None:
        """Инициализация сервиса."""
        self.billing_service = BillingService()

    async def check_bot_permissions(
        self,
        bot: Bot,
        chat_id: int,
        require_pin: bool = False,
    ) -> None:
        """
        Проверить права бота в канале.

        Args:
            bot: Telegram бот.
            chat_id: ID чата (канала).
            require_pin: Требуется ли право закреплять сообщения.

        Raises:
            BotNotAdminError: Если бот не администратор.
            InsufficientPermissionsError: Если нет нужных прав.
        """
        try:
            member = await bot.get_chat_member(chat_id, bot.id)
        except Exception as e:
            logger.warning(f"Cannot get chat member for chat {chat_id}: {e}")
            raise

        if member.status not in ("administrator", "creator"):
            raise BotNotAdminError(f"Бот не является администратором канала {chat_id}")

        # Check permissions with type guards for union types
        can_post = False
        can_delete = False
        can_pin = False

        if isinstance(member, ChatMemberOwner):
            # Владелец канала всегда имеет все права
            can_post = True
            can_delete = True
            can_pin = True
        elif isinstance(member, ChatMemberAdministrator):
            can_post = bool(member.can_post_messages)
            can_delete = bool(member.can_delete_messages)
            # For channels: pin permission is bundled into can_edit_messages (Telegram Bot API docs).
            # can_pin_messages applies only to groups/supergroups.
            can_pin = (
                bool(member.can_edit_messages or member.can_pin_messages) if require_pin else True
            )
        else:
            raise InsufficientPermissionsError("Бот не является администратором канала")

        if not can_post:
            raise InsufficientPermissionsError("Нет права публиковать сообщения")

        if not can_delete:
            raise InsufficientPermissionsError("Нет права удалять сообщения")

        if require_pin and not can_pin:
            raise InsufficientPermissionsError("Нет права закреплять сообщения")

    @staticmethod
    def _build_marked_text(
        placement: PlacementRequest,
        is_test: bool = False,
        for_media_caption: bool = False,
    ) -> str:
        """Build post text with ORD erid marker and tracking link.

        Deterministic logic per Phase 6.B.3:
          * provider == "stub" + no erid: publish without a marker; append the
            "[ТЕСТОВАЯ ПУБЛИКАЦИЯ]" footer when the placement is flagged is_test.
          * provider != "stub" + no erid: raise PublicationBlockedError; ФЗ-38
            forbids publishing real advertising без ERID.
          * erid present: append the disclaimer + erid line.

        Tracking link (if tracking_short_code is set) is appended after the
        marker logic and is independent of erid state.

        Caption budget (BL-080 8d): when ``for_media_caption=True``, truncate
        ``ad_text`` if needed so the composed text fits within
        ``TELEGRAM_CAPTION_LIMIT`` (1024). Disclaimer and tracking URL are
        always preserved (ФЗ-38 / ORD legal requirement); ad_text is the only
        sacrificable component. Word-boundary truncate with trailing ellipsis.
        """
        base_text = placement.ad_text or ""
        test_placement = is_test or bool(getattr(placement, "is_test", False))

        if not placement.erid:
            if settings.ord_provider == "stub":
                disclaimer = "\n[ТЕСТОВАЯ ПУБЛИКАЦИЯ]" if test_placement else ""
            else:
                raise PublicationBlockedError(
                    f"ERID required: ord_provider={settings.ord_provider}, placement={placement.id}"
                )
        else:
            advertiser_name = getattr(placement, "advertiser_name", None) or "Рекламодатель"
            disclaimer = f"\n\nРеклама. {advertiser_name}\nerid: {placement.erid}"

        if placement.tracking_short_code:
            tracking_url = f"{settings.tracking_base_url}/{placement.tracking_short_code}"
            tracking = f"\n🔗 {tracking_url}"
        else:
            tracking = ""

        if for_media_caption:
            budget = TELEGRAM_CAPTION_LIMIT - len(disclaimer) - len(tracking)
            base_text = truncate_ad_text(base_text, budget)

        return f"{base_text}{disclaimer}{tracking}"

    async def _send_message_for_placement(
        self,
        bot: Bot,
        chat_id: int,
        placement: PlacementRequest,
        marked_text: str,
    ) -> Message:
        """Send the appropriate Telegram message based on media type."""
        if placement.media_type == "video" and placement.video_file_id:
            return await bot.send_video(
                chat_id=chat_id,
                video=placement.video_file_id,
                caption=marked_text,
                parse_mode="HTML",
                duration=placement.video_duration,
            )
        if placement.media_type == "photo" and placement.video_file_id:
            return await bot.send_photo(
                chat_id=chat_id,
                photo=placement.video_file_id,
                caption=marked_text,
                parse_mode="HTML",
            )
        return await bot.send_message(
            chat_id=chat_id,
            text=marked_text,
            parse_mode="HTML",
        )

    async def _report_ord_publication(
        self,
        session: AsyncSession,
        placement: PlacementRequest,
        channel_telegram_id: int,
        message_id: int,
    ) -> None:
        """Dispatch ORD publication report as a background Celery task (non-blocking)."""
        try:
            from src.tasks.ord_tasks import report_publication_task

            report_publication_task.delay(placement.id)
        except Exception:
            logger.exception(
                "Failed to enqueue ORD publication report for placement %s",
                placement.id,
            )
            import sentry_sdk

            sentry_sdk.capture_exception()

    async def publish_placement(
        self,
        session: AsyncSession,
        bot: Bot,
        placement_id: int,
    ) -> None:
        """
        Опубликовать размещение.

        Args:
            session: Асинхронная сессия.
            bot: Telegram бот.
            placement_id: ID заявки.

        Raises:
            PostDeletionError: Если публикация не удалась.
        """
        # 1. Получить placement + channel (eager load to avoid lazy load in async)
        result = await session.execute(
            select(PlacementRequest)
            .options(selectinload(PlacementRequest.channel))
            .where(PlacementRequest.id == placement_id)
        )
        placement = result.scalar_one_or_none()
        if not placement:
            raise ValueError(f"PlacementRequest {placement_id} not found")

        channel = placement.channel
        if not channel:
            raise ValueError(f"Channel not found for placement {placement_id}")

        if channel.telegram_id is None:
            raise ValueError(f"Channel {channel.id} has no telegram_id")

        require_pin = placement.publication_format in ("pin_24h", "pin_48h")

        # 2. Проверить права бота
        try:
            await self.check_bot_permissions(bot, channel.telegram_id, require_pin=require_pin)
        except (BotNotAdminError, InsufficientPermissionsError) as e:
            # T2-5 / O-10: permission failures get a distinct status from
            # technical failures — allows downstream filter for cases where
            # admin re-grants permission and the placement could conceptually
            # retry, vs failed (irrecoverable without rebuild).
            transition_service = PlacementTransitionService(session)
            await transition_service.transition(
                placement=placement,
                to_status=PlacementStatus.failed_permissions,
                actor_user_id=None,
                reason="publication_failure_permissions",
                trigger="celery_signal",
            )
            logger.error(f"Bot permissions check failed for placement {placement_id}: {e}")
            raise PostDeletionError(f"Bot permissions check failed: {e}") from e

        # 3. Формируем текст с маркировкой erid
        for_media_caption = placement.media_type in ("photo", "video")
        marked_text = self._build_marked_text(
            placement,
            is_test=placement.is_test,
            for_media_caption=for_media_caption,
        )
        pub_log_repo = PublicationLogRepo(session)

        # Log erid presence before sending
        erid_event = "erid_ok" if placement.erid else "erid_missing"
        await pub_log_repo.log_event(
            placement_id=placement_id,
            channel_id=channel.telegram_id,
            event_type=erid_event,
            erid=placement.erid,
        )

        # 4. Отправить сообщение
        try:
            sent_message = await self._send_message_for_placement(
                bot, channel.telegram_id, placement, marked_text
            )
            post_url = (
                f"https://t.me/c/"
                f"{str(channel.telegram_id).removeprefix('-100')}/{sent_message.message_id}"
            )
            await pub_log_repo.log_event(
                placement_id=placement_id,
                channel_id=channel.telegram_id,
                event_type="published",
                message_id=sent_message.message_id,
                post_url=post_url,
                erid=placement.erid,
            )
            await self._report_ord_publication(
                session, placement, channel.telegram_id, sent_message.message_id
            )
        except TelegramBadRequest as e:
            placement.failed_count += 1
            await pub_log_repo.log_event(
                placement_id=placement_id,
                channel_id=channel.telegram_id,
                event_type="publish_failed",
                extra={"error": str(e)},
            )
            transition_service = PlacementTransitionService(session)
            await transition_service.transition(
                placement=placement,
                to_status=PlacementStatus.failed,
                actor_user_id=None,
                reason="publication_telegram_error",
                trigger="celery_signal",
            )
            logger.error(f"Failed to send message for placement {placement_id}: {e}")
            raise PostDeletionError(f"Failed to send message: {e}") from e

        # 5. Закрепить если нужно
        if require_pin:
            with suppress(TelegramBadRequest):
                await bot.pin_chat_message(
                    chat_id=channel.telegram_id,
                    message_id=sent_message.message_id,
                    disable_notification=True,
                )

        # 6a. Сохранить message_id ОТДЕЛЬНЫМ коммитом немедленно после отправки.
        # Это — идемпотентный замок: если воркер упадёт до следующего коммита,
        # message_id уже будет в БД и задача при повторном запуске не отправит пост повторно.
        duration_seconds = FORMAT_DURATIONS_SECONDS.get(placement.publication_format, 86400)
        scheduled_delete_at = datetime.now(UTC) + timedelta(seconds=duration_seconds)

        placement_repo = PlacementRequestRepo(session)
        await placement_repo.set_message_id(
            session, placement_id, sent_message.message_id, scheduled_delete_at
        )
        await session.commit()  # S-48: external-boundary (Telegram message_id idempotency)

        # 6b. После коммита объекты в сессии просрочены — перечитываем placement
        placement = (
            await session.execute(
                select(PlacementRequest).where(PlacementRequest.id == placement_id)
            )
        ).scalar_one_or_none()

        if placement:
            placement.sent_count += 1
            # published_at + last_published_at handled by _sync_status_timestamps.
            transition_service = PlacementTransitionService(session)
            try:
                await transition_service.transition(
                    placement=placement,
                    to_status=PlacementStatus.published,
                    actor_user_id=None,
                    reason="publication_success",
                    trigger="celery_signal",
                )
            except TransitionBlockedError as exc:
                blockers = [b.get("gate") for b in exc.extra.get("blockers", [])]
                logger.error(
                    "publish_placement: escrow->published blocked for placement %s "
                    "after Telegram send (message_id=%s): %s",
                    placement_id,
                    sent_message.message_id,
                    blockers,
                )
                # Telegram message is already live, but compliance gates failed.
                # escrow->failed is gate-empty (allow-list entry with no gates),
                # so the organic path goes through cleanly without raising.
                await transition_service.transition(
                    placement=placement,
                    to_status=PlacementStatus.failed,
                    actor_user_id=None,
                    reason="gate_block_publication",
                    trigger="celery_signal",
                )

        logger.info(
            f"Placement {placement_id} published: message_id={sent_message.message_id}, "
            f"scheduled_delete_at={scheduled_delete_at}"
        )

    async def delete_published_post(
        self,
        bot: Bot,
        session: AsyncSession,
        placement_id: int,
    ) -> None:
        """
        Удалить опубликованный пост.

        Идемпотентен по статусу: повторный вызов на `completed` — мгновенный
        no-op. Вызов на любом другом не-published статусе — warning + return,
        без побочных эффектов. В штатном пути release_escrow внутри метода
        также идемпотентен на уровне БД (Transaction.idempotency_key).

        Args:
            bot: Telegram бот.
            session: Асинхронная сессия.
            placement_id: ID заявки.
        """
        result = await session.execute(
            select(PlacementRequest)
            .options(selectinload(PlacementRequest.channel))
            .where(PlacementRequest.id == placement_id)
        )
        placement = result.scalar_one_or_none()
        if not placement:
            logger.warning(f"PlacementRequest {placement_id} not found for deletion")
            return

        # Status guard — первый рубеж идемпотентности до любых побочных эффектов.
        if placement.status == PlacementStatus.completed:
            logger.info(f"Placement {placement_id} already completed, skipping deletion")
            return
        if placement.status != PlacementStatus.published:
            logger.warning(
                f"Placement {placement_id} in unexpected status "
                f"{placement.status.value}; deletion aborted"
            )
            return

        if not placement.message_id:
            logger.warning(f"Placement {placement_id} has no message_id")
            return

        channel = placement.channel
        if not channel:
            logger.warning(f"Channel not found for placement {placement_id}")
            return

        if channel.telegram_id is None:
            logger.error("Channel %s has no telegram_id, cannot delete post", channel.id)
            raise ValueError(f"Channel {channel.id} has no telegram_id")

        # Для pin форматов — сначала открепить
        if placement.publication_format in ("pin_24h", "pin_48h"):
            with suppress(TelegramBadRequest):
                await bot.unpin_chat_message(
                    chat_id=channel.telegram_id,
                    message_id=placement.message_id,
                )

        # Удалить сообщение
        with suppress(TelegramBadRequest):
            await bot.delete_message(channel.telegram_id, placement.message_id)

        try:
            pub_log_repo = PublicationLogRepo(session)
            await pub_log_repo.log_event(
                placement_id=placement_id,
                channel_id=channel.telegram_id,
                event_type="deleted_by_bot",
                message_id=placement.message_id,
            )
        except Exception:
            logger.exception("Failed to log deleted_by_bot for placement %s", placement_id)

        placement.deleted_at = datetime.now(UTC)

        # КЛЮЧЕВОЙ МОМЕНТ: освободить эскроу ТОЛЬКО после успешного удаления
        # ESCROW-001: release_escrow вызывается ТОЛЬКО здесь
        await self.billing_service.release_escrow(
            session,
            placement_id,
            placement.final_price or placement.proposed_price,
            placement.advertiser_id,
            channel.owner_id,
        )

        # Переводим в completed после удаления + освобождения эскроу
        transition_service = PlacementTransitionService(session)
        try:
            await transition_service.transition(
                placement=placement,
                to_status=PlacementStatus.completed,
                actor_user_id=None,
                reason="manual_publish_delete",
                trigger="celery_signal",
            )
        except TransitionBlockedError as exc:
            blockers = [b.get("gate") for b in exc.extra.get("blockers", [])]
            logger.error(
                "delete_published_post: published->completed blocked for placement %s; "
                "leaving in 'published' for next post-publication verification cycle: %s",
                placement_id,
                blockers,
            )
            # Post deleted, escrow released — placement stays in `published`.
            # G11/G12 will be re-evaluated on the next periodic sweep.
            return

        # Sprint A.2: автоматическая генерация акта выполненных работ
        try:
            from src.core.services.act_service import ActService

            act = await ActService.generate_for_completed_placement(session, placement)
            logger.info(f"Act generated for placement {placement_id}: {act.act_number}")
        except Exception as e:
            # Отказоустойчивость: ошибка генерации акта НЕ откатывает
            # удаление поста и освобождение эскроу
            logger.warning(f"Failed to generate act for placement {placement_id}: {e}")

        await session.flush()

        logger.info(f"Placement {placement_id} deleted successfully and escrow released")
