"""
ReputationHistory model for reputation change tracking.
"""

from enum import Enum
from typing import Optional

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, TimestampMixin


class ReputationAction(str, Enum):
    """Действия влияющие на репутацию."""

    publication = "publication"
    review_5star = "review_5star"
    review_4star = "review_4star"
    review_3star = "review_3star"
    review_2star = "review_2star"
    review_1star = "review_1star"
    cancel_before_escrow = "cancel_before_escrow"
    cancel_after_confirm = "cancel_after_confirm"
    cancel_systematic = "cancel_systematic"
    reject_invalid_1 = "reject_invalid_1"
    reject_invalid_2 = "reject_invalid_2"
    reject_invalid_3 = "reject_invalid_3"
    reject_frequent = "reject_frequent"
    dispute_owner_fault = "dispute_owner_fault"
    recovery_30days = "recovery_30days"
    ban_reset = "ban_reset"


class ReputationHistory(Base, TimestampMixin):
    """
    Модель истории изменений репутации.
    """

    __tablename__ = "reputation_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    action: Mapped[ReputationAction] = mapped_column(nullable=False)
    delta: Mapped[float] = mapped_column(Float, nullable=False)
    score_before: Mapped[float] = mapped_column(Float, nullable=False)
    score_after: Mapped[float] = mapped_column(Float, nullable=False)
    placement_request_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("placement_requests.id"),
        nullable=True,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="reputation_history")
    placement_request: Mapped[Optional["PlacementRequest"]] = relationship("PlacementRequest", back_populates="reputation_history")

    def __repr__(self) -> str:
        return f"<ReputationHistory(id={self.id}, user_id={self.user_id}, action={self.action.value}, delta={self.delta})>"
