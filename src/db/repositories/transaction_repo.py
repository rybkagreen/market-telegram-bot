"""TransactionRepository for Transaction model operations."""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select

from src.db.models.transaction import Transaction, TransactionType
from src.db.repositories.base import BaseRepository


class TransactionRepository(BaseRepository[Transaction]):
    """Репозиторий для работы с транзакциями."""

    model = Transaction

    async def get_by_user(self, user_id: int, limit: int = 50) -> list[Transaction]:
        """Получить последние транзакции пользователя."""
        result = await self.session.execute(
            select(Transaction).where(Transaction.user_id == user_id).order_by(Transaction.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_placement(self, placement_request_id: int) -> list[Transaction]:
        """Получить транзакции по заявке."""
        result = await self.session.execute(select(Transaction).where(Transaction.placement_request_id == placement_request_id))
        return list(result.scalars().all())

    async def sum_topups_30d(self, user_id: int) -> Decimal:
        """Посчитать сумму топапов за 30 дней."""
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        result = await self.session.execute(
            select(func.coalesce(func.sum(Transaction.amount), Decimal("0"))).where(
                Transaction.user_id == user_id,
                Transaction.type == TransactionType.topup,
                Transaction.created_at > thirty_days_ago,
            )
        )
        return result.scalar() or Decimal("0")

    async def sum_payouts_30d(self, user_id: int) -> Decimal:
        """Посчитать сумму выплат за 30 дней."""
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        result = await self.session.execute(
            select(func.coalesce(func.sum(Transaction.amount), Decimal("0"))).where(
                Transaction.user_id == user_id,
                Transaction.type == TransactionType.payout,
                Transaction.created_at > thirty_days_ago,
            )
        )
        return result.scalar() or Decimal("0")

    async def create(self, data: dict[str, Any]) -> Transaction:
        """Создать транзакцию."""
        txn = Transaction(**data)
        self.session.add(txn)
        await self.session.flush()
        return txn
