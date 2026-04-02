"""Repository for Review model operations."""

from sqlalchemy import select

from src.db.models.review import Review
from src.db.repositories.base import BaseRepository


class ReviewRepo(BaseRepository[Review]):
    """Репозиторий для работы с отзывами о размещениях."""

    model = Review

    async def get_by_placement(self, placement_request_id: int) -> list[Review]:
        """Все отзывы по placement_request_id."""
        result = await self.session.execute(
            select(Review)
            .where(Review.placement_request_id == placement_request_id)
            .order_by(Review.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_by_placement_and_reviewer(
        self,
        placement_request_id: int,
        reviewer_id: int,
    ) -> Review | None:
        """Отзыв конкретного пользователя по placement — для проверки дубля."""
        result = await self.session.execute(
            select(Review).where(
                Review.placement_request_id == placement_request_id,
                Review.reviewer_id == reviewer_id,
            )
        )
        return result.scalar_one_or_none()

    async def create_review(
        self,
        placement_request_id: int,
        reviewer_id: int,
        reviewed_id: int,
        rating: int,
        comment: str | None,
    ) -> Review:
        """Создать отзыв напрямую (без проверок сервиса)."""
        review = Review(
            placement_request_id=placement_request_id,
            reviewer_id=reviewer_id,
            reviewed_id=reviewed_id,
            rating=rating,
            comment=comment,
        )
        self.session.add(review)
        await self.session.flush()
        await self.session.refresh(review)
        return review
