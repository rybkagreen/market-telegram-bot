"""ChannelMediakitRepo for ChannelMediakit model operations."""

from typing import Any

from sqlalchemy import select

from src.db.models.channel_mediakit import ChannelMediakit
from src.db.repositories.base import BaseRepository


class ChannelMediakitRepo(BaseRepository[ChannelMediakit]):
    """Репозиторий для работы с медиакитами каналов."""

    model = ChannelMediakit

    async def get_by_channel_id(self, channel_id: int) -> ChannelMediakit | None:
        """Получить медиакит канала по channel_id."""
        result = await self.session.execute(
            select(ChannelMediakit).where(ChannelMediakit.channel_id == channel_id)
        )
        return result.scalar_one_or_none()

    async def update_metrics(self, channel_id: int, **kwargs: Any) -> ChannelMediakit:
        """Обновить метрики медиакита. Создаёт запись если не существует."""
        mediakit = await self.get_by_channel_id(channel_id)
        if mediakit is None:
            mediakit = ChannelMediakit(channel_id=channel_id)
            self.session.add(mediakit)
            await self.session.flush()
            await self.session.refresh(mediakit)

        for key, value in kwargs.items():
            setattr(mediakit, key, value)

        await self.session.flush()
        await self.session.refresh(mediakit)
        return mediakit
