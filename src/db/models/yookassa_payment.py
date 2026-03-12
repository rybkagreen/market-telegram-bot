"""
Модель для хранения платежей ЮKassa.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base

if TYPE_CHECKING:
    pass


class YooKassaPayment(Base):
    """
    Модель платежа ЮKassa.

    Attributes:
        id: Уникальный идентификатор платежа.
        payment_id: UUID платежа от ЮKassa (уникальный).
        user_id: ID пользователя (FK на User).
        amount_rub: Сумма в рублях.
        credits: Количество кредитов для зачисления.
        status: Статус платежа (pending/succeeded/canceled/failed).
        description: Описание платежа.
        confirmation_url: URL для оплаты.
        idempotency_key: Уникальный ключ идемпотентности.
        created_at: Дата создания.
        paid_at: Дата оплаты.
    """

    __tablename__ = "yookassa_payment"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Payment ID от ЮKassa
    payment_id: Mapped[str] = mapped_column(
        String(36),
        unique=True,
        nullable=False,
        index=True,
        doc="UUID платежа от ЮKassa",
    )

    # Foreign keys
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID пользователя",
    )

    # Amount and credits
    amount_rub: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        doc="Сумма в рублях",
    )

    credits: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="Количество кредитов для зачисления",
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        index=True,
        doc="Статус платежа (pending/succeeded/canceled/failed)",
    )

    # Description
    description: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Описание платежа",
    )

    # Confirmation URL
    confirmation_url: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
        doc="URL для оплаты",
    )

    # Idempotency key
    idempotency_key: Mapped[str] = mapped_column(
        String(36),
        unique=True,
        nullable=False,
        doc="Уникальный ключ идемпотентности",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Дата оплаты",
    )
