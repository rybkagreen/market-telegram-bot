"""
Модель заявки на размещение PlacementRequest.
Спринт 6 — арбитражная система размещения рекламы.

Заявка проходит через арбитраж между рекламодателем и владельцем канала:
1. PENDING_OWNER — ожидает решения владельца (24ч)
2. COUNTER_OFFER — владелец сделал контр-предложение (макс 3 раунда)
3. PENDING_PAYMENT — владелец принял, ждём оплату (24ч)
4. ESCROW — средства заблокированы
5. PUBLISHED — успешно опубликовано
6. FAILED — ошибка публикации
7. REFUNDED — средства возвращены
8. CANCELLED — отменено
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.db.models.analytics import TelegramChat
    from src.db.models.campaign import Campaign
    from src.db.models.reputation_history import ReputationHistory
    from src.db.models.transaction import Transaction
    from src.db.models.user import User


class PlacementStatus(str, Enum):
    """Статусы заявки на размещение."""

    PENDING_OWNER = "pending_owner"  # Ожидает решения владельца (24ч)
    COUNTER_OFFER = "counter_offer"  # Владелец сделал контр-предложение
    PENDING_PAYMENT = "pending_payment"  # Владелец принял, ждём оплату (24ч)
    ESCROW = "escrow"  # Средства заблокированы
    PUBLISHED = "published"  # Успешно опубликовано
    FAILED = "failed"  # Ошибка публикации
    REFUNDED = "refunded"  # Средства возвращены
    CANCELLED = "cancelled"  # Отменено (рекламодателем или авто)


class PlacementRequest(Base, TimestampMixin):
    """
    Заявка на размещение рекламы через арбитраж.
    """

    # System constants (class-level, immutable)
    MIN_PRICE_PER_POST: int = 100  # Минимум 100 кредитов
    MAX_PACKAGE_DISCOUNT: int = 50  # Скидка пакета макс 50%
    MIN_SUBSCRIPTION_DAYS: int = 7  # Минимум 7 дней подписки
    MAX_SUBSCRIPTION_DAYS: int = 365  # Максимум 1 год
    MAX_POSTS_PER_DAY: int = 5  # Рекламных постов в день макс 5
    MAX_POSTS_PER_WEEK: int = 35  # В неделю макс 35
    MIN_HOURS_BETWEEN_POSTS: int = 4  # Между постами минимум 4 часа
    PLATFORM_COMMISSION: Decimal = Decimal("0.20")  # 20% комиссия платформы

    __tablename__ = "placement_requests"

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Foreign keys
    advertiser_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID рекламодателя",
    )

    campaign_id: Mapped[int] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID кампании",
    )

    channel_id: Mapped[int] = mapped_column(
        ForeignKey("telegram_chats.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID канала",
    )

    # Предложенные условия
    proposed_price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        doc="Цена предложенная рекламодателем",
    )

    final_price: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        doc="Итоговая согласованная цена",
    )

    proposed_schedule: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Желаемое время публикации",
    )

    final_schedule: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Согласованное время публикации",
    )

    proposed_frequency: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        doc="Частота (для пакетов)",
    )

    # Финальный текст
    final_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Финальный текст рекламы",
    )

    # Медиа
    media_file_id: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
        doc="ID медиафайла (фото/видео)",
    )

    # Статус
    status: Mapped[PlacementStatus] = mapped_column(
        String(50),
        default=PlacementStatus.PENDING_OWNER,
        nullable=False,
        index=True,
        doc="Статус заявки",
    )

    # Отклонения
    rejection_reason: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        doc="Причина отклонения (мин 10 символов)",
    )

    # Арбитраж
    counter_offer_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Счётчик раундов арбитража (макс 3)",
    )

    last_counter_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Время последнего контр-предложения",
    )

    # Эскроу
    escrow_transaction_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("transactions.id", ondelete="SET NULL"),
        nullable=True,
        doc="ID транзакции эскроу",
    )

    # Метаданные
    meta_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        doc="Дополнительные данные (retry_count, etc.)",
    )

    # Временные метки
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        doc="Дедлайн ответа владельца (+24ч от created_at)",
    )

    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Реальное время публикации",
    )

    # Отношения
    advertiser: Mapped["User"] = relationship(
        "User",
        foreign_keys=[advertiser_id],
        back_populates="placement_requests",
        lazy="selectin",
    )

    campaign: Mapped["Campaign"] = relationship(
        "Campaign",
        foreign_keys=[campaign_id],
        lazy="selectin",
    )

    channel: Mapped["TelegramChat"] = relationship(
        "TelegramChat",
        back_populates="placement_requests",
        lazy="selectin",
    )

    # История репутации (Спринт 6)
    reputation_history: Mapped[list["ReputationHistory"]] = relationship(
        "ReputationHistory",
        back_populates="placement_request",
        lazy="select",
    )

    escrow_transaction: Mapped[Optional["Transaction"]] = relationship(
        "Transaction",
        back_populates="placement_request",
        lazy="select",
    )

    # Индексы
    __table_args__ = (
        Index("ix_placement_requests_advertiser_id", "advertiser_id"),
        Index("ix_placement_requests_channel_id", "channel_id"),
        Index("ix_placement_requests_campaign_id", "campaign_id"),
        Index("ix_placement_requests_status", "status"),
        Index("ix_placement_requests_expires_at", "expires_at"),
        Index("ix_placement_requests_created_at", "created_at"),
        {
            "comment": "Заявки на размещение через арбитраж",
        },
    )

    def __repr__(self) -> str:
        return (
            f"<PlacementRequest(id={self.id}, advertiser_id={self.advertiser_id}, "
            f"channel_id={self.channel_id}, status={self.status.value})>"
        )

    @property
    def is_pending(self) -> bool:
        """Проверяет, ожидает ли заявка решения."""
        return self.status in (
            PlacementStatus.PENDING_OWNER,
            PlacementStatus.PENDING_PAYMENT,
        )

    @property
    def is_active(self) -> bool:
        """Проверяет, активна ли заявка (не завершена)."""
        return self.status not in (
            PlacementStatus.PUBLISHED,
            PlacementStatus.FAILED,
            PlacementStatus.REFUNDED,
            PlacementStatus.CANCELLED,
        )

    @property
    def can_counter(self) -> bool:
        """Проверяет, можно ли сделать контр-предложение (макс 3 раунда)."""
        return self.counter_offer_count < 3
