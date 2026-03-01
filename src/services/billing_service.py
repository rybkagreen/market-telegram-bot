"""
BillingService — бизнес-логика для работы с платежами.
Обёртка над src.core.services.billing_service для удобного использования в handlers.
"""

from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.services.billing_service import BillingService as CoreBillingService
from src.db.repositories.transaction_repo import TransactionRepository
from src.db.repositories.user_repo import UserRepository


class BillingService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._user_repo = UserRepository(session)
        self._transaction_repo = TransactionRepository(session)
        self._core_service = CoreBillingService()

    async def create_payment(self, telegram_id: int, amount: Decimal) -> str:
        """
        Создать платёж YooKassa. Возвращает payment_url.

        Args:
            telegram_id: Telegram ID пользователя.
            amount: Сумма платежа.

        Returns:
            URL для оплаты.
        """
        user = await self._user_repo.get_by_telegram_id(telegram_id)
        if not user:
            raise ValueError(f"User with telegram_id {telegram_id} not found")

        result = await self._core_service.create_payment(
            user_id=user.id,
            amount=amount,
        )
        return result["payment_url"]

    async def check_payment(self, telegram_id: int, payment_id: str) -> dict:
        """
        Проверить статус платежа.

        Args:
            telegram_id: Telegram ID пользователя.
            payment_id: ID платежа.

        Returns:
            {"status": ..., "balance": ...}
        """
        user = await self._user_repo.get_by_telegram_id(telegram_id)
        if not user:
            raise ValueError(f"User with telegram_id {telegram_id} not found")

        return await self._core_service.check_payment(
            payment_id=payment_id,
            user_id=user.id,
        )

    async def get_history(self, telegram_id: int, page: int = 1, per_page: int = 10):
        """
        История транзакций с пагинацией.

        Args:
            telegram_id: Telegram ID пользователя.
            page: Номер страницы.
            per_page: Размер страницы.

        Returns:
            (transactions, total)
        """
        user = await self._user_repo.get_by_telegram_id(telegram_id)
        if not user:
            raise ValueError(f"User with telegram_id {telegram_id} not found")

        return await self._transaction_repo.get_by_user(
            user_id=user.id,
            page=page,
            page_size=per_page,
        )
