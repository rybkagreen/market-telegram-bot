"""ComparisonService — сравнение метрик Telegram-каналов."""

from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.services.mediakit_service import _session_ctx
from src.db.models.telegram_chat import TelegramChat


class ComparisonService:
    """Сервис для сравнения каналов по ключевым метрикам."""

    async def get_channels_for_comparison(
        self,
        channel_ids: list[int],
        session: AsyncSession | None = None,
    ) -> list[dict[str, Any]]:
        """Получить данные каналов для сравнения по списку id."""
        async with _session_ctx(session) as s:
            result = await s.execute(
                select(TelegramChat)
                .where(TelegramChat.id.in_(channel_ids))
                .options(selectinload(TelegramChat.channel_settings))
            )
            chats = result.scalars().all()

            channels: list[dict[str, Any]] = []
            for chat in chats:
                subscribers = chat.member_count or 0
                price_per_post: float = float(
                    chat.channel_settings.price_per_post
                    if chat.channel_settings
                    else Decimal(0)
                )
                price_per_1k = price_per_post / (subscribers / 1000) if subscribers > 0 else 0.0
                channels.append({
                    "id": chat.id,
                    "username": chat.username,
                    "title": chat.title,
                    "subscribers": subscribers,
                    "avg_views": chat.avg_views or 0,
                    "last_er": chat.last_er or 0.0,
                    "post_frequency": 0.0,
                    "price_per_post": price_per_post,
                    "price_per_1k_subscribers": price_per_1k,
                    "is_best": {},
                    "topic": chat.category,
                    "rating": chat.rating or 0.0,
                })
            return channels

    def calculate_comparison_metrics(self, channels: list[dict[str, Any]]) -> dict[str, Any]:
        """Рассчитать сравнительные метрики. Синхронный метод."""
        if not channels:
            return {"channels": [], "best_values": {}, "recommendation": {}}

        best_subscribers = max(ch["subscribers"] for ch in channels)
        best_avg_views = max(ch["avg_views"] for ch in channels)
        best_er = max(ch["last_er"] for ch in channels)

        best_channel = max(channels, key=lambda ch: ch["last_er"])

        return {
            "channels": channels,
            "best_values": {
                "subscribers": best_subscribers,
                "avg_views": best_avg_views,
                "last_er": best_er,
            },
            "recommendation": {"channel_id": best_channel["id"]},
        }


comparison_service = ComparisonService()
