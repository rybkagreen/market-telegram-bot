"""
ReviewService for managing placement reviews and channel ratings.
"""


from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.placement_request import PlacementRequest, PlacementStatus
from src.db.models.review import Review
from src.db.models.telegram_chat import TelegramChat


class ReviewService:
    """
    Сервис управления отзывами 1-5★.
    Интегрирует расчёт рейтинга канала.
    """

    async def create_review(
        self,
        placement_request_id: int,
        reviewer_id: int,
        reviewed_id: int,
        rating: int,
        comment: str | None,
        session: AsyncSession,
    ) -> Review:
        """
        Создать отзыв о размещении.

        Проверки:
        - placement_request должен быть завершён (status=published)
        - нет дубликата отзыва для этого placement_request
        - rating в диапазоне 1-5

        После создания обновляет рейтинг канала через recalculate_channel_rating.
        """
        # Validate rating
        if not 1 <= rating <= 5:
            raise ValueError("Rating must be between 1 and 5")

        # Check placement_request exists and is published
        placement = await session.get(PlacementRequest, placement_request_id)
        if not placement:
            raise ValueError("Placement request not found")
        if placement.status != PlacementStatus.published:
            raise ValueError("Can only review published placements")

        # Check for duplicate review
        existing = await session.execute(
            select(Review).where(Review.placement_request_id == placement_request_id)
        )
        if existing.scalar_one_or_none():
            raise ValueError("Review already exists for this placement")

        # Create review
        review = Review(
            placement_request_id=placement_request_id,
            reviewer_id=reviewer_id,
            reviewed_id=reviewed_id,
            rating=rating,
            comment=comment,
        )
        session.add(review)
        await session.flush()

        # Update channel rating
        await self.recalculate_channel_rating(placement.channel_id, session)

        return review

    async def recalculate_channel_rating(
        self,
        channel_id: int,
        session: AsyncSession,
    ) -> float:
        """
        Рассчитать рейтинг канала 0-5 по формуле:

        - reach_score (30%): на основе avg_post_reach
        - er_score (25%): на основе last_er (engagement rate)
        - growth_score (15%): на основе роста подписчиков
        - frequency_score (10%): на основе частоты публикаций
        - reliability_score (15%): на основе отзывов и завершённых размещений
        - age_score (5%): на основе возраста канала

        Сохраняет в TelegramChat.rating. Возвращает новый рейтинг.
        """
        channel = await session.get(TelegramChat, channel_id)
        if not channel:
            return 0.0

        # reach_score (30%) - normalize by 10K reach = 5.0
        reach_score = min(5.0, (channel.avg_views or 0) / 2000)

        # er_score (25%) - normalize by 10% ER = 5.0
        er_score = min(5.0, (channel.last_er or 0) * 50)

        # growth_score (15%) - placeholder, would need historical data
        growth_score = 3.0  # Default average

        # frequency_score (10%) - placeholder
        frequency_score = 3.0

        # reliability_score (15%) - based on reviews
        reviews_result = await session.execute(
            select(func.avg(Review.rating)).where(
                Review.reviewed_id == channel.owner_id
            )
        )
        avg_review_rating = reviews_result.scalar() or 3.0
        reliability_score = avg_review_rating

        # age_score (5%) - placeholder
        age_score = 3.0

        # Calculate weighted average
        new_rating = (
            reach_score * 0.30 +
            er_score * 0.25 +
            growth_score * 0.15 +
            frequency_score * 0.10 +
            reliability_score * 0.15 +
            age_score * 0.05
        )

        # Update channel rating
        channel.rating = new_rating
        await session.flush()

        return new_rating

    async def get_channel_reviews(
        self,
        channel_id: int,
        session: AsyncSession,
        limit: int = 20,
    ) -> list[Review]:
        """
        Получить последние отзывы канала.
        """

        result = await session.execute(
            select(Review)
            .join(PlacementRequest, Review.placement_request_id == PlacementRequest.id)
            .where(PlacementRequest.channel_id == channel_id)
            .order_by(Review.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_user_rating(
        self,
        user_id: int,
        role: str,
        session: AsyncSession,
    ) -> float:
        """
        Средний рейтинг пользователя как владельца канала.
        """
        result = await session.execute(
            select(func.avg(Review.rating)).where(Review.reviewed_id == user_id)
        )
        avg_rating = result.scalar()
        return float(avg_rating) if avg_rating else 0.0
