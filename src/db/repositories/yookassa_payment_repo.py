"""YookassaPaymentRepository for YookassaPayment model operations."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from src.db.models.yookassa_payment import YookassaPayment
from src.db.repositories.base import BaseRepository


class YookassaPaymentRepository(BaseRepository[YookassaPayment]):
    """Репозиторий для работы с платежами ЮKassa."""

    model = YookassaPayment

    async def get_by_payment_id(self, payment_id: str) -> YookassaPayment | None:
        """Получить платёж по ID от ЮKassa."""
        result = await self.session.execute(
            select(YookassaPayment).where(YookassaPayment.yookassa_payment_id == payment_id)
        )
        return result.scalar_one_or_none()

    async def get_by_user(self, user_id: int, limit: int = 50) -> list[YookassaPayment]:
        """Получить платежи пользователя."""
        result = await self.session.execute(
            select(YookassaPayment)
            .where(YookassaPayment.user_id == user_id)
            .order_by(YookassaPayment.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_pending_payments(self) -> list[YookassaPayment]:
        """Получить ожидающие платежи."""
        result = await self.session.execute(
            select(YookassaPayment)
            .where(YookassaPayment.status == "pending")
            .order_by(YookassaPayment.created_at)
        )
        return list(result.scalars().all())

    async def sum_by_user_window(self, user_id: int, days: int = 30) -> float:
        """Посчитать сумму платежей пользователя за окно дней."""
        cutoff = datetime.now(UTC) - timedelta(days=days)
        result = await self.session.execute(
            select(func.coalesce(func.sum(YookassaPayment.amount), 0)).where(
                YookassaPayment.user_id == user_id,
                YookassaPayment.status == "succeeded",
                YookassaPayment.created_at > cutoff,
            )
        )
        return float(result.scalar_one() or 0)
