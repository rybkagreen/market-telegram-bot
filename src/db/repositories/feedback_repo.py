"""Feedback repository."""

from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.feedback import UserFeedback, FeedbackStatus
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
        feedback.responded_at = datetime.now(timezone.utc)

        await self.session.flush()
        return feedback
