"""ReputationScore model for user reputation tracking."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base

if TYPE_CHECKING:
    from src.db.models.user import User


class ReputationScore(Base):
    """Модель репутационного счёта пользователя. one-to-one с User."""

    __tablename__ = "reputation_scores"

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), primary_key=True)
    advertiser_score: Mapped[float] = mapped_column(Float, default=5.0, server_default="5.0")
    owner_score: Mapped[float] = mapped_column(Float, default=5.0, server_default="5.0")
    is_advertiser_blocked: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    is_owner_blocked: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    advertiser_blocked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    owner_blocked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    advertiser_violations_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    owner_violations_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), server_default=func.now()
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="reputation_score")

    def __repr__(self) -> str:
        return f"<ReputationScore(user_id={self.user_id}, advertiser_score={self.advertiser_score}, owner_score={self.owner_score})>"
