"""UserBadge model for user achievements/badges."""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.db.models.user import User


class BadgeConditionType(str, Enum):
    """Типы условий для получения значка."""

    CAMPAIGNS_COUNT = "campaigns_count"
    PLACEMENTS_COUNT = "placements_count"
    STREAK_DAYS = "streak_days"
    SPEND_AMOUNT = "spend_amount"
    EARNED_AMOUNT = "earned_amount"
    REVIEW_COUNT = "review_count"
    MANUAL = "manual"


class BadgeCategory(str, Enum):
    """Категории значков."""

    ADVERTISER = "advertiser"
    OWNER = "owner"
    BOTH = "both"


class Badge(Base, TimestampMixin):
    """Модель значка/достижения."""

    __tablename__ = "badges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    icon_emoji: Mapped[str] = mapped_column(String(8), nullable=False)
    xp_reward: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    credits_reward: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    category: Mapped[str] = mapped_column(String(16), nullable=False)
    condition_type: Mapped[str] = mapped_column(String(32), nullable=False)
    condition_value: Mapped[float] = mapped_column(Float, default=0.0, server_default="0")
    is_rare: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    def __repr__(self) -> str:
        return f"<Badge(id={self.id}, code={self.code!r}, name={self.name!r})>"


class BadgeAchievement(Base, TimestampMixin):
    """Модель уровней/ступеней достижения."""

    __tablename__ = "badge_achievements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    badge_id: Mapped[int] = mapped_column(Integer, ForeignKey("badges.id"), nullable=False)
    achievement_type: Mapped[str] = mapped_column(String(64), nullable=False)
    threshold: Mapped[float] = mapped_column(Float, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    # Relationships
    badge: Mapped["Badge"] = relationship("Badge")

    def __repr__(self) -> str:
        return f"<BadgeAchievement(id={self.id}, badge_id={self.badge_id}, threshold={self.threshold})>"


class UserBadge(Base, TimestampMixin):
    """Модель достижений/значков пользователя."""

    __tablename__ = "user_badges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    badge_type: Mapped[str] = mapped_column(String(64), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    earned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    badge_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("badges.id"), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="badges")
    badge: Mapped[Optional["Badge"]] = relationship("Badge")

    def __repr__(self) -> str:
        return f"<UserBadge(id={self.id}, user_id={self.user_id}, badge_type={self.badge_type})>"
