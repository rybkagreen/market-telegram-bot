"""KudirRecordRepository for KudirRecord model operations."""

from datetime import date

from sqlalchemy import func, select

from src.db.models.kudir_record import KudirRecord
from src.db.repositories.base import BaseRepository


class KudirRecordRepository(BaseRepository[KudirRecord]):
    """Репозиторий для работы с записями КУДиР."""

    model = KudirRecord

    async def get_by_year(self, year: int) -> list[KudirRecord]:
        """Получить все записи КУДиР за год."""
        result = await self.session.execute(
            select(KudirRecord)
            .where(func.extract("year", KudirRecord.operation_date) == year)
            .order_by(KudirRecord.operation_date)
        )
        return list(result.scalars().all())

    async def get_by_date_range(self, start_date: date, end_date: date) -> list[KudirRecord]:
        """Получить записи КУДиР за период."""
        result = await self.session.execute(
            select(KudirRecord)
            .where(KudirRecord.operation_date >= start_date)
            .where(KudirRecord.operation_date <= end_date)
            .order_by(KudirRecord.operation_date)
        )
        return list(result.scalars().all())

    async def get_income_sum(self, year: int) -> float:
        """Получить сумму доходов за год."""
        result = await self.session.execute(
            select(func.coalesce(func.sum(KudirRecord.income_amount), 0)).where(
                func.extract("year", KudirRecord.operation_date) == year,
                KudirRecord.operation_type == "income",
            )
        )
        return float(result.scalar_one() or 0)

    async def get_expense_sum(self, year: int) -> float:
        """Получить сумму расходов за год."""
        result = await self.session.execute(
            select(func.coalesce(func.sum(KudirRecord.expense_amount), 0)).where(
                func.extract("year", KudirRecord.operation_date) == year,
                KudirRecord.operation_type == "expense",
            )
        )
        return float(result.scalar_one() or 0)
