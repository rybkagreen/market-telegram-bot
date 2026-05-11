"""MediakitService — канал-mediakit business logic.

Pattern 1 strict (caller-owns session). All methods require
session: AsyncSession parameter. Service does NOT commit —
router/handler owns transaction lifecycle (S-48).
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.db.models.channel_mediakit import ChannelMediakit
from src.db.models.placement_request import PlacementRequest, PlacementStatus
from src.db.models.telegram_chat import TelegramChat
from src.db.repositories.channel_mediakit_repo import ChannelMediakitRepo

POST_FREQUENCY_WINDOW_DAYS = 30

_UPDATE_WHITELIST: frozenset[str] = frozenset({
    "description",
    "audience_description",
    "logo_file_id",
    "theme_color",
    "is_published",
    # SQLAlchemy synonyms on ChannelMediakit forward to canonical fields.
    "custom_description",
    "is_public",
})


class MediakitService:
    """Сервис для работы с медиакитами каналов (Pattern 1 strict)."""

    async def get_or_create_mediakit(
        self,
        channel_id: int,
        session: AsyncSession,
    ) -> ChannelMediakit:
        """Lookup or create ChannelMediakit для канала.

        Sets owner_user_id from TelegramChat.owner_id at creation time.
        flush() + refresh() only; caller owns commit (S-48).
        """
        repo = ChannelMediakitRepo(session)
        existing = await repo.get_by_channel_id(channel_id)
        if existing is not None:
            return existing

        chat_result = await session.execute(
            select(TelegramChat).where(TelegramChat.id == channel_id)
        )
        chat = chat_result.scalar_one_or_none()
        owner_user_id = chat.owner_id if chat is not None else None

        mediakit = ChannelMediakit(channel_id=channel_id, owner_user_id=owner_user_id)
        session.add(mediakit)
        await session.flush()
        await session.refresh(mediakit)
        return mediakit

    async def update_mediakit(
        self,
        mediakit_id: int,
        user_id: int,
        updates: dict[str, Any],
        session: AsyncSession,
    ) -> ChannelMediakit:
        """Update ChannelMediakit fields через whitelist.

        Whitelist: description, audience_description, logo_file_id,
        theme_color, is_published (5 fields). Counters + owner_user_id
        excluded. Raises PermissionError if user_id != mediakit.owner_user_id.
        flush() + refresh() only; caller owns commit.
        """
        result = await session.execute(
            select(ChannelMediakit).where(ChannelMediakit.id == mediakit_id)
        )
        mediakit = result.scalar_one_or_none()
        if mediakit is None:
            raise ValueError(f"Mediakit {mediakit_id} not found")
        if mediakit.owner_user_id is not None and mediakit.owner_user_id != user_id:
            raise PermissionError("Access denied: not the owner")

        for key, value in updates.items():
            if key in _UPDATE_WHITELIST:
                setattr(mediakit, key, value)

        await session.flush()
        await session.refresh(mediakit)
        return mediakit

    async def get_mediakit_data(
        self,
        channel_id: int,
        session: AsyncSession,
    ) -> dict[str, Any]:
        """Read-only dict для PDF rendering.

        Schema matches mediakit_pdf.generate_mediakit_pdf consumer.
        post_frequency derived from PlacementRequest published в last
        POST_FREQUENCY_WINDOW_DAYS days.
        show_metrics hardcoded all-True (Q4.3).
        Reviews block dropped (Q4.4).
        """
        chat_result = await session.execute(
            select(TelegramChat)
            .where(TelegramChat.id == channel_id)
            .options(selectinload(TelegramChat.channel_settings))
        )
        chat = chat_result.scalar_one_or_none()

        mediakit = await self.get_or_create_mediakit(channel_id, session=session)

        window_start = datetime.now(UTC) - timedelta(days=POST_FREQUENCY_WINDOW_DAYS)
        post_count_result = await session.execute(
            select(func.count(PlacementRequest.id)).where(
                PlacementRequest.channel_id == channel_id,
                PlacementRequest.status == PlacementStatus.published,
                PlacementRequest.published_at.is_not(None),
                PlacementRequest.published_at >= window_start,
            )
        )
        post_frequency = int(post_count_result.scalar_one() or 0)

        channel_data: dict[str, Any] = {}
        metrics: dict[str, Any] = {
            "subscribers": 0,
            "avg_views": 0,
            "er": 0.0,
            "post_frequency": post_frequency,
        }
        price: dict[str, Any] = {"amount": 0, "currency": "кр"}

        if chat is not None:
            channel_data = {
                "id": chat.id,
                "username": chat.username,
                "title": chat.title,
                "description": chat.description,
                "topic": chat.category,
                "member_count": chat.member_count,
            }
            metrics = {
                "subscribers": chat.member_count or 0,
                "avg_views": chat.avg_views or 0,
                "er": chat.last_er or 0.0,
                "post_frequency": post_frequency,
            }
            if chat.channel_settings is not None:
                price = {"amount": chat.channel_settings.price_per_post, "currency": "кр"}

        mediakit_data: dict[str, Any] = {
            "id": mediakit.id,
            "custom_description": mediakit.description,
            "theme_color": mediakit.theme_color,
            "is_public": mediakit.is_published,
            "logo_file_id": mediakit.logo_file_id,
        }

        show_metrics: dict[str, bool] = {
            "subscribers": True,
            "avg_views": True,
            "er": True,
            "post_frequency": True,
            "topics": True,
            "price": True,
        }

        return {
            "channel": channel_data,
            "mediakit": mediakit_data,
            "metrics": metrics,
            "price": price,
            "show_metrics": show_metrics,
        }

    async def register_pdf_hit(
        self,
        channel_id: int,
        session: AsyncSession,
    ) -> None:
        """Atomic counter increment for PDF hit (views_count + downloads_count).

        Bare UPDATE — single SQL round-trip, race-safe via DB-level arithmetic.
        No SELECT, no ORM materialization. UPDATE affects 0 rows if the
        ChannelMediakit row is absent (silent no-op) — caller responsibility
        to ensure the row exists (typically via get_mediakit_data, which calls
        get_or_create_mediakit internally).

        flush() called to surface UPDATE within the session view for callers
        that may re-read counters in the same transaction. Caller owns commit
        lifecycle (S-48).
        """
        stmt = (
            update(ChannelMediakit)
            .where(ChannelMediakit.channel_id == channel_id)
            .values(
                views_count=ChannelMediakit.views_count + 1,
                downloads_count=ChannelMediakit.downloads_count + 1,
            )
        )
        await session.execute(stmt)
        await session.flush()


mediakit_service = MediakitService()
