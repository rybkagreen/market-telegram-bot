"""
Stub module for legacy channel_settings_repo.
ChannelSettings are now managed via ChannelSettings model directly.
This file exists for backward compatibility with legacy API files.
"""

from src.db.models.channel_settings import ChannelSettings
from src.db.repositories.base import BaseRepository


class ChannelSettingsRepo(BaseRepository[ChannelSettings]):
    """Channel settings repository."""

    model = ChannelSettings

    async def get_by_channel_id(self, channel_id: int) -> ChannelSettings | None:
        """Get settings by channel ID."""
        return await self.session.get(ChannelSettings, channel_id)

    async def get_or_create(self, channel_id: int) -> ChannelSettings:
        """Get or create settings for channel."""
        settings = await self.get_by_channel_id(channel_id)
        if not settings:
            settings = ChannelSettings(channel_id=channel_id)
            self.session.add(settings)
            await self.session.flush()
            await self.session.refresh(settings)
        return settings

    async def update_settings(self, channel_id: int, **kwargs) -> ChannelSettings:
        """Update channel settings."""
        settings = await self.get_or_create(channel_id)
        for key, value in kwargs.items():
            if hasattr(settings, key):
                setattr(settings, key, value)
        await self.session.flush()
        await self.session.refresh(settings)
        return settings

    async def get_by_channel(self, channel_id: int) -> ChannelSettings | None:
        """Alias for get_by_channel_id — used by placement_request_service."""
        return await self.get_by_channel_id(channel_id)
