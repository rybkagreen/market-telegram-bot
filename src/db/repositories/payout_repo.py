"""
PayoutRepository for PayoutRequest model operations.
"""


from sqlalchemy import select

from src.db.models.payout import PayoutRequest, PayoutStatus
from src.db.repositories.base import BaseRepository


class PayoutRepository(BaseRepository[PayoutRequest]):
    """
    Репозиторий для работы с заявками на выплату.
    """

    model = PayoutRequest

    async def get_by_owner(
        self,
        owner_id: int,
    ) -> list[PayoutRequest]:
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

    async def get_active_for_owner(
        self,
        owner_id: int,
    ) -> PayoutRequest | None:
        """
        Получить активную заявку владельца (pending/processing).

        Возвращает одну заявку или None.
        """
        result = await self.session.execute(
            select(PayoutRequest)
            .where(
                PayoutRequest.owner_id == owner_id,
                PayoutRequest.status.in_(
                    [PayoutStatus.pending, PayoutStatus.processing]
                ),
            )
            .limit(1)
        )
        return result.scalar_one_or_none()
