"""
Transaction Repository для работы с транзакциями.
"""

from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.transaction import Transaction, TransactionType
from src.db.repositories.base import BaseRepository


class TransactionRepository(BaseRepository[Transaction]):
    """
    Репозиторий для работы с транзакциями.
    """

    model = Transaction

    def __init__(self, session: AsyncSession) -> None:
        """Инициализация репозитория."""
        super().__init__(session)

    async def get_by_user(
        self,
        user_id: int,
        transaction_type: TransactionType | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Transaction], int]:
        """
        Получить транзакции пользователя.

        Args:
            user_id: ID пользователя.
            transaction_type: Фильтр по типу.
            page: Номер страницы.
            page_size: Размер страницы.

        Returns:
            Кортеж (транзакции, общее количество).
        """
        filters = [Transaction.user_id == user_id]
        if transaction_type:
            filters.append(Transaction.type == transaction_type)

        # Общее количество
        count_query = select(func.count(Transaction.id)).where(*filters)
        total_result = await self.session.execute(count_query)
        total = total_result.scalar_one()

        # Транзакции
        query = (
            select(Transaction)
            .where(*filters)
            .order_by(Transaction.created_at.desc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        )

        result = await self.session.execute(query)
        transactions = list(result.scalars().all())

        return transactions, total

    async def get_total_by_type(
        self,
        user_id: int,
        transaction_type: TransactionType,
    ) -> Decimal:
        """
        Получить общую сумму транзакций по типу.

        Args:
            user_id: ID пользователя.
            transaction_type: Тип транзакции.

        Returns:
            Общая сумма.
        """
        query = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.user_id == user_id,
            Transaction.type == transaction_type,
        )

        result = await self.session.execute(query)
        return Decimal(str(result.scalar_one() or 0))

    async def create_transaction(
        self,
        user_id: int,
        amount: Decimal,
        transaction_type: TransactionType,
        payment_id: str | None = None,
        meta_json: dict[str, Any] | None = None,
    ) -> Transaction:
        """
        Создать транзакцию.

        Args:
            user_id: ID пользователя.
            amount: Сумма.
            transaction_type: Тип транзакции.
            payment_id: ID платежа.
            meta_json: Дополнительные данные.

        Returns:
            Созданная транзакция.
        """
        return await self.create(
            {
                "user_id": user_id,
                "amount": amount,
                "type": transaction_type,
                "payment_id": payment_id,
                "meta_json": meta_json,
            }
        )

    # ══════════════════════════════════════════════════════════════
    # S-04: Методы для velocity check и payout fee
    # ══════════════════════════════════════════════════════════════

    async def sum_topups_window(
        self,
        session: AsyncSession,
        user_id: int,
        days: int,
    ) -> Decimal:
        """
        Сумма пополнений пользователя за последние N дней (для velocity check).

        Args:
            session: Асинхронная сессия.
            user_id: ID пользователя.
            days: Количество дней.

        Returns:
            Сумма пополнений (минимум Decimal('0')).
        """
        from sqlalchemy import text

        stmt = text("""
            SELECT COALESCE(SUM(amount), 0)
            FROM transactions
            WHERE user_id = :uid
              AND type = 'topup'
              AND created_at >= NOW() - INTERVAL ':days days'
        """)
        result = await session.execute(stmt, {"uid": user_id, "days": days})
        return result.scalar_one() or Decimal("0")

    async def create_payout_fee(
        self,
        session: AsyncSession,
        user_id: int,
        amount: Decimal,
        payout_id: int,
    ) -> Transaction:
        """
        Зафиксировать комиссию за вывод как транзакцию PAYOUT_FEE.

        Args:
            session: Асинхронная сессия.
            user_id: ID пользователя.
            amount: Сумма комиссии.
            payout_id: ID заявки на выплату.

        Returns:
            Созданная транзакция.
        """
        attributes = {
            "user_id": user_id,
            "amount": amount,
            "type": TransactionType.PAYOUT_FEE,
            "meta_json": {"payout_id": payout_id},
            "description": f"Payout fee for payout #{payout_id}",
        }
        return await self.create(attributes)
