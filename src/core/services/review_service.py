"""ReviewService for managing placement reviews and channel ratings."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.placement_request import PlacementRequest, PlacementStatus
from src.db.models.review import Review
from src.db.models.telegram_chat import TelegramChat


class ReviewService:
    """Сервис управления отзывами 1-5★. Интегрирует расчёт рейтинга канала."""

    async def create_review(
        self,
        placement_request_id: int,
        reviewer_id: int,
        reviewed_id: int,
        rating: int,
        comment: str | None,
        session: AsyncSession,
    ) -> Review:
        """Создать отзыв о размещении."""
        if not 1 <= rating <= 5:
            raise ValueError("Rating must be between 1 and 5")

        placement = await session.get(PlacementRequest, placement_request_id)
        if not placement:
            raise ValueError("Placement request not found")
        if placement.status != PlacementStatus.published:
            raise ValueError("Can only review published placements")

        existing = await session.execute(
            select(Review).where(
                Review.placement_request_id == placement_request_id,
                Review.reviewer_id == reviewer_id,
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("Review already exists for this placement from this reviewer")

        review = Review(
            placement_request_id=placement_request_id,
            reviewer_id=reviewer_id,
            reviewed_id=reviewed_id,
            rating=rating,
            comment=comment,
        )
        session.add(review)
        await session.flush()
        await session.refresh(review)
        await self.recalculate_channel_rating(placement.channel_id, session)
        return review

    async def recalculate_channel_rating(self, channel_id: int, session: AsyncSession) -> float:
        """Рассчитать рейтинг канала 0-5 по формуле."""
        channel = await session.get(TelegramChat, channel_id)
        if not channel:
            return 0.0

        reach_score = min(5.0, float(channel.avg_views or 0) / 2000)
        er_score = min(5.0, float(channel.last_er or 0) * 50)
        growth_score = 3.0
        frequency_score = 3.0

        reviews_result = await session.execute(
            select(func.avg(Review.rating)).where(Review.reviewed_id == channel.owner_id)
        )
        avg_review_rating = float(reviews_result.scalar() or 3.0)
        reliability_score = avg_review_rating
        age_score = 3.0

        new_rating = (
            reach_score * 0.30
            + er_score * 0.25
            + growth_score * 0.15
            + frequency_score * 0.10
            + reliability_score * 0.15
            + age_score * 0.05
        )
        channel.rating = new_rating
        await session.flush()
        return new_rating

    async def get_channel_reviews(
        self, channel_id: int, session: AsyncSession, limit: int = 20
    ) -> list[Review]:
        """Получить последние отзывы канала."""

        result = await session.execute(
            select(Review)
            .join(PlacementRequest, Review.placement_request_id == PlacementRequest.id)
            .where(PlacementRequest.channel_id == channel_id)
            .order_by(Review.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_user_rating(self, user_id: int, role: str, session: AsyncSession) -> float:
        """Средний рейтинг пользователя как владельца канала."""
        result = await session.execute(
            select(func.avg(Review.rating)).where(Review.reviewed_id == user_id)
        )
        avg_rating = result.scalar()
        return float(avg_rating) if avg_rating else 0.0
