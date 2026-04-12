"""User feedback model."""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.db.models.user import User


class FeedbackStatus(str, Enum):
    """Feedback status enum."""

    NEW = "NEW"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    REJECTED = "REJECTED"


class UserFeedback(Base, TimestampMixin):
    """User feedback for support."""

    __tablename__ = "user_feedback"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default=FeedbackStatus.NEW, server_default="NEW", nullable=False, index=True
    )
    admin_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    responded_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    # Relationships
    user: Mapped[User] = relationship(foreign_keys=[user_id], back_populates="feedback_list")
    responder: Mapped[User | None] = relationship(
        foreign_keys=[responded_by_id], back_populates="responded_feedback_list"
    )

    def __repr__(self) -> str:
        return f"<UserFeedback(id={self.id}, user_id={self.user_id}, status={self.status})>"
