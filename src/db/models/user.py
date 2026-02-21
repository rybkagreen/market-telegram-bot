"""
Модель пользователя User.
Хранит информацию о пользователях бота, их балансе и тарифном плане.
"""

from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, Boolean, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.db.models.campaign import Campaign
    from src.db.models.transaction import Transaction


class UserPlan(str, Enum):
    """Тарифные планы пользователей."""

    FREE = "free"  # Бесплатный, ограниченные возможности
    STARTER = "starter"  # Стартовый, базовые возможности
    PRO = "pro"  # Профессиональный, расширенные возможности
    BUSINESS = "business"  # Бизнес, полный доступ


class User(Base, TimestampMixin):
    """
    Модель пользователя Telegram бота.

    Attributes:
        id: Уникальный идентификатор в БД (автоинкремент).
        telegram_id: Telegram ID пользователя (BigInt, уникальный).
        username: Username пользователя в Telegram.
        first_name: Имя пользователя.
        last_name: Фамилия пользователя.
        language_code: Язык пользователя (например, 'ru', 'en').
        balance: Баланс пользователя в рублях.
        plan: Тарифный план пользователя.
        referral_code: Уникальный реферальный код пользователя.
        referred_by_id: ID пользователя, который пригласил этого.
        is_banned: Забанен ли пользователь.
        is_active: Активен ли пользователь.
    """

    __tablename__ = "users"

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Telegram данные
    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        nullable=False,
        index=True,
        doc="Telegram ID пользователя",
    )

    username: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        doc="Username пользователя в Telegram",
    )

    first_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="Имя пользователя",
    )

    last_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="Фамилия пользователя",
    )

    language_code: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        default="ru",
        doc="Язык пользователя (ISO код)",
    )

    # Баланс и тариф
    balance: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00"),
        nullable=False,
        doc="Баланс пользователя в рублях",
    )

    plan: Mapped[UserPlan] = mapped_column(
        String(50),
        default=UserPlan.FREE,
        nullable=False,
        index=True,
        doc="Тарифный план пользователя",
    )

    # Реферальная программа
    referral_code: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        index=True,
        doc="Уникальный реферальный код пользователя",
    )

    referred_by_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        nullable=True,
        index=True,
        doc="ID пользователя, который пригласил этого",
    )

    # Статусы
    is_banned: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        doc="Забанен ли пользователь",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        doc="Активен ли пользователь",
    )

    # Отношения
    campaigns: Mapped[list["Campaign"]] = relationship(
        back_populates="user",
        lazy="selectin",
        cascade="all, delete-orphan",
        doc="Кампании пользователя",
    )

    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="user",
        lazy="selectin",
        cascade="all, delete-orphan",
        doc="Транзакции пользователя",
    )

    # Индексы
    __table_args__ = (
        UniqueConstraint("telegram_id", name="uq_users_telegram_id"),
        {
            "comment": "Пользователи Telegram бота",
        },
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, username={self.username!r})>"

    @property
    def full_name(self) -> str:
        """Возвращает полное имя пользователя."""
        parts = [self.first_name or "", self.last_name or ""]
        return " ".join(part for part in parts if part).strip() or self.username or "User"

    @property
    def mention(self) -> str:
        """Возвращает упоминание пользователя в Telegram."""
        if self.username:
            return f"@{self.username}"
        return self.full_name

    def can_send_campaigns(self) -> bool:
        """Проверяет, может ли пользователь запускать кампании."""
        return not self.is_banned and self.is_active and self.plan != UserPlan.FREE

    def get_campaign_limit(self) -> int:
        """Возвращает лимит кампаний в месяц для текущего тарифа."""
        limits = {
            UserPlan.FREE: 0,
            UserPlan.STARTER: 5,
            UserPlan.PRO: 20,
            UserPlan.BUSINESS: 100,
        }
        return limits.get(self.plan, 0)

    def get_chat_limit_per_campaign(self) -> int:
        """Возвращает лимит чатов на одну кампанию."""
        limits = {
            UserPlan.FREE: 0,
            UserPlan.STARTER: 50,
            UserPlan.PRO: 200,
            UserPlan.BUSINESS: 1000,
        }
        return limits.get(self.plan, 0)
