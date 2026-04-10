"""YookassaPaymentRepository for YooKassa payment operations."""

from typing import Any

from sqlalchemy import select

from src.db.models.yookassa_payment import YookassaPayment
from src.db.repositories.base import BaseRepository


class YookassaPaymentRepository(BaseRepository[YookassaPayment]):
    """Репозиторий для работы с платежами YooKassa."""

    model = YookassaPayment

    async def get_by_payment_id(self, payment_id: str) -> YookassaPayment | None:
        """
        Получить платёж по external payment_id.

        Args:
            payment_id: Внешний ID платежа (от YooKassa).

        Returns:
            Запись платежа или None.
        """
        result = await self.session.execute(
            select(YookassaPayment).where(YookassaPayment.payment_id == payment_id)
        )
        return result.scalar_one_or_none()

    async def create(self, data: dict[str, Any]) -> YookassaPayment:
        """Создать запись платежа."""
        instance = YookassaPayment(**data)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance
