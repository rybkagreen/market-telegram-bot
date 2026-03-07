"""
Payout Service — сервис для управления выплатами владельцам каналов.
Спринт 1 — базовая система учёта выплат (80% от цены поста).
Реальная интеграция с CryptoBot добавляется в Спринте 2.
"""

import logging
from datetime import UTC
from decimal import Decimal

from src.db.models.payout import Payout, PayoutCurrency, PayoutStatus
from src.db.session import async_session_factory

logger = logging.getLogger(__name__)


class PayoutService:
    """
    Сервис для управления выплатами.

    Методы:
        calculate_payout: Рассчитать сумму выплаты (80% от цены поста)
        get_owner_balance: Получить баланс владельца к выплате
        create_pending_payout: Создать запись о выплате в статусе pending
        process_payout: Обработать выплату (заглушка для Спринта 2)
    """

    def __init__(self) -> None:
        """Инициализация сервиса."""
        self.payout_percentage = Decimal("0.8")  # 80% владельцу
        self.platform_percentage = Decimal("0.2")  # 20% платформе

    def calculate_payout(self, price_per_post: Decimal) -> tuple[Decimal, Decimal]:
        """
        Рассчитать сумму выплаты и комиссию платформы.

        Args:
            price_per_post: Цена поста в рублях.

        Returns:
            Кортеж (payout_amount, platform_fee).
        """
        payout_amount = price_per_post * self.payout_percentage
        platform_fee = price_per_post * self.platform_percentage
        return payout_amount.quantize(Decimal("0.01")), platform_fee.quantize(Decimal("0.01"))

    async def get_owner_balance(self, owner_user_id: int) -> Decimal:
        """
        Получить баланс владельца к выплате (сумма pending выплат).

        Args:
            owner_user_id: ID владельца в БД.

        Returns:
            Сумма к выплате.
        """
        from sqlalchemy import func, select

        async with async_session_factory() as session:
            stmt = (
                select(func.sum(Payout.amount))
                .where(
                    Payout.owner_id == owner_user_id,
                    Payout.status == PayoutStatus.PENDING,
                )
            )
            result = await session.execute(stmt)
            balance = result.scalar_one() or Decimal("0")
            return balance

    async def get_owner_payouts(
        self,
        owner_user_id: int,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Payout]:
        """
        Получить список выплат владельца.

        Args:
            owner_user_id: ID владельца в БД.
            limit: Максимальное количество записей.
            offset: Смещение.

        Returns:
            Список выплат.
        """
        from sqlalchemy import select

        async with async_session_factory() as session:
            stmt = (
                select(Payout)
                .where(Payout.owner_id == owner_user_id)
                .order_by(Payout.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def create_pending_payout(
        self,
        owner_user_id: int,
        channel_id: int,
        placement_id: int,
        price_per_post: Decimal,
    ) -> Payout:
        """
        Создать запись о выплате в статусе pending.

        Вызывается после факта публикации поста.

        Args:
            owner_user_id: ID владельца в БД.
            channel_id: ID канала.
            placement_id: ID размещения (mailing_log.id).
            price_per_post: Цена поста в рублях.

        Returns:
            Созданная запись Payout.
        """
        payout_amount, platform_fee = self.calculate_payout(price_per_post)

        async with async_session_factory() as session:
            # Проверяем что payout ещё не создан для этого placement
            existing = await session.get(Payout, placement_id)
            if existing:
                logger.warning(f"Payout already exists for placement {placement_id}")
                return existing

            payout = Payout(
                owner_id=owner_user_id,
                channel_id=channel_id,
                placement_id=placement_id,
                amount=payout_amount,
                platform_fee=platform_fee,
                currency=PayoutCurrency.RUB,
                status=PayoutStatus.PENDING,
            )

            session.add(payout)
            await session.flush()
            await session.refresh(payout)

            logger.info(
                f"Created pending payout {payout.id}: "
                f"{payout_amount} ₽ for owner {owner_user_id}"
            )

            return payout

    async def process_payout(self, payout_id: int, wallet_address: str | None = None) -> bool:
        """
        Обработать выплату (перевести в статус processing/paid).

        Args:
            payout_id: ID выплаты.
            wallet_address: Адрес кошелька для выплаты.

        Returns:
            True если успешно.
        """
        async with async_session_factory() as session:
            payout = await session.get(Payout, payout_id)
            if not payout:
                logger.error(f"Payout {payout_id} not found")
                return False

            if payout.status != PayoutStatus.PENDING:
                logger.warning(f"Payout {payout_id} already processed (status={payout.status.value})")
                return False

            # В Спринте 1 просто меняем статус на PROCESSING
            # В Спринте 2 здесь будет интеграция с CryptoBot
            payout.status = PayoutStatus.PROCESSING
            if wallet_address:
                payout.wallet_address = wallet_address

            await session.flush()

            logger.info(f"Payout {payout_id} marked as processing")
            return True

    async def mark_payout_paid(
        self,
        payout_id: int,
        tx_hash: str | None = None,
    ) -> bool:
        """
        Отметить выплату как выплаченную.

        Args:
            payout_id: ID выплаты.
            tx_hash: Хэш транзакции.

        Returns:
            True если успешно.
        """
        from datetime import datetime

        async with async_session_factory() as session:
            payout = await session.get(Payout, payout_id)
            if not payout:
                logger.error(f"Payout {payout_id} not found")
                return False

            if payout.status not in (PayoutStatus.PENDING, PayoutStatus.PROCESSING):
                logger.warning(f"Payout {payout_id} cannot be marked as paid (status={payout.status.value})")
                return False

            payout.status = PayoutStatus.PAID
            payout.paid_at = datetime.now(UTC)
            if tx_hash:
                payout.tx_hash = tx_hash

            await session.flush()

            logger.info(f"Payout {payout_id} marked as paid")
            return True

    async def cancel_payout(self, payout_id: int) -> bool:
        """
        Отменить выплату.

        Args:
            payout_id: ID выплаты.

        Returns:
            True если успешно.
        """
        async with async_session_factory() as session:
            payout = await session.get(Payout, payout_id)
            if not payout:
                logger.error(f"Payout {payout_id} not found")
                return False

            if payout.status == PayoutStatus.PAID:
                logger.warning(f"Payout {payout_id} already paid, cannot cancel")
                return False

            payout.status = PayoutStatus.CANCELLED
            await session.flush()

            logger.info(f"Payout {payout_id} cancelled")
            return True


# Глобальный экземпляр
payout_service = PayoutService()
