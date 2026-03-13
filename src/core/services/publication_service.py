"""
Publication Service для публикации и удаления постов.
S-07: публикация размещений, управление закрепами, удаление по расписанию.
"""

import logging
from datetime import UTC, datetime, timedelta

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
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
        member = await bot.get_chat_member(chat_id, bot.id)

        if member.status not in ("administrator", "creator"):
            raise BotNotAdminError(f"Бот не является администратором канала {chat_id}")

        if not member.can_post_messages:
            raise InsufficientPermissionsError("Нет права публиковать сообщения")

        if not member.can_delete_messages:
            raise InsufficientPermissionsError("Нет права удалять сообщения")

        if require_pin and not member.can_pin_messages:
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

            # 7. Разблокировать эскроу (вызывается billing_service.release_escrow)
            await self.billing_service.release_escrow(
                session,
                placement_id,
                placement.final_price or placement.proposed_price,
                placement.advertiser_id,
                channel.owner_user_id or 0,
            )

            placement.status = PlacementStatus.PUBLISHED
            placement.published_at = datetime.now(UTC)
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

            # Для pin форматов — сначала открепить
            if placement.publication_format in ("pin_24h", "pin_48h"):
                try:
                    await bot.unpin_chat_message(
                        chat_id=channel.telegram_id,
                        message_id=placement.message_id,
                    )
                except TelegramBadRequest:
                    pass  # уже откреплено — не падаем

            # Удалить сообщение
            try:
                await bot.delete_message(channel.telegram_id, placement.message_id)
            except TelegramBadRequest:
                pass  # уже удалено — не падаем

            # Зафиксировать удаление
            placement_repo = PlacementRequestRepo(session)
            await placement_repo.mark_deleted(session, placement_id)

            placement.status = PlacementStatus.COMPLETED
            placement.deleted_at = datetime.now(UTC)
            await session.flush()

            logger.info(f"Placement {placement_id} deleted successfully")
