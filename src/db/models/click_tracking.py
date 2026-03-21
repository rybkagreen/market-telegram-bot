"""ClickTracking model for click tracking."""

from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class ClickTracking(Base):
    """Модель клика по ссылке отслеживания."""

    __tablename__ = "click_tracking"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    placement_request_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("placement_requests.id", ondelete="CASCADE"), index=True
    )
    short_code: Mapped[str] = mapped_column(String(16), index=True)
    clicked_at: Mapped[datetime] = mapped_column(default=func.now())
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)

    def __repr__(self) -> str:
        return f"<ClickTracking(id={self.id}, placement_request_id={self.placement_request_id}, short_code={self.short_code})>"
