"""
Payout Repository для работы с выплатами.
Расширяет BaseRepository специфичными методами для Payout.
"""

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.payout import Payout, PayoutStatus
from src.db.repositories.base import BaseRepository


class PayoutRepository(BaseRepository[Payout]):
    """
    Репозиторий для работы с выплатами.

    Методы:
        get_available_amount: Сумма всех выплат в статусе PENDING для owner_id
        get_total_earned: Сумма всех выплат в статусе PAID для owner_id
        get_by_owner: Получить все выплаты владельца
        get_pending_payouts: Получить все ожидающие выплаты
    """

    model = Payout

    def __init__(self, session: AsyncSession) -> None:
        """Инициализация репозитория."""
        super().__init__(session)

    async def get_available_amount(self, owner_id: int) -> Decimal:
        """
        Сумма всех выплат в статусе PENDING для owner_id.

        Args:
            owner_id: ID владельца в БД (users.id).

        Returns:
            Сумма к выплате (Decimal), 0 если нет pending выплат.
        """
        stmt = (
            select(func.sum(Payout.amount))
            .where(
                Payout.owner_id == owner_id,
                Payout.status == PayoutStatus.PENDING,
            )
        )
        result = await self.session.execute(stmt)
        balance = result.scalar_one() or Decimal("0")
        return balance

    async def get_total_earned(self, owner_id: int) -> Decimal:
        """
        Сумма всех выплат в статусе PAID для owner_id.

        Args:
            owner_id: ID владельца в БД.

        Returns:
            Общая сумма заработанных средств (Decimal).
        """
        stmt = (
            select(func.sum(Payout.amount))
            .where(
                Payout.owner_id == owner_id,
                Payout.status == PayoutStatus.PAID,
            )
        )
        result = await self.session.execute(stmt)
        total = result.scalar_one() or Decimal("0")
        return total

    async def get_by_owner(
        self,
        owner_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Payout]:
        """
        Получить все выплаты владельца с пагинацией.

        Args:
            owner_id: ID владельца в БД.
            limit: Максимальное количество записей.
            offset: Смещение.

        Returns:
            Список выплат.
        """
        stmt = (
            select(Payout)
            .where(Payout.owner_id == owner_id)
            .order_by(Payout.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_pending_payouts(self, limit: int = 100) -> list[Payout]:
        """
        Получить все ожидающие выплаты.

        Args:
            limit: Максимальное количество записей.

        Returns:
            Список pending выплат.
        """
        stmt = (
            select(Payout)
            .where(Payout.status == PayoutStatus.PENDING)
            .order_by(Payout.created_at)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_available_amounts_bulk(
        self,
        owner_ids: list[int],
    ) -> dict[int, Decimal]:
        """
        Получить суммы доступных выплат для нескольких владельцев.

        Args:
            owner_ids: Список ID владельцев.

        Returns:
            dict {owner_id: available_amount}.
        """
        if not owner_ids:
            return {}

        stmt = (
            select(Payout.owner_id, func.sum(Payout.amount))
            .where(
                Payout.owner_id.in_(owner_ids),
                Payout.status == PayoutStatus.PENDING,
            )
            .group_by(Payout.owner_id)
        )
        result = await self.session.execute(stmt)
        return {row.owner_id: (row[1] or Decimal("0")) for row in result.all()}


# ─────────────────────────────────────────────
# Helper function для использования без явного создания репозитория
# ─────────────────────────────────────────────

async def get_available_payout_amount(owner_user_id: int) -> Decimal:
    """
    Получить доступную сумму к выводу для владельца канала.

    Args:
        owner_user_id: ID владельца в БД (users.id).

    Returns:
        Сумма к выводу (Decimal).

    Usage:
        from src.db.repositories.payout_repo import get_available_payout_amount
        amount = await get_available_payout_amount(user.id)
    """
    from src.db.session import async_session_factory

    async with async_session_factory() as session:
        repo = PayoutRepository(session)
        return await repo.get_available_amount(owner_user_id)
