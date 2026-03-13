"""
Модель системного счёта платформы PlatformAccount.
Спринт 2 — аудит балансов платформы.

Singleton — всегда одна запись (id=1).
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class PlatformAccount(Base):
    """
    Singleton — всегда одна запись (id=1).
    Системный счёт платформы для аудита балансов.
    """

    __tablename__ = "platform_account"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)

    # Текущие обязательства
    escrow_reserved: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        server_default="0",
        doc="Зарезервировано в эскроу (SUM final_price WHERE status='escrow')",
    )

    payout_reserved: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        server_default="0",
        doc="Зарезервировано на выплаты (SUM gross_amount WHERE pending/processing)",
    )

    # Прибыль платформы (15% эскроу + 1.5% payout fees)
    profit_accumulated: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        server_default="0",
        doc="Накопленная прибыль платформы",
    )

    # Исторические итоги (для аудита)
    total_topups: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        server_default="0",
        doc="Исторически пополнено (desired_balance)",
    )

    total_payouts: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        server_default="0",
        doc="Исторически выплачено (net_amount)",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        onupdate=func.now(),
        doc="Время последнего обновления",
    )

    def __repr__(self) -> str:
        return (
            f"<PlatformAccount(id={self.id}, escrow_reserved={self.escrow_reserved}, "
            f"payout_reserved={self.payout_reserved}, profit_accumulated={self.profit_accumulated})>"
        )
