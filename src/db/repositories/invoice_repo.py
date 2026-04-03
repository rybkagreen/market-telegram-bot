"""InvoiceRepository for Invoice model operations."""

from sqlalchemy import select

from src.db.models.invoice import Invoice
from src.db.repositories.base import BaseRepository


class InvoiceRepository(BaseRepository[Invoice]):
    """Репозиторий для работы со счетами на оплату."""

    model = Invoice

    async def get_by_number(self, invoice_number: str) -> Invoice | None:
        """Получить счёт по номеру."""
        result = await self.session.execute(
            select(Invoice).where(Invoice.invoice_number == invoice_number)
        )
        return result.scalar_one_or_none()

    async def get_by_user(self, user_id: int, limit: int = 50) -> list[Invoice]:
        """Получить счета пользователя."""
        result = await self.session.execute(
            select(Invoice)
            .where(Invoice.user_id == user_id)
            .order_by(Invoice.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update_status(self, invoice_id: int, status: str) -> Invoice | None:
        """Обновить статус счёта."""
        invoice = await self.session.get(Invoice, invoice_id)
        if invoice:
            invoice.status = status
            await self.session.flush()
            await self.session.refresh(invoice)
        return invoice
