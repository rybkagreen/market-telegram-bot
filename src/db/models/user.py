"""User model for Telegram users."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, TimestampMixin


class UserPlan(str, Enum):
    """Тарифные планы пользователя."""

    FREE = "free"
    STARTER = "starter"
    PRO = "pro"
    BUSINESS = "business"
    ADMIN = "admin"


if TYPE_CHECKING:
    from src.db.models.badge import UserBadge
    from src.db.models.dispute import PlacementDispute
    from src.db.models.feedback import UserFeedback
    from src.db.models.payout import PayoutRequest
    from src.db.models.placement_request import PlacementRequest
    from src.db.models.reputation_history import ReputationHistory
    from src.db.models.reputation_score import ReputationScore
    from src.db.models.review import Review
    from src.db.models.telegram_chat import TelegramChat
    from src.db.models.transaction import Transaction


class User(Base, TimestampMixin):
    """Модель пользователя Telegram."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str] = mapped_column(String(256), nullable=False)
    last_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    current_role: Mapped[str] = mapped_column(String(16), default="new", server_default="new")
    plan: Mapped[str] = mapped_column(String(16), default="free", server_default="free")
    plan_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    terms_accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    balance_rub: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"), server_default="0")
    earned_rub: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"), server_default="0")
    credits: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    referral_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    referred_by_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    advertiser_xp: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    advertiser_level: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    owner_xp: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    owner_level: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    ai_uses_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    ai_uses_reset_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    # Relationships
    referred_by: Mapped[Optional["User"]] = relationship("User", remote_side=[id], backref="referrals")
    telegram_chats: Mapped[list["TelegramChat"]] = relationship("TelegramChat", back_populates="owner", cascade="all, delete-orphan")
    placement_requests_advertiser: Mapped[list["PlacementRequest"]] = relationship("PlacementRequest", foreign_keys="PlacementRequest.advertiser_id", back_populates="advertiser")
    placement_requests_owner: Mapped[list["PlacementRequest"]] = relationship("PlacementRequest", foreign_keys="PlacementRequest.owner_id", back_populates="owner")
    transactions: Mapped[list["Transaction"]] = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")
    payout_requests: Mapped[list["PayoutRequest"]] = relationship("PayoutRequest", foreign_keys="PayoutRequest.owner_id", back_populates="owner", cascade="all, delete-orphan")
    reputation_score: Mapped[Optional["ReputationScore"]] = relationship("ReputationScore", back_populates="user", uselist=False, cascade="all, delete-orphan")
    reputation_history: Mapped[list["ReputationHistory"]] = relationship("ReputationHistory", back_populates="user", cascade="all, delete-orphan")
    disputes_advertiser: Mapped[list["PlacementDispute"]] = relationship("PlacementDispute", foreign_keys="PlacementDispute.advertiser_id", back_populates="advertiser")
    disputes_owner: Mapped[list["PlacementDispute"]] = relationship("PlacementDispute", foreign_keys="PlacementDispute.owner_id", back_populates="owner")
    reviews_given: Mapped[list["Review"]] = relationship("Review", foreign_keys="Review.reviewer_id", back_populates="reviewer")
    reviews_received: Mapped[list["Review"]] = relationship("Review", foreign_keys="Review.reviewed_id", back_populates="reviewed")
    badges: Mapped[list["UserBadge"]] = relationship("UserBadge", back_populates="user", cascade="all, delete-orphan")
    feedback_list: Mapped[list["UserFeedback"]] = relationship(
        "UserFeedback",
        foreign_keys="UserFeedback.user_id",
        back_populates="user"
    )
    responded_feedback_list: Mapped[list["UserFeedback"]] = relationship(
        "UserFeedback",
        foreign_keys="UserFeedback.responded_by_id",
        back_populates="responder"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, username={self.username!r})>"
