"""
Модель для хранения крипто-платежей через CryptoBot и Telegram Stars.
"""

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.db.models.user import User


class PaymentMethod(str, enum.Enum):
    """Методы оплаты."""

    CRYPTOBOT = "cryptobot"
    STARS = "stars"


class PaymentStatus(str, enum.Enum):
    """Статусы платежей."""

    PENDING = "pending"
    PAID = "paid"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class CryptoPayment(Base, TimestampMixin):
    """
    Модель крипто-платежа (CryptoBot / Telegram Stars).

    Attributes:
        id: Уникальный идентификатор платежа.
        user_id: ID пользователя (FK на User).
        method: Метод оплаты (cryptobot / stars).
        invoice_id: ID инвойса в CryptoBot (уникальный).
        currency: Валюта платежа (USDT, TON, BTC...).
        amount: Сумма в валюте.
        telegram_payment_charge_id: ID платежа Telegram (для Stars).
        stars_amount: Количество Stars (для Stars оплаты).
        credits: Количество кредитов для зачисления.
        bonus_credits: Бонусные кредиты (за объём пакета).
        status: Статус платежа.
        payload: Произвольные данные (например "user:123:credits:300").
        credited_at: Когда кредиты зачислены пользователю.
    """

    __tablename__ = "crypto_payments"

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Foreign keys
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID пользователя",
    )

    # Метод оплаты
    method: Mapped[PaymentMethod] = mapped_column(
        Enum(PaymentMethod, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        doc="Метод оплаты (cryptobot / stars)",
    )

    # CryptoBot fields
    invoice_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        unique=True,
        index=True,
        doc="ID инвойса в CryptoBot",
    )

    currency: Mapped[str | None] = mapped_column(
        String(16),
        nullable=True,
        doc="Валюта платежа (USDT, TON, BTC...)",
    )

    amount: Mapped[float | None] = mapped_column(
        Numeric(20, 8),
        nullable=True,
        doc="Сумма в валюте",
    )

    # Stars fields
    telegram_payment_charge_id: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        doc="ID платежа Telegram (для Stars)",
    )

    stars_amount: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        doc="Количество Stars (для Stars оплаты)",
    )

    # Credits to award
    credits: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="Количество кредитов для зачисления",
    )

    bonus_credits: Mapped[int] = mapped_column(
        Integer,
        default=0,
        doc="Бонусные кредиты (за объём пакета)",
    )

    # Status
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, values_callable=lambda x: [e.value for e in x]),
        default=PaymentStatus.PENDING,
        nullable=False,
        index=True,
        doc="Статус платежа",
    )

    # Raw payload
    payload: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        doc="Произвольные данные платежа",
    )

    # Raw response from API
    meta_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        doc="Сырой ответ от API платежной системы",
    )

    # When credited to user
    credited_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        doc="Когда кредиты зачислены пользователю",
    )

    # Отношения
    user: Mapped["User"] = relationship(
        back_populates="crypto_payments",
        lazy="selectin",
    )

    # Индексы
    __table_args__ = (
        Index("ix_crypto_payments_status", "status"),
        Index("ix_crypto_payments_user_status", "user_id", "status"),
        {
            "comment": "Крипто-платежи (CryptoBot / Telegram Stars)",
        },
    )

    def __repr__(self) -> str:
        return f"<CryptoPayment(id={self.id}, user_id={self.user_id}, status={self.status.value}, credits={self.credits})>"

    @property
    def total_credits(self) -> int:
        """Общее количество кредитов (основные + бонус)."""
        return self.credits + self.bonus_credits

    @property
    def is_pending(self) -> bool:
        """Платёж ожидает оплаты."""
        return self.status == PaymentStatus.PENDING

    @property
    def is_paid(self) -> bool:
        """Платёж оплачен."""
        return self.status == PaymentStatus.PAID

    @property
    def is_expired(self) -> bool:
        """Платёж истёк."""
        return self.status == PaymentStatus.EXPIRED

    @property
    def is_cancelled(self) -> bool:
        """Платёж отменён."""
        return self.status == PaymentStatus.CANCELLED

    def to_dict(self) -> dict:
        """Конвертирует платёж в словарь."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "method": self.method.value,
            "invoice_id": self.invoice_id,
            "currency": self.currency,
            "amount": float(self.amount) if self.amount else None,
            "stars_amount": self.stars_amount,
            "credits": self.credits,
            "bonus_credits": self.bonus_credits,
            "total_credits": self.total_credits,
            "status": self.status.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "credited_at": self.credited_at.isoformat() if self.credited_at else None,
        }
