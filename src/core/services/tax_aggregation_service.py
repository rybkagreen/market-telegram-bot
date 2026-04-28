"""TaxAggregationService — учёт выручки УСН и КУДиР.

Автоматически записывает доход платформы в квартальную агрегацию
и создаёт записи в книге учёта доходов (КУДиР) при каждом
поступлении средств (топап, комиссия размещения).
"""

import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.kudir_record import KudirRecord
from src.db.models.platform_quarterly_revenue import PlatformQuarterlyRevenue
from src.db.repositories.tax_repo import TaxRepository

logger = logging.getLogger(__name__)


class TaxAggregationService:
    """Сервис для налоговой агрегации (ИП УСН 6%).

    Вызывается при каждом поступлении дохода платформы:
    - Топап (gross_amount от ЮKassa)
    - Комиссия размещения (Промт 15.7: 21,2% от final_price —
      20% валовая + 1,5% сервисный сбор из 80% доли владельца;
      см. PLATFORM_TOTAL_RATE в src/constants/fees.py)

    Методы:
        record_income_for_usn: записать доход в квартал и КУДиР
        _get_quarter_string: получить строку квартала 'YYYY-QN'
    """

    @classmethod
    async def record_income_for_usn(
        cls,
        session: AsyncSession,
        amount: Decimal,
        description: str,
        vat_amount: Decimal = Decimal("0"),
    ) -> tuple[PlatformQuarterlyRevenue, KudirRecord]:
        """Записать доход в квартальную агрегацию УСН и КУДиР.

        Args:
            session: Асинхронная сессия.
            amount: Сумма дохода (выручка платформы).
            description: Описание операции для КУДиР.
            vat_amount: Сумма НДС (22% от комиссии платформы).

        Returns:
            Кортеж (quarterly_revenue, kudir_record).
        """
        now = datetime.now(UTC)
        year = now.year
        quarter_num = (now.month - 1) // 3 + 1  # 1-4
        quarter_str = cls._get_quarter_string(year, quarter_num)

        repo = TaxRepository(session)

        # Атомарный upsert квартала
        quarter_revenue = await repo.get_or_create_quarter_revenue(year, quarter_num)

        # Инкремент выручки
        await repo.increment_usn_revenue(quarter_revenue, amount)

        # Инкремент НДС (если применимо)
        if vat_amount > 0:
            await repo.increment_vat_accumulated(quarter_revenue, vat_amount)

        # Следующий номер записи КУДиР
        entry_number = await repo.get_next_kudir_entry_number(quarter_str)

        # Создание записи КУДиР
        kudir_record = await repo.create_kudir_record(
            quarter=quarter_str,
            entry_number=entry_number,
            description=description,
            income_amount=amount,
        )

        logger.info(
            f"Tax income recorded: +{amount} ₽ for {quarter_str}, "
            f"KUDiR entry #{entry_number}, total USN revenue: "
            f"{quarter_revenue.usn_revenue} ₽, VAT: {vat_amount} ₽"
        )

        return quarter_revenue, kudir_record

    @classmethod
    def _get_quarter_string(cls, year: int, quarter: int) -> str:
        """Получить строку квартала в формате 'YYYY-QN'.

        Args:
            year: Год.
            quarter: Номер квартала (1-4).

        Returns:
            Строка квартала, напр. '2026-Q1'.
        """
        return f"{year}-Q{quarter}"

    @classmethod
    async def get_quarterly_summary(
        cls, session: AsyncSession, year: int, quarter: int
    ) -> dict[str, Any]:
        """Получить сводку по кварталу для администратора (ООО УСН 15%).

        Args:
            session: Асинхронная сессия.
            year: Год.
            quarter: Номер квартала (1-4).

        Returns:
            Dict с usn_revenue, total_expenses, tax_due, applicable_rate, kudir_entries[].

        Raises:
            ValueError: Если квартал не найден.
        """
        from decimal import Decimal

        from src.db.models.platform_quarterly_revenue import PlatformQuarterlyRevenue

        repo = TaxRepository(session)

        # Получить квартальную выручку
        result = await session.execute(
            select(PlatformQuarterlyRevenue).where(
                PlatformQuarterlyRevenue.year == year,
                PlatformQuarterlyRevenue.quarter == quarter,
            )
        )
        quarter_revenue = result.scalar_one_or_none()
        if not quarter_revenue:
            raise ValueError(f"Quarter {year}-Q{quarter} not found")

        # Получить записи КУДиР
        quarter_str = cls._get_quarter_string(year, quarter)
        kudir_records = await repo.get_by_quarter(quarter_str)

        # Форматируем записи с учётом доходов и расходов
        kudir_entries = [
            {
                "entry_number": r.entry_number,
                "operation_date": r.operation_date,
                "operation_type": r.operation_type,
                "expense_category": r.expense_category,
                "description": r.description,
                "income_amount": r.income_amount,
                "expense_amount": r.expense_amount,
            }
            for r in kudir_records
        ]

        total_income = sum(
            (r.income_amount for r in kudir_records if r.operation_type == "income"),
            Decimal("0"),
        )
        total_expenses = sum(
            (r.expense_amount for r in kudir_records if r.expense_amount is not None),
            Decimal("0"),
        )

        return {
            "year": year,
            "quarter": quarter,
            "usn_revenue": quarter_revenue.usn_revenue,
            "vat_accumulated": quarter_revenue.vat_accumulated,
            "ndfl_withheld": quarter_revenue.ndfl_withheld,
            "total_expenses": quarter_revenue.total_expenses,
            "tax_base_15": quarter_revenue.tax_base_15,
            "calculated_tax_15": quarter_revenue.calculated_tax_15,
            "min_tax_1": quarter_revenue.min_tax_1,
            "tax_due": quarter_revenue.tax_due,
            "applicable_rate": quarter_revenue.applicable_rate,
            "kudir_entries": kudir_entries,
            "total_income": total_income,
            "total_expenses_kudir": total_expenses,
        }

    @classmethod
    async def record_expense_for_usn(
        cls,
        session: AsyncSession,
        amount: Decimal,
        expense_category: str,
        description: str,
    ) -> tuple[PlatformQuarterlyRevenue, KudirRecord]:
        """Записать расход в квартальную агрегацию УСН и КУДиР.

        Args:
            session: Асинхронная сессия.
            amount: Сумма расхода.
            expense_category: Категория расхода (ст. 346.16 НК РФ).
            description: Описание операции для КУДиР.

        Returns:
            Кортеж (quarterly_revenue, kudir_record).
        """
        now = datetime.now(UTC)
        year = now.year
        quarter_num = (now.month - 1) // 3 + 1  # 1-4
        quarter_str = cls._get_quarter_string(year, quarter_num)

        repo = TaxRepository(session)

        # Атомарный upsert квартала
        quarter_revenue = await repo.get_or_create_quarter_revenue(year, quarter_num)

        # Инкремент расходов и пересчёт налоговых метрик
        await repo.increment_total_expenses(quarter_revenue, amount)

        # Следующий номер записи КУДиР
        entry_number = await repo.get_next_expense_entry_number(quarter_str)

        # Создание записи КУДиР с типом 'expense'
        kudir_record = await repo.create_kudir_record(
            quarter=quarter_str,
            entry_number=entry_number,
            description=description,
            income_amount=Decimal("0"),
            operation_type="expense",
            expense_category=expense_category,
            expense_amount=amount,
        )

        logger.info(
            f"Tax expense recorded: +{amount} ₽ ({expense_category}) for {quarter_str}, "
            f"KUDiR entry #{entry_number}, total expenses: "
            f"{quarter_revenue.total_expenses} ₽, tax_due: {quarter_revenue.tax_due} ₽"
        )

        return quarter_revenue, kudir_record

    @classmethod
    def calculate_tax_due(cls, income: Decimal, expenses: Decimal) -> dict[str, Any]:
        """Рассчитать налог УСН 15% с учётом минимального налога 1%.

        Формула (ст. 346.21 НК РФ):
            tax_base = max(0, income - expenses)
            calculated_tax_15 = tax_base * 0.15
            min_tax_1 = income * 0.01
            tax_due = max(calculated_tax_15, min_tax_1)

        Args:
            income: Совокупные доходы за квартал.
            expenses: Совокупные расходы за квартал.

        Returns:
            Dict с tax_base, calculated_tax_15, min_tax_1, tax_due, applicable_rate.
        """
        tax_base = max(Decimal("0"), income - expenses)
        calculated_tax_15 = (tax_base * Decimal("0.15")).quantize(Decimal("0.01"))
        min_tax_1 = (income * Decimal("0.01")).quantize(Decimal("0.01"))
        tax_due = max(calculated_tax_15, min_tax_1)
        applicable_rate = "15%" if calculated_tax_15 >= min_tax_1 else "1%"

        return {
            "tax_base": tax_base,
            "calculated_tax_15": calculated_tax_15,
            "min_tax_1": min_tax_1,
            "tax_due": tax_due,
            "applicable_rate": applicable_rate,
        }

    @classmethod
    async def record_storno(
        cls,
        session: AsyncSession,
        original_txn_id: int,
        reason: str,
    ) -> dict[str, Any]:
        """Сторнировать оригинальную транзакцию с пересчётом налоговой базы.

        Steps:
            1. Найти оригинальную транзакцию.
            2. Если is_reversed=True → raise ValueError.
            3. Создать транзакцию-сторно с amount = -original.amount.
            4. Обновить is_reversed=True на оригинале.
            5. Если операция была доходом → decrement_usn_revenue().
            6. Если операция была расходом → decrement_total_expenses().
            7. Создать KudirRecord с отрицательной суммой.
            8. Вернуть результат.

        Args:
            session: Асинхронная сессия.
            original_txn_id: ID оригинальной транзакции.
            reason: Причина сторнирования.

        Returns:
            Dict с storno_txn_id, adjusted_tax_metrics, kudir_entry_number.

        Raises:
            ValueError: Если транзакция не найдена или уже сторнирована.
        """
        from src.db.models.transaction import Transaction

        # Шаг 1: Найти оригинальную транзакцию
        result = await session.execute(select(Transaction).where(Transaction.id == original_txn_id))
        original = result.scalar_one_or_none()
        if not original:
            raise ValueError(f"Transaction {original_txn_id} not found")

        if original.is_reversed:
            raise ValueError(f"Transaction {original_txn_id} already reversed")

        now = datetime.now(UTC)
        year = now.year
        quarter_num = (now.month - 1) // 3 + 1
        quarter_str = cls._get_quarter_string(year, quarter_num)

        repo = TaxRepository(session)
        quarter_revenue = await repo.get_or_create_quarter_revenue(year, quarter_num)

        # Шаг 5-6: Декрементировать квартальные показатели
        if original.type.value in ("topup", "commission", "escrow_release"):
            # Доход → уменьшаем выручку
            await repo.decrement_usn_revenue(quarter_revenue, abs(original.amount))
        elif original.type.value in ("payout", "payout_fee", "platform_fee"):
            # Расход → уменьшаем расходы
            await repo.decrement_total_expenses(quarter_revenue, abs(original.amount))

        # Шаг 7: Создать KudirRecord сторнирования
        entry_number = await repo.get_next_kudir_entry_number(quarter_str)
        is_income_storno = original.type.value in ("topup", "commission", "escrow_release")

        kudir_record = await repo.create_kudir_record(
            quarter=quarter_str,
            entry_number=entry_number,
            description=f"Сторно: {reason} (orig txn #{original_txn_id})",
            income_amount=Decimal("0"),
            operation_type="expense" if not is_income_storno else "income",
            expense_category=original.expense_category,
            expense_amount=None if is_income_storno else abs(original.amount),
        )
        # Для сторнирования дохода — запишем отрицательную сумму в income_amount
        if is_income_storno:
            kudir_record.income_amount = -abs(original.amount)
            await session.flush()
            await session.refresh(kudir_record)

        # Пометить оригинал как сторнированный
        original.is_reversed = True
        await session.flush()
        await session.refresh(original)

        logger.info(
            f"Storno recorded: txn #{original_txn_id}, reason={reason}, "
            f"adjusted tax_due={quarter_revenue.tax_due} ₽"
        )

        return {
            "storno_kudir_entry": entry_number,
            "adjusted_tax_due": str(quarter_revenue.tax_due),
            "adjusted_applicable_rate": quarter_revenue.applicable_rate,
            "original_txn_id": original_txn_id,
        }
