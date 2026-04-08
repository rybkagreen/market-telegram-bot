"""MediakitService — управление медиакитами каналов."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.channel_mediakit import ChannelMediakit
from src.db.models.telegram_chat import TelegramChat


@asynccontextmanager
async def _session_ctx(session: AsyncSession | None) -> AsyncGenerator[AsyncSession]:
    """Provide a session: use existing one or create from factory (lazy import)."""
    if session is not None:
        yield session
        return
    from src.db.session import async_session_factory  # noqa: PLC0415

    async with async_session_factory() as s:
        yield s


class MediakitService:
    """Сервис для работы с медиакитами каналов."""

    async def get_or_create_mediakit(
        self,
        channel_id: int,
        session: AsyncSession | None = None,
    ) -> ChannelMediakit:
        """Найти или создать медиакит для канала."""
        async with _session_ctx(session) as s:
            result = await s.execute(
                select(ChannelMediakit).where(ChannelMediakit.channel_id == channel_id)
            )
            existing = result.scalar_one_or_none()
            if existing is not None:
                return existing

            chat_result = await s.execute(
                select(TelegramChat).where(TelegramChat.id == channel_id)
            )
            chat = chat_result.scalar_one_or_none()
            owner_user_id = chat.owner_id if chat is not None else None

            mediakit = ChannelMediakit(channel_id=channel_id, owner_user_id=owner_user_id)
            s.add(mediakit)
            await s.flush()
            await s.refresh(mediakit)
            return mediakit

    async def update_mediakit(
        self,
        mediakit_id: int,
        user_id: int,
        updates: dict[str, Any],
        session: AsyncSession | None = None,
    ) -> ChannelMediakit:
        """Обновить поля медиакита. Проверяет владельца."""
        async with _session_ctx(session) as s:
            result = await s.execute(
                select(ChannelMediakit).where(ChannelMediakit.id == mediakit_id)
            )
            mediakit = result.scalar_one_or_none()
            if mediakit is None:
                raise ValueError(f"Mediakit {mediakit_id} not found")
            if mediakit.owner_user_id is not None and mediakit.owner_user_id != user_id:
                raise PermissionError("Access denied: not the owner")

            for key, value in updates.items():
                setattr(mediakit, key, value)

            await s.flush()
            await s.refresh(mediakit)
            return mediakit

    async def get_mediakit_data(
        self,
        channel_id: int,
        session: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """Получить полные данные медиакита для канала."""
        async with _session_ctx(session) as s:
            chat_result = await s.execute(
                select(TelegramChat).where(TelegramChat.id == channel_id)
            )
            chat = chat_result.scalar_one_or_none()

            mediakit_result = await s.execute(
                select(ChannelMediakit).where(ChannelMediakit.channel_id == channel_id)
            )
            mediakit = mediakit_result.scalar_one_or_none()

            if mediakit is None:
                mediakit = await self.get_or_create_mediakit(channel_id, session=s)

            channel_data: dict[str, Any] = {}
            metrics: dict[str, Any] = {"subscribers": 0, "avg_views": 0, "er": 0.0, "post_frequency": 0.0}
            price: dict[str, Any] = {"amount": 0, "currency": "кр"}

            if chat is not None:
                channel_data = {
                    "id": chat.id,
                    "username": chat.username,
                    "title": chat.title,
                    "member_count": chat.member_count,
                }
                metrics = {
                    "subscribers": chat.member_count or 0,
                    "avg_views": chat.last_avg_views or 0,
                    "er": chat.last_er or 0.0,
                    "post_frequency": chat.last_post_frequency or 0.0,
                }
                if chat.price_per_post is not None:
                    price = {"amount": chat.price_per_post, "currency": "кр"}

            mediakit_data: dict[str, Any] = {}
            if mediakit is not None:
                mediakit_data = {
                    "id": mediakit.id,
                    "custom_description": mediakit.description,
                    "theme_color": mediakit.theme_color,
                    "is_public": mediakit.is_published,
                    "show_metrics": {"subscribers": True, "avg_views": True, "er": True},
                }

            return {
                "channel": channel_data,
                "mediakit": mediakit_data,
                "metrics": metrics,
                "price": price,
            }


mediakit_service = MediakitService()
