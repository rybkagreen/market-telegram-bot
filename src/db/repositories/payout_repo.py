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
        stmt = select(func.sum(Payout.amount)).where(
            Payout.owner_id == owner_id,
            Payout.status == PayoutStatus.PENDING,
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
        stmt = select(func.sum(Payout.amount)).where(
            Payout.owner_id == owner_id,
            Payout.status == PayoutStatus.PAID,
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

    # ══════════════════════════════════════════════════════════════
    # S-04: Методы для velocity check и создания payout
    # ══════════════════════════════════════════════════════════════

    async def sum_completed_payouts_window(
        self,
        session: AsyncSession,
        user_id: int,
        days: int,
    ) -> Decimal:
        """
        Сумма выплат пользователя за последние N дней (для velocity check).

        Args:
            session: Асинхронная сессия.
            user_id: ID пользователя.
            days: Количество дней.

        Returns:
            Сумма выплат (минимум Decimal('0')).
        """
        from sqlalchemy import text

        stmt = text("""
            SELECT COALESCE(SUM(COALESCE(gross_amount, amount, 0)), 0)
            FROM payouts
            WHERE owner_id = :uid
              AND status IN ('paid', 'processing')
              AND created_at >= NOW() - INTERVAL ':days days'
        """)
        result = await session.execute(stmt, {"uid": user_id, "days": days})
        return result.scalar_one() or Decimal("0")

    async def get_active_payout(
        self,
        session: AsyncSession,
        user_id: int,
    ) -> Payout | None:
        """
        Проверить наличие активной заявки на выплату.

        Args:
            session: Асинхронная сессия.
            user_id: ID пользователя.

        Returns:
            Payout или None.
        """
        stmt = select(Payout).where(
            Payout.owner_id == user_id,
            Payout.status.in_([PayoutStatus.PENDING, PayoutStatus.PROCESSING]),
        ).limit(1)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_payout(
        self,
        session: AsyncSession,
        user_id: int,
        gross_amount: Decimal,
        fee_amount: Decimal,
        net_amount: Decimal,
    ) -> Payout:
        """
        Создать заявку на выплату с полями v4.2.

        Args:
            session: Асинхронная сессия.
            user_id: ID пользователя.
            gross_amount: Запрошенная сумма (gross).
            fee_amount: Комиссия платформы.
            net_amount: Сумма к выплате (net).

        Returns:
            Созданная заявка на выплату.
        """
        attributes = {
            "owner_id": user_id,
            "gross_amount": gross_amount,
            "fee_amount": fee_amount,
            "net_amount": net_amount,
            "status": PayoutStatus.PENDING,
            "tax_withheld": None,  # MVP Вариант A
        }
        return await super().create(attributes)
