"""
Mediakit Service — сервис для работы с медиакитами каналов.
Спринт 9 — медиакиты для привлечения рекламодателей.
"""

import logging
from typing import TYPE_CHECKING, Any

from src.db.session import async_session_factory

if TYPE_CHECKING:
    from src.db.models.channel_mediakit import ChannelMediakit

logger = logging.getLogger(__name__)


class MediakitService:
    """Сервис для управления медиакитами каналов."""

    async def get_or_create_mediakit(self, channel_id: int) -> "ChannelMediakit":
        """
        Получить или создать медиакит для канала.

        Args:
            channel_id: ID канала.

        Returns:
            Объект ChannelMediakit.
        """
        from sqlalchemy import select

        from src.db.models.channel_mediakit import ChannelMediakit

        async with async_session_factory() as session:
            # Проверяем существует ли
            stmt = select(ChannelMediakit).where(
                ChannelMediakit.channel_id == channel_id
            )
            result = await session.execute(stmt)
            mediakit = result.scalar_one_or_none()

            if mediakit:
                return mediakit

            # Создаём новый
            from src.db.models.analytics import TelegramChat

            channel = await session.get(TelegramChat, channel_id)
            if not channel:
                raise ValueError(f"Channel {channel_id} not found")

            mediakit = ChannelMediakit(
                channel_id=channel_id,
                owner_user_id=channel.owner_user_id,
                custom_description=channel.description,
                theme_color="#1a73e8",
                is_public=True,
            )

            session.add(mediakit)
            await session.flush()

            logger.info(f"Created mediakit for channel {channel_id}")
            return mediakit

    async def update_mediakit(
        self,
        mediakit_id: int,
        owner_user_id: int,
        updates: dict[str, Any],
    ) -> "ChannelMediakit":
        """
        Обновить медиакит (только владелец).

        Args:
            mediakit_id: ID медиакита.
            owner_user_id: ID владельца для проверки прав.
            updates: Словарь с полями для обновления.

        Returns:
            Обновлённый объект ChannelMediakit.

        Raises:
            ValueError: Если пользователь не владелец.
        """
        from src.db.models.channel_mediakit import ChannelMediakit

        async with async_session_factory() as session:
            mediakit = await session.get(ChannelMediakit, mediakit_id)
            if not mediakit:
                raise ValueError(f"Mediakit {mediakit_id} not found")

            # Проверка прав
            if mediakit.owner_user_id != owner_user_id:
                raise ValueError("Only owner can update mediakit")

            # Разрешённые поля для обновления
            allowed_fields = {
                "custom_description",
                "logo_file_id",
                "banner_file_id",
                "show_metrics",
                "theme_color",
                "is_public",
            }

            # Обновляем только разрешённые поля
            for field, value in updates.items():
                if field in allowed_fields:
                    setattr(mediakit, field, value)

            await session.flush()
            await session.refresh(mediakit)

            logger.info(f"Updated mediakit {mediakit_id}")
            return mediakit

    async def get_mediakit_data(self, channel_id: int) -> dict[str, Any]:
        """
        Получить полные данные для медиакита.

        Args:
            channel_id: ID канала.

        Returns:
            dict с данными канала, медиакита, метрик, отзывов и цены.
        """
        from sqlalchemy import select

        from src.db.models.analytics import TelegramChat
        from src.db.models.review import Review, ReviewerRole

        async with async_session_factory() as session:
            # Получить канал
            channel = await session.get(TelegramChat, channel_id)
            if not channel:
                raise ValueError(f"Channel {channel_id} not found")

            # Получить или создать медиакит
            mediakit = await self.get_or_create_mediakit(channel_id)

            # Сформировать данные
            data = {
                "channel": {
                    "id": channel.id,
                    "username": channel.username,
                    "title": channel.title,
                    "description": channel.description,
                    "topic": channel.topic,
                    "member_count": channel.member_count,
                },
                "mediakit": {
                    "id": mediakit.id,
                    "custom_description": mediakit.custom_description,
                    "logo_file_id": mediakit.logo_file_id,
                    "theme_color": mediakit.theme_color,
                    "is_public": mediakit.is_public,
                    "show_metrics": mediakit.show_metrics or {},
                },
                "metrics": {
                    "subscribers": channel.member_count or 0,
                    "avg_views": channel.last_avg_views or 0,
                    "er": channel.last_er or 0.0,
                    "post_frequency": channel.last_post_frequency or 0.0,
                },
                "price": {
                    "amount": float(channel.price_per_post) if channel.price_per_post else 0,
                    "currency": "кр",
                },
                "reviews": {
                    "average_rating": 0.0,
                    "count": 0,
                },
            }

            # Получить отзывы (если есть)
            stmt = select(Review).where(
                Review.channel_id == channel_id,
                Review.reviewer_role == ReviewerRole.ADVERTISER,
                Review.is_hidden == False,  # noqa: E712
            )
            result = await session.execute(stmt)
            reviews = list(result.scalars().all())

            if reviews:
                avg_rating = sum(r.score_compliance for r in reviews if r.score_compliance) / len(reviews)
                data["reviews"] = {
                    "average_rating": round(avg_rating, 1),
                    "count": len(reviews),
                }

            return data

    async def track_view(self, mediakit_id: int) -> None:
        """
        Засчитать просмотр медиакита.

        Args:
            mediakit_id: ID медиакита.
        """
        from src.db.models.channel_mediakit import ChannelMediakit

        async with async_session_factory() as session:
            mediakit = await session.get(ChannelMediakit, mediakit_id)
            if mediakit:
                mediakit.views_count += 1
                await session.flush()
                logger.info(f"Tracked view for mediakit {mediakit_id}")

    async def track_download(self, mediakit_id: int) -> None:
        """
        Засчитать скачивание PDF медиакита.

        Args:
            mediakit_id: ID медиакита.
        """
        from src.db.models.channel_mediakit import ChannelMediakit

        async with async_session_factory() as session:
            mediakit = await session.get(ChannelMediakit, mediakit_id)
            if mediakit:
                mediakit.downloads_count += 1
                await session.flush()
                logger.info(f"Tracked download for mediakit {mediakit_id}")

    async def delete_mediakit(self, mediakit_id: int, owner_user_id: int) -> bool:
        """
        Удалить медиакит (только владелец).

        Args:
            mediakit_id: ID медиакита.
            owner_user_id: ID владельца для проверки прав.

        Returns:
            True если удалён.

        Raises:
            ValueError: Если пользователь не владелец.
        """
        from src.db.models.channel_mediakit import ChannelMediakit

        async with async_session_factory() as session:
            mediakit = await session.get(ChannelMediakit, mediakit_id)
            if not mediakit:
                return False

            # Проверка прав
            if mediakit.owner_user_id != owner_user_id:
                raise ValueError("Only owner can delete mediakit")

            await session.delete(mediakit)
            await session.flush()

            logger.info(f"Deleted mediakit {mediakit_id}")
            return True


# Глобальный экземпляр
mediakit_service = MediakitService()
