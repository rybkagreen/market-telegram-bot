"""KudirRecord model for КУДиР (Книга учёта доходов и расходов)."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base, TimestampMixin


class KudirRecord(Base, TimestampMixin):
    """Запись в книге учёта доходов и расходов (КУДиР) для ООО УСН 15%.

    Каждая запись: номер, дата, описание, тип операции (доход/расход),
    категория расхода (ст. 346.16 НК РФ), сумма.
    entry_number инкрементируется атомарно внутри квартала.
    """

    __tablename__ = "kudir_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    quarter: Mapped[str] = mapped_column(String(10), nullable=False)  # формат '2026-Q1'
    entry_number: Mapped[int] = mapped_column(Integer, nullable=False)
    operation_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )
    operation_type: Mapped[str] = mapped_column(
        String(10), nullable=False, default="income", server_default="income"
    )
    expense_category: Mapped[str | None] = mapped_column(String(30), nullable=True)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    income_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    expense_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)

    def __repr__(self) -> str:
        return (
            f"<KudirRecord(id={self.id}, quarter={self.quarter!r}, "
            f"entry={self.entry_number}, type={self.operation_type})>"
        )
