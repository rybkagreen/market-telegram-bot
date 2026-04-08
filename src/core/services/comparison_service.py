"""ComparisonService — сравнение метрик Telegram-каналов."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
                select(TelegramChat).where(TelegramChat.id.in_(channel_ids))
            )
            chats = result.scalars().all()

            channels: list[dict[str, Any]] = []
            for chat in chats:
                member_count = chat.member_count or 0
                price_per_post = chat.price_per_post or 0
                price_per_1k = (
                    price_per_post / (member_count / 1000) if member_count > 0 else 0.0
                )
                channels.append(
                    {
                        "channel_id": chat.id,
                        "member_count": member_count,
                        "avg_views": chat.last_avg_views or 0,
                        "er": chat.last_er or 0.0,
                        "post_frequency": chat.last_post_frequency or 0.0,
                        "price_per_post": price_per_post,
                        "price_per_1k_subscribers": price_per_1k,
                    }
                )
            return channels

    def calculate_comparison_metrics(self, channels: list[dict[str, Any]]) -> dict[str, Any]:
        """Рассчитать сравнительные метрики. Синхронный метод."""
        if not channels:
            return {"channels": [], "best_values": {}, "recommendation": {}}

        best_member_count = max(ch["member_count"] for ch in channels)
        best_avg_views = max(ch["avg_views"] for ch in channels)
        best_er = max(ch["er"] for ch in channels)

        best_channel = max(channels, key=lambda ch: ch["er"])

        return {
            "channels": channels,
            "best_values": {
                "member_count": best_member_count,
                "avg_views": best_avg_views,
                "er": best_er,
            },
            "recommendation": {"channel_id": best_channel["channel_id"]},
        }


comparison_service = ComparisonService()
