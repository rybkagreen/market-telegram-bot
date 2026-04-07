"""PayoutRepository for PayoutRequest model operations."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select

from src.db.models.payout import PayoutRequest, PayoutStatus
from src.db.repositories.base import BaseRepository


class PayoutRepository(BaseRepository[PayoutRequest]):
    """Репозиторий для работы с заявками на выплату."""

    model = PayoutRequest

    async def get_by_owner(self, owner_id: int) -> list[PayoutRequest]:
        """Получить заявки владельца."""
        result = await self.session.execute(
            select(PayoutRequest)
            .where(PayoutRequest.owner_id == owner_id)
            .order_by(PayoutRequest.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_pending(self) -> list[PayoutRequest]:
        """Получить все ожидающие выплаты."""
        result = await self.session.execute(
            select(PayoutRequest)
            .where(PayoutRequest.status == PayoutStatus.pending)
            .order_by(PayoutRequest.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_active_for_owner(self, owner_id: int) -> PayoutRequest | None:
        """Получить активную заявку владельца (pending/processing)."""
        result = await self.session.execute(
            select(PayoutRequest)
            .where(
                PayoutRequest.owner_id == owner_id,
                PayoutRequest.status.in_([PayoutStatus.pending, PayoutStatus.processing]),
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def sum_completed_payouts_window(self, owner_id: int, days: int = 30) -> Decimal:
        """Посчитать сумму завершённых выплат за окно дней."""
        cutoff = datetime.now(UTC) - timedelta(days=days)
        result = await self.session.execute(
            select(func.coalesce(func.sum(PayoutRequest.net_amount), Decimal("0")))
            .where(PayoutRequest.owner_id == owner_id)
            .where(PayoutRequest.status == PayoutStatus.paid)
            .where(PayoutRequest.created_at > cutoff)
        )
        return result.scalar() or Decimal("0")

    async def get_pending_sum(self) -> Decimal:
        """Получить сумму gross_amount по ожидающим выплатам."""
        result = await self.session.execute(
            select(func.coalesce(func.sum(PayoutRequest.gross_amount), Decimal("0"))).where(
                PayoutRequest.status.in_([PayoutStatus.pending, PayoutStatus.processing])
            )
        )
        return result.scalar_one() or Decimal("0")
