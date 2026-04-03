"""TaxRepository — репозиторий для налоговой агрегации и КУДиР."""

import logging
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.kudir_record import KudirRecord
from src.db.models.platform_quarterly_revenue import PlatformQuarterlyRevenue
from src.db.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class TaxRepository(BaseRepository[PlatformQuarterlyRevenue]):
    """Репозиторий для работы с квартальной выручкой и КУДиР."""

    model = PlatformQuarterlyRevenue

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self._kudir_session = session

    async def get_or_create_quarter_revenue(
        self, year: int, quarter: int
    ) -> PlatformQuarterlyRevenue:
        """Получить или создать запись квартальной выручки с блокировкой.

        SELECT ... FOR UPDATE для атомарного инкремента.

        Args:
            year: Год (напр. 2026).
            quarter: Квартал (1-4).

        Returns:
            Запись PlatformQuarterlyRevenue.
        """
        result = await self.session.execute(
            select(PlatformQuarterlyRevenue)
            .where(
                PlatformQuarterlyRevenue.year == year,
                PlatformQuarterlyRevenue.quarter == quarter,
            )
            .with_for_update()
        )
        record = result.scalar_one_or_none()

        if record is not None:
            return record

        # Создаём новую запись
        record = PlatformQuarterlyRevenue(
            year=year,
            quarter=quarter,
            usn_revenue=Decimal("0"),
            vat_accumulated=Decimal("0"),
            ndfl_withheld=Decimal("0"),
        )
        self.session.add(record)
        await self.session.flush()
        await self.session.refresh(record)

        logger.info(f"Created quarterly revenue record: {year}-Q{quarter}")
        return record

    async def increment_usn_revenue(
        self, record: PlatformQuarterlyRevenue, amount: Decimal
    ) -> None:
        """Инкрементировать выручку УСН.

        Args:
            record: Запись квартала.
            amount: Сумма для добавления.
        """
        record.usn_revenue += amount
        await self.session.flush()
        await self.session.refresh(record)

    async def increment_vat_accumulated(
        self, record: PlatformQuarterlyRevenue, amount: Decimal
    ) -> None:
        """Инкрементировать накопленный НДС.

        Args:
            record: Запись квартала.
            amount: Сумма НДС.
        """
        record.vat_accumulated += amount
        await self.session.flush()
        await self.session.refresh(record)

    async def increment_ndfl_withheld(
        self, record: PlatformQuarterlyRevenue, amount: Decimal
    ) -> None:
        """Инкрементировать удержанный НДФЛ.

        Args:
            record: Запись квартала.
            amount: Сумма НДФЛ.
        """
        record.ndfl_withheld += amount
        await self.session.flush()
        await self.session.refresh(record)

    async def get_next_kudir_entry_number(self, quarter: str) -> int:
        """Получить следующий номер записи КУДиР для квартала.

        SELECT MAX(entry_number) WHERE quarter = ... + 1.

        Args:
            quarter: Квартал в формате 'YYYY-QN'.

        Returns:
            Следующий номер записи (начиная с 1).
        """
        result = await self._kudir_session.execute(
            select(func.coalesce(func.max(KudirRecord.entry_number), 0)).where(
                KudirRecord.quarter == quarter
            )
        )
        max_num = result.scalar() or 0
        return max_num + 1

    async def create_kudir_record(
        self,
        quarter: str,
        entry_number: int,
        description: str,
        income_amount: Decimal,
        operation_type: str = "income",
        expense_category: str | None = None,
        expense_amount: Decimal | None = None,
    ) -> KudirRecord:
        """Создать запись КУДиР (доход или расход).

        Args:
            quarter: Квартал ('YYYY-QN').
            entry_number: Номер записи.
            description: Описание операции.
            income_amount: Сумма дохода (для income) или 0 (для expense).
            operation_type: Тип операции ('income' или 'expense').
            expense_category: Категория расхода (ст. 346.16 НК РФ).
            expense_amount: Сумма расхода (для expense).

        Returns:
            Созданная запись KudirRecord.
        """
        record = KudirRecord(
            quarter=quarter,
            entry_number=entry_number,
            operation_date=datetime.now(UTC),
            operation_type=operation_type,
            expense_category=expense_category,
            description=description,
            income_amount=income_amount,
            expense_amount=expense_amount,
        )
        self._kudir_session.add(record)
        await self._kudir_session.flush()
        await self._kudir_session.refresh(record)
        return record

    async def get_by_quarter(self, quarter_str: str) -> list[KudirRecord]:
        """Получить все записи КУДиР для указанного квартала.

        SELECT * FROM kudir_records WHERE quarter = :quarter
        ORDER BY entry_number ASC.

        Args:
            quarter_str: Квартал в формате 'YYYY-QN'.

        Returns:
            Список записей KudirRecord, отсортированных по entry_number.
        """
        result = await self.session.execute(
            select(KudirRecord)
            .where(KudirRecord.quarter == quarter_str)
            .order_by(KudirRecord.entry_number.asc())
        )
        return list(result.scalars().all())

    async def increment_total_expenses(
        self, record: PlatformQuarterlyRevenue, amount: Decimal
    ) -> None:
        """Инкрементировать суммарные расходы квартала.

        SELECT ... FOR UPDATE уже получен при вызове get_or_create_quarter_revenue.

        Args:
            record: Запись квартала.
            amount: Сумма для добавления.
        """
        record.total_expenses += amount
        await self.session.flush()
        await self.session.refresh(record)
        # Пересчитать налоговые метрики
        await self.update_tax_metrics(record)

    async def update_tax_metrics(self, record: PlatformQuarterlyRevenue) -> None:
        """Пересчитать налоговые показатели УСН 15%.

        Формула:
            tax_base = max(0, usn_revenue - total_expenses)
            calculated_tax_15 = tax_base * 0.15
            min_tax_1 = usn_revenue * 0.01
            tax_due = max(calculated_tax_15, min_tax_1)
            applicable_rate = '15%' если calculated_tax_15 >= min_tax_1, иначе '1%'

        Args:
            record: Запись квартала.
        """
        tax_base = max(Decimal("0"), record.usn_revenue - record.total_expenses)
        calculated_tax_15 = (tax_base * Decimal("0.15")).quantize(Decimal("0.01"))
        min_tax_1 = (record.usn_revenue * Decimal("0.01")).quantize(Decimal("0.01"))
        tax_due = max(calculated_tax_15, min_tax_1)
        applicable_rate = "15%" if calculated_tax_15 >= min_tax_1 else "1%"

        record.tax_base_15 = tax_base
        record.calculated_tax_15 = calculated_tax_15
        record.min_tax_1 = min_tax_1
        record.tax_due = tax_due
        record.applicable_rate = applicable_rate

        await self.session.flush()
        await self.session.refresh(record)

    async def get_next_expense_entry_number(self, quarter: str) -> int:
        """Получить следующий номер записи расхода для квартала.

        SELECT MAX(entry_number) WHERE quarter = ... + 1.

        Args:
            quarter: Квартал в формате 'YYYY-QN'.

        Returns:
            Следующий номер записи (начиная с 1).
        """
        result = await self._kudir_session.execute(
            select(func.coalesce(func.max(KudirRecord.entry_number), 0)).where(
                KudirRecord.quarter == quarter
            )
        )
        max_num = result.scalar() or 0
        return max_num + 1

    async def decrement_usn_revenue(
        self, record: PlatformQuarterlyRevenue, amount: Decimal
    ) -> None:
        """Декрементировать выручку УСН (для сторнирования).

        Args:
            record: Запись квартала.
            amount: Сумма для вычитания.
        """
        record.usn_revenue = max(Decimal("0"), record.usn_revenue - amount)
        await self.session.flush()
        await self.session.refresh(record)
        await self.update_tax_metrics(record)

    async def decrement_total_expenses(
        self, record: PlatformQuarterlyRevenue, amount: Decimal
    ) -> None:
        """Декрементировать суммарные расходы (для сторнирования расходов).

        Args:
            record: Запись квартала.
            amount: Сумма для вычитания.
        """
        record.total_expenses = max(Decimal("0"), record.total_expenses - amount)
        await self.session.flush()
        await self.session.refresh(record)
        await self.update_tax_metrics(record)
