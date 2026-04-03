"""PlatformQuarterlyRevenue model for USN tax aggregation."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class PlatformQuarterlyRevenue(Base):
    """Квартальная агрегация выручки для ООО УСН 15% (доходы − расходы).

    Одна запись на квартал. Инкремент через SELECT ... FOR UPDATE.
    Налоговая база: usn_revenue − total_expenses.
    Налог: max(tax_base * 0.15, usn_revenue * 0.01) — минимальный 1%.
    """

    __tablename__ = "platform_quarterly_revenues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    quarter: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-4
    usn_revenue: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0"), server_default="0"
    )
    vat_accumulated: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0"), server_default="0"
    )
    ndfl_withheld: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0"), server_default="0"
    )
    # Sprint D.1: ООО УСН 15% expense & tax calculation fields
    total_expenses: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0"), server_default="0"
    )
    tax_base_15: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0"), server_default="0"
    )
    calculated_tax_15: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0"), server_default="0"
    )
    min_tax_1: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0"), server_default="0"
    )
    tax_due: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0"), server_default="0"
    )
    applicable_rate: Mapped[str | None] = mapped_column(String(5), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("year", "quarter", name="uq_platform_quarterly_revenues_year_quarter"),
    )

    def __repr__(self) -> str:
        return (
            f"<PlatformQuarterlyRevenue(year={self.year}, quarter={self.quarter}, "
            f"revenue={self.usn_revenue}, expenses={self.total_expenses}, "
            f"tax_due={self.tax_due}, rate={self.applicable_rate})>"
        )
