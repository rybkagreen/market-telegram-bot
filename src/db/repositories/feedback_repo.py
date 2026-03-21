"""Feedback repository."""

from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select

from src.db.models.feedback import FeedbackStatus, UserFeedback
from src.db.repositories.base import BaseRepository


class FeedbackRepository(BaseRepository[UserFeedback]):
    """Repository for user feedback operations."""

    model = UserFeedback

    async def create_feedback(
        self,
        user_id: int,
        text: str,
    ) -> UserFeedback:
        """Create new feedback from user."""
        feedback = UserFeedback(
            user_id=user_id,
            text=text,
            status=FeedbackStatus.NEW,
        )
        self.session.add(feedback)
        await self.session.flush()
        return feedback

    async def get_by_user_id(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[UserFeedback]:
        """Get all feedback from user."""
        query = select(UserFeedback).where(
            UserFeedback.user_id == user_id
        ).order_by(
            UserFeedback.created_at.desc()
        ).limit(limit).offset(offset)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_status(
        self,
        status: FeedbackStatus,
        limit: int = 50,
    ) -> Sequence[UserFeedback]:
        """Get feedback by status (for admin)."""
        query = select(UserFeedback).where(
            UserFeedback.status == status
        ).order_by(
            UserFeedback.created_at.desc()
        ).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def respond_to_feedback(
        self,
        feedback_id: int,
        admin_user_id: int,
        response_text: str,
        status: FeedbackStatus = FeedbackStatus.RESOLVED,
    ) -> UserFeedback | None:
        """Add admin response to feedback."""
        feedback = await self.get_by_id(feedback_id)
        if not feedback:
            return None

        feedback.admin_response = response_text
        feedback.status = status
        feedback.responded_by_id = admin_user_id
        feedback.responded_at = datetime.now(UTC)

        await self.session.flush()
        return feedback

    async def count_by_user(self, user_id: int) -> int:
        """Посчитать количество отзывов пользователя."""
        result = await self.session.execute(select(func.count()).where(UserFeedback.user_id == user_id))
        return result.scalar_one() or 0

    async def count_by_status(self, status: FeedbackStatus | None = None) -> int:
        """Посчитать количество отзывов по статусу (для админской пагинации)."""
        if status is None:
            result = await self.session.execute(select(func.count()).select_from(UserFeedback))
        else:
            result = await self.session.execute(select(func.count()).where(UserFeedback.status == status))
        return result.scalar_one() or 0
