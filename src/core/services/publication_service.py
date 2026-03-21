"""
Publication Service для публикации и удаления постов.
S-07: публикация размещений, управление закрепами, удаление по расписанию.
"""

import logging
from contextlib import suppress
from datetime import UTC, datetime, timedelta

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import ChatMemberAdministrator, ChatMemberOwner
from sqlalchemy.ext.asyncio import AsyncSession

from src.constants.payments import FORMAT_DURATIONS_SECONDS
from src.core.exceptions import BotNotAdminError, InsufficientPermissionsError, PostDeletionError
from src.core.services.billing_service import BillingService
from src.db.models.placement_request import PlacementRequest, PlacementStatus
from src.db.repositories.placement_request_repo import PlacementRequestRepo

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
            can_pin = bool(member.can_pin_messages) if require_pin else True
        else:
            raise InsufficientPermissionsError(
                'Бот не является администратором канала'
            )

        if not can_post:
            raise InsufficientPermissionsError("Нет права публиковать сообщения")

        if not can_delete:
            raise InsufficientPermissionsError("Нет права удалять сообщения")

        if require_pin and not can_pin:
            raise InsufficientPermissionsError("Нет права закреплять сообщения")

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
        async with session.begin():
            # 1. Получить placement + channel + рекламный текст
            placement = await session.get(PlacementRequest, placement_id)
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
                placement.status = PlacementStatus.FAILED
                await session.flush()
                logger.error(f"Bot permissions check failed for placement {placement_id}: {e}")
                raise PostDeletionError(f"Bot permissions check failed: {e}") from e

            # 3. Отправить сообщение
            try:
                message = await bot.send_message(
                    chat_id=channel.telegram_id,
                    text=placement.final_text,
                    parse_mode="HTML",
                )
            except TelegramBadRequest as e:
                placement.status = PlacementStatus.FAILED
                # Увеличить failed_count
                from sqlalchemy import update
                await session.execute(
                    update(PlacementRequest)
                    .where(PlacementRequest.id == placement_id)
                    .values(failed_count=PlacementRequest.failed_count + 1)
                )
                await session.flush()
                logger.error(f"Failed to send message for placement {placement_id}: {e}")
                raise PostDeletionError(f"Failed to send message: {e}") from e

            # 4. Закрепить если нужно
            if require_pin:
                try:
                    await bot.pin_chat_message(
                        chat_id=channel.telegram_id,
                        message_id=message.message_id,
                        disable_notification=True,
                    )
                except TelegramBadRequest as e:
                    logger.warning(f"Failed to pin message for placement {placement_id}: {e}")
                    # Не падаем — пост опубликован, просто не закреплён

            # 5. Рассчитать scheduled_delete_at
            duration_seconds = FORMAT_DURATIONS_SECONDS.get(placement.publication_format, 86400)
            scheduled_delete_at = datetime.now(UTC) + timedelta(seconds=duration_seconds)

            # 6. Сохранить message_id и scheduled_delete_at
            placement_repo = PlacementRequestRepo(session)
            await placement_repo.set_message_id(
                session, placement_id, message.message_id, scheduled_delete_at
            )

            # 7. Обновить статус на PUBLISHED (эскроу освобождается ТОЛЬКО после удаления)
            placement.status = PlacementStatus.PUBLISHED
            placement.published_at = datetime.now(UTC)

            # Увеличить sent_count
            from sqlalchemy import update
            await session.execute(
                update(PlacementRequest)
                .where(PlacementRequest.id == placement_id)
                .values(
                    sent_count=PlacementRequest.sent_count + 1,
                    last_published_at=datetime.now(UTC)
                )
            )

            await session.flush()

            logger.info(
                f"Placement {placement_id} published: message_id={message.message_id}, "
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

        Args:
            bot: Telegram бот.
            session: Асинхронная сессия.
            placement_id: ID заявки.
        """
        async with session.begin():
            placement = await session.get(PlacementRequest, placement_id)
            if not placement:
                logger.warning(f"PlacementRequest {placement_id} not found for deletion")
                return

            if not placement.message_id:
                logger.warning(f"Placement {placement_id} has no message_id")
                return

            channel = placement.channel
            if not channel:
                logger.warning(f"Channel not found for placement {placement_id}")
                return

            if channel.telegram_id is None:
                logger.error('Channel %s has no telegram_id, cannot delete post', channel.id)
                raise ValueError(f'Channel {channel.id} has no telegram_id')

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

            # Зафиксировать удаление
            placement_repo = PlacementRequestRepo(session)
            await placement_repo.mark_deleted(session, placement_id)

            placement.status = PlacementStatus.PUBLISHED
            placement.deleted_at = datetime.now(UTC)

            # КЛЮЧЕВОЙ МОМЕНТ: освободить эскроу ТОЛЬКО после успешного удаления
            # ESCROW-001: release_escrow вызывается ТОЛЬКО здесь
            await self.billing_service.release_escrow(
                session,
                placement_id,
                placement.final_price or placement.proposed_price,
                placement.advertiser_id,
                channel.owner_user_id or 0,
            )

            await session.flush()

            logger.info(f"Placement {placement_id} deleted successfully and escrow released")
