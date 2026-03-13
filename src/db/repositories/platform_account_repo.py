"""
PlatformAccount Repository для работы с системным счётом платформы.
Singleton репозиторий — всегда одна запись (id=1).
"""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.platform_account import PlatformAccount
from src.db.repositories.base import BaseRepository


class PlatformAccountRepo(BaseRepository[PlatformAccount]):
    """
    Репозиторий для работы с системным счётом платформы.

    Singleton — всегда одна запись с id=1.
    Все операции модификации используют atomic UPDATE для конкурентной безопасности.
    """

    model = PlatformAccount

    def __init__(self, session: AsyncSession) -> None:
        """Инициализация репозитория."""
        super().__init__(session)

    async def get_for_update(self, session: AsyncSession) -> PlatformAccount:
        """
        Получить singleton запись с блокировкой SELECT FOR UPDATE.

        Args:
            session: Асинхронная сессия.

        Returns:
            Единственную запись platform_account.

        Raises:
            RuntimeError: Если запись не найдена (singleton должен существовать).
        """
        stmt = select(PlatformAccount).where(PlatformAccount.id == 1).with_for_update()
        result = await session.execute(stmt)
        account = result.scalar_one_or_none()

        if account is None:
            raise RuntimeError("PlatformAccount singleton (id=1) not found")

        return account

    async def get(self, session: AsyncSession) -> PlatformAccount:
        """
        Получить singleton запись без блокировки.

        Args:
            session: Асинхронная сессия.

        Returns:
            Единственную запись platform_account.

        Raises:
            RuntimeError: Если запись не найдена.
        """
        stmt = select(PlatformAccount).where(PlatformAccount.id == 1)
        result = await session.execute(stmt)
        account = result.scalar_one_or_none()

        if account is None:
            raise RuntimeError("PlatformAccount singleton (id=1) not found")

        return account

    async def add_to_escrow(self, session: AsyncSession, amount: Decimal) -> None:
        """
        Добавить сумму в escrow_reserved.

        Args:
            session: Асинхронная сессия.
            amount: Сумма для добавления.
        """
        from sqlalchemy import text

        stmt = text("""
            UPDATE platform_account
            SET escrow_reserved = escrow_reserved + :amount
            WHERE id = 1
        """)
        await session.execute(stmt, {"amount": amount})

    async def release_from_escrow(
        self,
        session: AsyncSession,
        amount: Decimal,
        platform_fee: Decimal,
    ) -> None:
        """
        Освободить сумму из escrow и добавить комиссию в profit.

        Args:
            session: Асинхронная сессия.
            amount: Сумма для освобождения из escrow.
            platform_fee: Комиссия платформы для добавления в profit.
        """
        from sqlalchemy import text

        stmt = text("""
            UPDATE platform_account
            SET escrow_reserved = escrow_reserved - :amount,
                profit_accumulated = profit_accumulated + :platform_fee
            WHERE id = 1
        """)
        await session.execute(stmt, {"amount": amount, "platform_fee": platform_fee})

    async def add_to_payout_reserved(self, session: AsyncSession, amount: Decimal) -> None:
        """
        Добавить сумму в payout_reserved.

        Args:
            session: Асинхронная сессия.
            amount: Сумма для добавления.
        """
        from sqlalchemy import text

        stmt = text("""
            UPDATE platform_account
            SET payout_reserved = payout_reserved + :amount
            WHERE id = 1
        """)
        await session.execute(stmt, {"amount": amount})

    async def complete_payout(
        self,
        session: AsyncSession,
        gross_amount: Decimal,
        net_amount: Decimal,
    ) -> None:
        """
        Завершить выплату — уменьшить payout_reserved и увеличить total_payouts.

        Args:
            session: Асинхронная сессия.
            gross_amount: Полная сумма выплаты (gross).
            net_amount: Фактически выплаченная сумма (net).
        """
        from sqlalchemy import text

        stmt = text("""
            UPDATE platform_account
            SET payout_reserved = payout_reserved - :gross_amount,
                total_payouts = total_payouts + :net_amount
            WHERE id = 1
        """)
        await session.execute(stmt, {"gross_amount": gross_amount, "net_amount": net_amount})

    async def add_to_topups(self, session: AsyncSession, amount: Decimal) -> None:
        """
        Добавить сумму в total_topups (исторические пополнения).

        Args:
            session: Асинхронная сессия.
            amount: Сумма для добавления.
        """
        from sqlalchemy import text

        stmt = text("""
            UPDATE platform_account
            SET total_topups = total_topups + :amount
            WHERE id = 1
        """)
        await session.execute(stmt, {"amount": amount})

    async def add_to_profit(self, session: AsyncSession, amount: Decimal) -> None:
        """
        Добавить сумму в profit_accumulated (например, payout_fee).

        Args:
            session: Асинхронная сессия.
            amount: Сумма для добавления.
        """
        from sqlalchemy import text

        stmt = text("""
            UPDATE platform_account
            SET profit_accumulated = profit_accumulated + :amount
            WHERE id = 1
        """)
        await session.execute(stmt, {"amount": amount})
