"""
Модель транзакции Transaction.
Хранит историю финансовых операций пользователей.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.db.models.user import User


class TransactionType(str, Enum):
    """Типы транзакций."""

    TOPUP = "topup"  # Пополнение баланса
    SPEND = "spend"  # Списание за кампанию
    REFUND = "refund"  # Возврат средств
    BONUS = "bonus"  # Бонус (реферальная программа, промокод)
    ADJUSTMENT = "adjustment"  # Корректировка вручную (admin)


class Transaction(Base, TimestampMixin):
    """
    Модель финансовой транзакции.

    Attributes:
        id: Уникальный идентификатор транзакции.
        user_id: ID пользователя (FK на User).
        amount: Сумма транзакции в рублях (всегда положительная).
        type: Тип транзакции.
        payment_id: ID платежа в платежной системе (YooKassa).
        status: Статус платежа.
        description: Описание транзакции.
        meta_json: Дополнительные данные (JSONB).
        processed_at: Время обработки транзакции.
        balance_before: Баланс до транзакции.
        balance_after: Баланс после транзакции.
        campaign_id: ID связанной кампании (если spend).
        error_message: Сообщение об ошибке (если failed).
    """

    __tablename__ = "transactions"

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Foreign keys
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID пользователя",
    )

    # Сумма
    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        doc="Сумма транзакции в рублях (всегда положительная)",
    )

    # Тип
    type: Mapped[TransactionType] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        doc="Тип транзакции",
    )

    # Платежные данные
    payment_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        unique=True,
        index=True,
        doc="ID платежа в платежной системе",
    )

    payment_status: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        doc="Статус платежа в платежной системе",
    )

    payment_method: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        doc="Метод платежа (bank_card, sbp, yoomoney, и т.д.)",
    )

    # Описание
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Описание транзакции",
    )

    # Метаданные (JSONB)
    meta_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        doc="Дополнительные данные (JSONB)",
    )

    # Временные метки
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        doc="Время обработки транзакции",
    )

    # Баланс
    balance_before: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        doc="Баланс до транзакции",
    )

    balance_after: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        doc="Баланс после транзакции",
    )

    # Связь с кампанией
    campaign_id: Mapped[int | None] = mapped_column(
        nullable=True,
        index=True,
        doc="ID связанной кампании (если списание за кампанию)",
    )

    # Ошибки
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Сообщение об ошибке",
    )

    # Отношения
    user: Mapped["User"] = relationship(
        back_populates="transactions",
        lazy="selectin",
    )

    # Заявки на размещение (Спринт 6)
    placement_request: Mapped[Optional["PlacementRequest"]] = relationship(
        "PlacementRequest",
        back_populates="escrow_transaction",
        lazy="select",
        uselist=False,
    )

    # Индексы
    __table_args__ = (
        UniqueConstraint("payment_id", name="uq_transactions_payment_id"),
        Index("ix_transactions_user_type", "user_id", "type"),
        Index("ix_transactions_created", "created_at"),
        CheckConstraint("amount > 0", name="ck_transactions_amount_positive"),
        {
            "comment": "Финансовые транзакции пользователей",
        },
    )

    def __repr__(self) -> str:
        return f"<Transaction(id={self.id}, user_id={self.user_id}, amount={self.amount}, type={self.type.value})>"

    @property
    def is_topup(self) -> bool:
        """Проверяет, является ли транзакция пополнением."""
        return self.type == TransactionType.TOPUP

    @property
    def is_spend(self) -> bool:
        """Проверяет, является ли транзакция списанием."""
        return self.type == TransactionType.SPEND

    @property
    def is_bonus(self) -> bool:
        """Проверяет, является ли транзакция бонусом."""
        return self.type == TransactionType.BONUS

    @property
    def signed_amount(self) -> Decimal:
        """Возвращает сумму со знаком (+ для пополнений, - для списаний)."""
        if self.is_topup or self.is_bonus:
            return self.amount
        return -self.amount

    def to_dict(self) -> dict:
        """Конвертирует транзакцию в словарь."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "amount": float(self.amount),
            "type": self.type.value,
            "payment_id": self.payment_id,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "balance_before": float(self.balance_before),
            "balance_after": float(self.balance_after),
            "campaign_id": self.campaign_id,
        }
