"""
Payout Service — сервис для управления выплатами владельцам каналов.
Спринт 1 — базовая система учёта выплат (80% от цены поста).
Реальная интеграция с CryptoBot добавляется в Спринте 1 (Task 1).
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal

from src.config.settings import settings
from src.core.services.cryptobot_service import (
    InsufficientFundsError,
    PayoutAPIError,
    UserNotFoundError,
    cryptobot_service,
)
from src.db.models.payout import Payout, PayoutCurrency, PayoutStatus
from src.db.models.user import User
from src.db.session import async_session_factory

logger = logging.getLogger(__name__)


# Compatibility for Python 3.10 and 3.11+
try:
    from datetime import UTC  # Python 3.11+
except ImportError:
    UTC = timezone.utc  # type: ignore[misc, assignment]  # noqa: UP017


class PayoutService:
    """
    Сервис для управления выплатами.

    Методы:
        calculate_payout: Рассчитать сумму выплаты (80% от цены поста)
        get_owner_balance: Получить баланс владельца к выплате
        create_pending_payout: Создать запись о выплате в статусе pending
        process_payout: Обработать выплату через CryptoBot API
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
            stmt = select(func.sum(Payout.amount)).where(
                Payout.owner_id == owner_user_id,
                Payout.status == PayoutStatus.PENDING,
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
                f"Created pending payout {payout.id}: {payout_amount} ₽ for owner {owner_user_id}"
            )

            return payout

    async def process_payout(self, payout_id: int) -> dict:
        """
        Обработать выплату через CryptoBot API.

        Шаги:
        1. Получить Payout из БД по payout_id
        2. Проверить статус: только PENDING → обрабатывать
        3. Проверить минимальную сумму
        4. Получить telegram_id владельца из User
        5. Вызвать cryptobot_service.send_transfer()
        6. При успехе: статус → COMPLETED, записать transfer_id
        7. При ошибке: статус → FAILED, записать error_message
        8. Вернуть {"success": bool, "transfer_id": str | None, "error": str | None}

        Args:
            payout_id: ID выплаты.

        Returns:
            dict с результатом выплаты.
        """
        async with async_session_factory() as session:
            # Шаг 1: Получить выплату
            payout = await session.get(Payout, payout_id)
            if not payout:
                logger.error(f"Payout {payout_id} not found")
                return {"success": False, "transfer_id": None, "error": "Payout not found"}

            # Шаг 2: Проверить статус
            if payout.status != PayoutStatus.PENDING:
                logger.warning(
                    f"Payout {payout_id} already processed (status={payout.status.value})"
                )
                return {
                    "success": False,
                    "transfer_id": None,
                    "error": f"Already processed: {payout.status.value}",
                }

            # Шаг 3: Проверить минимальную сумму (конвертируем в USDT для проверки)
            min_payout_usdt = settings.min_payout_usdt
            if payout.currency == PayoutCurrency.USDT:
                payout_amount = float(payout.amount)
            elif payout.currency == PayoutCurrency.RUB:
                # Конвертируем рубли в USDT по курсу
                usdt_rate = settings.currency_rates.get("USDT", 90)
                payout_amount = float(payout.amount) / usdt_rate
            else:
                # Для других валют — прямая конвертация
                rate = settings.currency_rates.get(payout.currency.value, 1)
                payout_amount = float(payout.amount) / rate if rate > 0 else 0

            if payout_amount < min_payout_usdt:
                logger.warning(
                    f"Payout {payout_id} amount {payout_amount} USDT < minimum {min_payout_usdt}"
                )
                return {
                    "success": False,
                    "transfer_id": None,
                    "error": f"Amount below minimum ({min_payout_usdt} USDT)",
                }

            # Шаг 4: Получить telegram_id владельца
            user = await session.get(User, payout.owner_id)
            if not user:
                logger.error(f"User {payout.owner_id} not found for payout {payout_id}")
                return {
                    "success": False,
                    "transfer_id": None,
                    "error": "User not found",
                }

            if not user.telegram_id:
                logger.error(f"User {payout.owner_id} has no telegram_id")
                return {
                    "success": False,
                    "transfer_id": None,
                    "error": "User has no telegram_id",
                }

            # Шаг 5: Вызвать CryptoBot API
            try:
                # Определяем валюту для перевода
                transfer_currency = payout.currency.value
                if payout.currency == PayoutCurrency.RUB:
                    # Рубли конвертируем в USDT для выплаты
                    transfer_currency = "USDT"
                    usdt_rate = settings.currency_rates.get("USDT", 90)
                    transfer_amount = float(payout.amount) / usdt_rate
                else:
                    transfer_amount = float(payout.amount)

                # Формируем комментарий
                channel_username = ""
                if payout.channel:
                    channel_username = (
                        f"@{payout.channel.username}" if payout.channel.username else ""
                    )

                comment = (
                    f"Выплата за размещения{' ' + channel_username if channel_username else ''}"
                )

                # Выполняем перевод
                transfer_result = await cryptobot_service.send_transfer(
                    telegram_id=user.telegram_id,
                    amount=transfer_amount,
                    currency=transfer_currency,
                    comment=comment,
                    disable_notification=False,
                )

                # Шаг 6: Успех — обновляем статус
                payout.status = PayoutStatus.PAID
                payout.tx_hash = transfer_result.get("transfer_id")
                payout.paid_at = payout.created_at  # Используем created_at как paid_at

                await session.flush()

                logger.info(
                    f"Payout {payout_id} completed: {transfer_amount} {transfer_currency} "
                    f"to user {user.telegram_id} | transfer_id={transfer_result.get('transfer_id')}"
                )

                return {
                    "success": True,
                    "transfer_id": transfer_result.get("transfer_id"),
                    "error": None,
                }

            # Шаг 7: Обработка ошибок
            except InsufficientFundsError as e:
                payout.status = PayoutStatus.FAILED
                error_msg = f"Insufficient funds: {str(e)}"
                logger.error(f"Payout {payout_id} failed: {error_msg}")

            except UserNotFoundError as e:
                payout.status = PayoutStatus.FAILED
                error_msg = f"User not found in CryptoBot: {str(e)}"
                logger.error(f"Payout {payout_id} failed: {error_msg}")

            except PayoutAPIError as e:
                payout.status = PayoutStatus.FAILED
                error_msg = f"API error: {str(e)}"
                logger.error(f"Payout {payout_id} failed: {error_msg}")

            except Exception as e:
                payout.status = PayoutStatus.FAILED
                error_msg = f"Unexpected error: {str(e)}"
                logger.exception(f"Payout {payout_id} failed with unexpected error")

            # Записываем ошибку и сохраняем
            payout.wallet_address = error_msg  # Используем wallet_address для хранения ошибки
            await session.flush()

            return {
                "success": False,
                "transfer_id": None,
                "error": error_msg,
            }

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
        async with async_session_factory() as session:
            payout = await session.get(Payout, payout_id)
            if not payout:
                logger.error(f"Payout {payout_id} not found")
                return False

            if payout.status not in (PayoutStatus.PENDING, PayoutStatus.PROCESSING):
                logger.warning(
                    f"Payout {payout_id} cannot be marked as paid (status={payout.status.value})"
                )
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
