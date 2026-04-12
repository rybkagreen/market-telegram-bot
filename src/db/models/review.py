"""Review model for placement reviews."""

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.db.models.placement_request import PlacementRequest
    from src.db.models.user import User


class Review(Base, TimestampMixin):
    """Модель отзыва о размещении."""

    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    placement_request_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("placement_requests.id"), nullable=False
    )
    reviewer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    reviewed_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    placement_request: Mapped[PlacementRequest] = relationship(
        "PlacementRequest", back_populates="reviews"
    )
    reviewer: Mapped[User] = relationship(
        "User", foreign_keys=[reviewer_id], back_populates="reviews_given"
    )
    reviewed: Mapped[User] = relationship(
        "User", foreign_keys=[reviewed_id], back_populates="reviews_received"
    )

    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 5", name="check_rating_range"),
        UniqueConstraint(
            "placement_request_id", "reviewer_id", name="uq_review_placement_reviewer"
        ),
    )

    def __repr__(self) -> str:
        return f"<Review(id={self.id}, placement_request_id={self.placement_request_id}, rating={self.rating})>"
