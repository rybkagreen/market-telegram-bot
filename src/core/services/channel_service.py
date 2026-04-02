"""ChannelService for channel management, comparison, and classification."""

import logging
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.channel_mediakit import ChannelMediakit
from src.db.models.channel_settings import ChannelSettings
from src.db.models.placement_request import PlacementRequest, PlacementStatus
from src.db.models.telegram_chat import TelegramChat

logger = logging.getLogger(__name__)


class ChannelService:
    """Сервис управления каналами. Объединяет comparison и mediakit."""

    async def get_channels_for_campaign(
        self,
        category: str | None,
        exclude_owner_id: int,
        session: AsyncSession,
    ) -> list[TelegramChat]:
        """Каналы подходящие для кампании. Фильтр по category, is_active=True, исключить exclude_owner_id."""
        conditions = [TelegramChat.is_active.is_(True), TelegramChat.owner_id != exclude_owner_id]
        if category:
            conditions.append(TelegramChat.category == category)

        result = await session.execute(select(TelegramChat).where(and_(*conditions)).order_by(TelegramChat.rating.desc()))
        return list(result.scalars().all())

    @staticmethod
    def _build_allowed_formats(row: Any) -> list[str]:
        """Build list of allowed ad formats from a settings row."""
        format_flags = [
            (row.allow_format_post_24h, "post_24h"),
            (row.allow_format_post_48h, "post_48h"),
            (row.allow_format_post_7d, "post_7d"),
            (row.allow_format_pin_24h, "pin_24h"),
            (row.allow_format_pin_48h, "pin_48h"),
        ]
        return [fmt for flag, fmt in format_flags if flag]

    async def get_channel_comparison(self, channel_ids: list[int], session: AsyncSession) -> list[dict[str, Any]]:
        """Данные для сравнения каналов."""
        result = await session.execute(
            select(
                TelegramChat.id,
                TelegramChat.title,
                TelegramChat.username,
                TelegramChat.member_count,
                TelegramChat.last_er,
                TelegramChat.avg_views,
                TelegramChat.rating,
                TelegramChat.category,
                ChannelSettings.price_per_post,
                ChannelSettings.allow_format_post_24h,
                ChannelSettings.allow_format_post_48h,
                ChannelSettings.allow_format_post_7d,
                ChannelSettings.allow_format_pin_24h,
                ChannelSettings.allow_format_pin_48h,
            )
            .join(ChannelSettings, ChannelSettings.channel_id == TelegramChat.id, isouter=True)
            .where(TelegramChat.id.in_(channel_ids))
        )

        return [
            {
                "channel_id": row.id,
                "title": row.title,
                "username": row.username,
                "member_count": row.member_count or 0,
                "last_er": row.last_er or 0.0,
                "avg_views": row.avg_views or 0,
                "rating": row.rating or 0.0,
                "category": row.category,
                "price_per_post": row.price_per_post or 1000,
                "allowed_formats": self._build_allowed_formats(row),
            }
            for row in result.all()
        ]

    async def get_or_create_mediakit(self, channel_id: int, session: AsyncSession) -> ChannelMediakit:
        """Получить или создать медиакит канала."""
        mediakit = await session.execute(select(ChannelMediakit).where(ChannelMediakit.channel_id == channel_id))
        result = mediakit.scalar_one_or_none()
        if not result:
            result = ChannelMediakit(channel_id=channel_id)
            session.add(result)
            await session.flush()
            await session.refresh(result)
        return result

    async def update_mediakit(self, channel_id: int, data: dict[str, Any], session: AsyncSession) -> ChannelMediakit:
        """Обновить поля медиакита."""
        mediakit = await self.get_or_create_mediakit(channel_id, session)
        valid_fields = {"description", "audience_description", "avg_post_reach", "views_count", "downloads_count", "is_published"}
        for field, value in data.items():
            if field in valid_fields:
                setattr(mediakit, field, value)
        await session.flush()
        await session.refresh(mediakit)
        return mediakit

    async def suggest_optimal_publish_time(self, channel_id: int, session: AsyncSession) -> int:
        """Вернуть оптимальный час публикации (0-23)."""
        result = await session.execute(
            select(func.count()).select_from(PlacementRequest).where(
                PlacementRequest.channel_id == channel_id,
                PlacementRequest.status == PlacementStatus.published,
                PlacementRequest.published_at.isnot(None),
            )
        )
        count = result.scalar() or 0
        if count < 5:
            return 14
        channel = await session.get(TelegramChat, channel_id)
        if not channel:
            return 14
        if channel.avg_views > 5000:
            return 19
        elif channel.avg_views > 1000:
            return 14
        else:
            return 12
