"""
Billing Service для управления платежами и балансом.
"""

import logging
import uuid
from decimal import Decimal
from typing import Any

from src.core.services.notification_service import notification_service
from src.db.models.transaction import Transaction, TransactionType
from src.db.repositories.transaction_repo import TransactionRepository
from src.db.repositories.user_repo import UserRepository
from src.db.session import async_session_factory

logger = logging.getLogger(__name__)


class BillingService:
    """
    Сервис для управления платежами и балансом.

    Методы:
        create_payment: Создать платёж
        check_payment: Проверить статус платежа
        deduct_balance: Списать средства
        apply_referral_bonus: Начислить реферальный бонус
    """

    def __init__(self) -> None:
        """Инициализация сервиса."""
        pass

    async def create_payment(
        self,
        user_id: int,
        amount: Decimal,
        payment_method: str = "yookassa",
    ) -> dict[str, Any]:
        """
        Создать платёж.

        Args:
            user_id: ID пользователя.
            amount: Сумма платежа.
            payment_method: Метод оплаты.

        Returns:
            Данные платежа (payment_id, payment_url).
        """
        async with async_session_factory() as session:
            user_repo = UserRepository(session)
            user = await user_repo.get_by_id(user_id)

            if not user:
                raise ValueError(f"User {user_id} not found")

            # Генерируем payment_id
            payment_id = str(uuid.uuid4())

            # Создаём транзакцию со статусом pending
            transaction_repo = TransactionRepository(session)
            await transaction_repo.create_transaction(
                user_id=user_id,
                amount=amount,
                transaction_type=TransactionType.TOPUP,
                payment_id=payment_id,
                meta_json={"status": "pending", "method": payment_method},
            )

            # В production здесь создаём платёж в YooKassa
            # Для now возвращаем заглушку
            payment_url = f"https://yookassa.ru/payment/{payment_id}"

            logger.info(f"Payment {payment_id} created for user {user_id}, amount: {amount}")

            return {
                "payment_id": payment_id,
                "payment_url": payment_url,
                "amount": str(amount),
                "status": "pending",
            }

    async def check_payment(
        self,
        payment_id: str,
        user_id: int,
    ) -> dict[str, Any]:
        """
        Проверить статус платежа.

        Args:
            payment_id: ID платежа.
            user_id: ID пользователя.

        Returns:
            Статус платежа.
        """
        async with async_session_factory() as session:
            transaction_repo = TransactionRepository(session)

            # Ищем транзакцию по payment_id
            transaction = await transaction_repo.find_one(
                Transaction.payment_id == payment_id,
                Transaction.user_id == user_id,
            )

            if not transaction:
                raise ValueError(f"Payment {payment_id} not found")

            # Получаем статус из meta_json
            meta = transaction.meta_json or {}
            status = meta.get("status", "pending")

            # В production здесь проверяем статус в YooKassa
            # Если paid, то зачисляем на баланс
            credited = meta.get("credited") if meta else None
            if status == "succeeded" and credited is not True:
                # Зачисляем на баланс
                user_repo = UserRepository(session)
                await user_repo.update_balance(user_id, transaction.amount)

                # Обновляем транзакцию
                meta["credited"] = True
                await transaction_repo.update(transaction.id, {"meta_json": meta})

                logger.info(f"Payment {payment_id} credited to user {user_id}")

                # Уведомляем пользователя
                await notification_service.notify_low_balance(
                    user_id=user_id,
                    balance=transaction.amount,
                )

            return {
                "payment_id": payment_id,
                "status": status,
                "amount": str(transaction.amount),
                "credited": meta.get("credited", False),
            }

    async def deduct_balance(
        self,
        user_id: int,
        amount: Decimal,
        description: str = "",
    ) -> bool:
        """
        Списать средства с баланса.

        Args:
            user_id: ID пользователя.
            amount: Сумма для списания.
            description: Описание списания.

        Returns:
            True если списание успешно.
        """
        async with async_session_factory() as session:
            user_repo = UserRepository(session)

            # Проверяем баланс
            user = await user_repo.get_by_id(user_id)
            if not user:
                return False

            if user.balance < amount:
                logger.warning(f"User {user_id} has insufficient balance: {user.balance}")
                return False

            # Списываем баланс (атомарно)
            await user_repo.update_balance(user_id, Decimal(-amount))

            # Создаём транзакцию
            transaction_repo = TransactionRepository(session)
            await transaction_repo.create_transaction(
                user_id=user_id,
                amount=amount,
                transaction_type=TransactionType.SPEND,
                meta_json={"description": description},
            )

            logger.info(f"Spend {amount} RUB from user {user_id}: {description}")

            return True

    async def apply_referral_bonus(
        self,
        referrer_id: int,
        referred_user_id: int,
        bonus_amount: Decimal,
    ) -> bool:
        """
        Начислить реферальный бонус.

        Args:
            referrer_id: ID пригласившего.
            referred_user_id: ID приглашённого.
            bonus_amount: Сумма бонуса.

        Returns:
            True если бонус начислен.
        """
        async with async_session_factory() as session:
            user_repo = UserRepository(session)

            # Проверяем реферера
            referrer = await user_repo.get_by_id(referrer_id)
            if not referrer:
                return False

            # Начисляем бонус
            await user_repo.update_balance(referrer_id, bonus_amount)

            # Создаём транзакцию
            transaction_repo = TransactionRepository(session)
            await transaction_repo.create_transaction(
                user_id=referrer_id,
                amount=bonus_amount,
                transaction_type=TransactionType.TOPUP,
                payment_id=None,
                meta_json={
                    "type": "referral_bonus",
                    "referred_user_id": referred_user_id,
                },
            )

            logger.info(f"Referral bonus {bonus_amount} RUB to user {referrer_id}")

            # Уведомляем
            await notification_service.notify_referral_bonus(
                user_id=referrer_id,
                bonus_amount=bonus_amount,
                referred_user_id=referred_user_id,
            )

            return True


# Глобальный экземпляр
billing_service = BillingService()
