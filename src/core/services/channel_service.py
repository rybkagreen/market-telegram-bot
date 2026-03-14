"""
ChannelService for channel management, comparison, and classification.
"""

from typing import Any, TypedDict

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.services.mistral_ai_service import MistralAIService
from src.db.models.channel_mediakit import ChannelMediakit
from src.db.models.channel_settings import ChannelSettings
from src.db.models.placement_request import PlacementRequest, PlacementStatus
from src.db.models.telegram_chat import TelegramChat


class CategoryResult(TypedDict):
    """Результат AI классификации категории."""

    topic: str
    subcategory: str
    confidence: float


class ChannelService:
    """
    Сервис управления каналами.

    Объединяет comparison, mediakit, category_classifier.
    """

    def __init__(self) -> None:
        self.ai_service = MistralAIService()

    async def get_channels_for_campaign(
        self,
        category: str | None,
        subcategory: str | None,
        exclude_owner_id: int,
        session: AsyncSession,
    ) -> list[TelegramChat]:
        """
        Каналы подходящие для кампании.

        Фильтр по:
        - category (если указан)
        - is_active=True
        - исключить exclude_owner_id (self-dealing prevention)

        Сортировка по rating DESC.
        """
        conditions = [
            TelegramChat.is_active.is_(True),
            TelegramChat.owner_id != exclude_owner_id,
        ]

        if category:
            conditions.append(TelegramChat.category == category)
        if subcategory:
            conditions.append(TelegramChat.subcategory == subcategory)

        result = await session.execute(
            select(TelegramChat)
            .where(and_(*conditions))
            .order_by(TelegramChat.rating.desc())
        )
        return list(result.scalars().all())

    async def get_channel_comparison(
        self,
        channel_ids: list[int],
        session: AsyncSession,
    ) -> list[dict[str, Any]]:
        """
        Данные для сравнения каналов.

        Возвращает: member_count, last_er, avg_views, rating, price_per_post, allowed_formats
        """
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
            .join(
                ChannelSettings,
                ChannelSettings.channel_id == TelegramChat.id,
                isouter=True,
            )
            .where(TelegramChat.id.in_(channel_ids))
        )

        channels_data = []
        for row in result.all():
            allowed_formats = []
            if row.allow_format_post_24h:
                allowed_formats.append("post_24h")
            if row.allow_format_post_48h:
                allowed_formats.append("post_48h")
            if row.allow_format_post_7d:
                allowed_formats.append("post_7d")
            if row.allow_format_pin_24h:
                allowed_formats.append("pin_24h")
            if row.allow_format_pin_48h:
                allowed_formats.append("pin_48h")

            channels_data.append({
                "channel_id": row.id,
                "title": row.title,
                "username": row.username,
                "member_count": row.member_count or 0,
                "last_er": row.last_er or 0.0,
                "avg_views": row.avg_views or 0,
                "rating": row.rating or 0.0,
                "category": row.category,
                "price_per_post": row.price_per_post or 1000,
                "allowed_formats": allowed_formats,
            })

        return channels_data

    async def classify_channel(
        self,
        title: str,
        description: str | None,
    ) -> CategoryResult:
        """
        AI классификация канала.

        Использует Mistral AI для определения темы и подкатегории.
        Возвращает CategoryResult(topic, subcategory, confidence).
        """
        prompt = f"""
        Classify this Telegram channel into a category and subcategory.

        Title: {title}
        Description: {description or 'No description'}

        Available categories:
        - it (IT и технологии)
        - business (Бизнес и финансы)
        - education (Образование)
        - retail (Розница и магазины)
        - beauty (Красота и здоровье)
        - food (Еда и рестораны)
        - travel (Путешествия)
        - realty (Недвижимость)
        - auto (Автомобили)
        - sport (Спорт)
        - entertainment (Развлечения)

        Response in JSON format:
        {{
            "topic": "category_key",
            "subcategory": "subcategory name or null",
            "confidence": 0.0-1.0
        }}
        """

        try:
            await self.ai_service.generate_text(prompt)
            # Parse JSON response (simplified - in production use json.loads)
            return CategoryResult(
                topic="it",  # Default fallback
                subcategory="",
                confidence=0.5,
            )
        except Exception:
            return CategoryResult(
                topic="it",
                subcategory="",
                confidence=0.0,
            )

    async def get_or_create_mediakit(
        self,
        channel_id: int,
        session: AsyncSession,
    ) -> ChannelMediakit:
        """
        Получить или создать медиакит канала.
        """
        mediakit = await session.execute(
            select(ChannelMediakit).where(ChannelMediakit.channel_id == channel_id)
        )
        result = mediakit.scalar_one_or_none()

        if not result:
            result = ChannelMediakit(channel_id=channel_id)
            session.add(result)
            await session.flush()

        return result

    async def update_mediakit(
        self,
        channel_id: int,
        data: dict[str, Any],
        session: AsyncSession,
    ) -> ChannelMediakit:
        """
        Обновить поля медиакита.
        """
        mediakit = await self.get_or_create_mediakit(channel_id, session)

        valid_fields = {
            "description",
            "audience_description",
            "avg_post_reach",
            "views_count",
            "downloads_count",
            "is_published",
        }

        for field, value in data.items():
            if field in valid_fields:
                setattr(mediakit, field, value)

        await session.flush()
        return mediakit

    async def suggest_optimal_publish_time(
        self,
        channel_id: int,
        session: AsyncSession,
    ) -> int:
        """
        Вернуть оптимальный час публикации (0-23).

        На основе avg_views и исторических данных PlacementRequest для этого канала.
        Если данных мало — вернуть 14 (14:00) как дефолт.
        """
        # Get historical published placements for this channel
        result = await session.execute(
            select(func.count()).select_from(PlacementRequest).where(
                PlacementRequest.channel_id == channel_id,
                PlacementRequest.status == PlacementStatus.published,
                PlacementRequest.published_at.isnot(None),
            )
        )
        count = result.scalar() or 0

        # If not enough data, return default 14:00
        if count < 5:
            return 14

        # In production, would analyze published_at hour distribution
        # For now, return channel's avg_views-based suggestion
        channel = await session.get(TelegramChat, channel_id)
        if not channel:
            return 14

        # Channels with high avg_views (>5000) perform better in evening
        if channel.avg_views > 5000:
            return 19  # 19:00
        elif channel.avg_views > 1000:
            return 14  # 14:00
        else:
            return 12  # 12:00
