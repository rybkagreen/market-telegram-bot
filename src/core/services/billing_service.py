"""
Billing Service для управления платежами и балансом.
Работает с кредитами (1 кредит = 1 рублю).
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
        deduct_credits: Списать кредиты
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
            amount: Сумма платежа в рублях (конвертируется в кредиты 1:1).
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

            # Конвертируем рубли в кредиты (1:1)
            credits_amount = int(amount)

            # Создаём транзакцию со статусом pending
            transaction_repo = TransactionRepository(session)
            await transaction_repo.create_transaction(
                user_id=user_id,
                amount=amount,
                transaction_type=TransactionType.TOPUP,
                payment_id=payment_id,
                meta_json={
                    "status": "pending",
                    "method": payment_method,
                    "credits": credits_amount,
                },
            )

            # В production здесь создаём платёж в YooKassa
            # Для now возвращаем заглушку
            payment_url = f"https://yookassa.ru/payment/{payment_id}"

            logger.info(
                f"Payment {payment_id} created for user {user_id}, amount: {amount} RUB = {credits_amount} credits"
            )

            return {
                "payment_id": payment_id,
                "payment_url": payment_url,
                "amount": str(amount),
                "credits": credits_amount,
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
            # Если paid, то зачисляем кредиты на баланс
            credited = meta.get("credited") if meta else None
            if status == "succeeded" and credited is not True:
                # Зачисляем кредиты на баланс (1 рубль = 1 кредит)
                user_repo = UserRepository(session)
                credits_amount = int(transaction.amount)
                await user_repo.update_credits(user_id, credits_amount)

                # Обновляем транзакцию
                meta["credited"] = True
                meta["credits_credited"] = credits_amount
                await transaction_repo.update(transaction.id, {"meta_json": meta})

                logger.info(
                    f"Payment {payment_id} credited: {credits_amount} credits to user {user_id}"
                )

                # Уведомляем пользователя
                await notification_service.notify_low_balance(
                    user_id=user_id,
                    balance=Decimal(credits_amount),
                )

            return {
                "payment_id": payment_id,
                "status": status,
                "amount": str(transaction.amount),
                "credited": meta.get("credited", False),
            }

    async def deduct_credits(
        self,
        user_id: int,
        credits: int,
        description: str = "",
    ) -> bool:
        """
        Списать кредиты с баланса.

        Args:
            user_id: ID пользователя.
            credits: Количество кредитов для списания.
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

            if user.credits < credits:
                logger.warning(
                    f"User {user_id} has insufficient credits: {user.credits} < {credits}"
                )
                return False

            # Списываем кредиты
            await user_repo.update_credits(user_id, -credits)

            # Создаём транзакцию (для истории, в рублях)
            transaction_repo = TransactionRepository(session)
            await transaction_repo.create_transaction(
                user_id=user_id,
                amount=Decimal(credits),  # 1 кредит = 1 рублю
                transaction_type=TransactionType.SPEND,
                meta_json={"description": description, "credits_spent": credits},
            )

            logger.info(f"Spend {credits} credits from user {user_id}: {description}")

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
            bonus_amount: Сумма бонуса в рублях (конвертируется в кредиты 1:1).

        Returns:
            True если бонус начислен.
        """
        async with async_session_factory() as session:
            user_repo = UserRepository(session)

            # Проверяем реферера
            referrer = await user_repo.get_by_id(referrer_id)
            if not referrer:
                return False

            # Начисляем бонус в кредитах (1 рубль = 1 кредит)
            bonus_credits = int(bonus_amount)
            await user_repo.update_credits(referrer_id, bonus_credits)

            # Создаём транзакцию
            transaction_repo = TransactionRepository(session)
            await transaction_repo.create_transaction(
                user_id=referrer_id,
                amount=bonus_amount,
                transaction_type=TransactionType.BONUS,
                payment_id=None,
                meta_json={
                    "type": "referral_bonus",
                    "referred_user_id": referred_user_id,
                    "bonus_credits": bonus_credits,
                },
            )

            logger.info(f"Referral bonus {bonus_credits} credits to user {referrer_id}")

            # Уведомляем
            await notification_service.notify_referral_bonus(
                user_id=referrer_id,
                bonus_amount=bonus_amount,
                referred_user_id=referred_user_id,
            )

            return True


# ─────────────────────────────────────────────
# Эскроу-механика (Спринт 1)
# ─────────────────────────────────────────────

    async def freeze_funds(
        self,
        user_id: int,
        campaign_id: int,
        amount: Decimal,
    ) -> bool:
        """
        Заморозить средства пользователя для кампании.

        Средства блокируются на балансе до публикации или отмены кампании.

        Args:
            user_id: ID пользователя.
            campaign_id: ID кампании.
            amount: Сумма для заморозки.

        Returns:
            True если успешно.
        """

        async with async_session_factory() as session:
            from src.db.models.user import User

            user = await session.get(User, user_id)
            if not user:
                logger.error(f"User {user_id} not found")
                return False

            # Проверяем баланс (с учётом замороженных средств)
            frozen_amount = await self._get_frozen_amount(user_id)
            available_balance = Decimal(user.credits) - frozen_amount

            if available_balance < amount:
                logger.warning(
                    f"Insufficient funds: available={available_balance}, required={amount}"
                )
                return False

            # Создаём транзакцию заморозки
            transaction_repo = TransactionRepository(session)
            await transaction_repo.create_transaction(
                user_id=user_id,
                amount=amount,
                transaction_type=TransactionType.SPEND,
                payment_id=f"frozen_campaign_{campaign_id}",
                meta_json={
                    "type": "frozen",
                    "campaign_id": campaign_id,
                    "status": "frozen",
                },
            )

            logger.info(f"Frozen {amount} credits for campaign {campaign_id}, user {user_id}")
            return True

    async def release_funds_for_placement(
        self,
        user_id: int,
        campaign_id: int,
        placement_id: int,
        amount: Decimal,
    ) -> bool:
        """
        Разморозить средства для конкретного размещения.

        Вызывается после факта публикации поста.

        Args:
            user_id: ID пользователя.
            campaign_id: ID кампании.
            placement_id: ID размещения.
            amount: Сумма для списания.

        Returns:
            True если успешно.
        """
        async with async_session_factory() as session:
            # Создаём транзакцию списания
            transaction_repo = TransactionRepository(session)
            await transaction_repo.create_transaction(
                user_id=user_id,
                amount=amount,
                transaction_type=TransactionType.SPEND,
                payment_id=f"placement_{placement_id}",
                meta_json={
                    "type": "placement",
                    "campaign_id": campaign_id,
                    "placement_id": placement_id,
                    "status": "completed",
                },
            )

            logger.info(
                f"Released {amount} credits for placement {placement_id}, "
                f"campaign {campaign_id}, user {user_id}"
            )
            return True

    async def refund_frozen_funds(
        self,
        user_id: int,
        campaign_id: int,
        amount: Decimal,
    ) -> bool:
        """
        Вернуть замороженные средства пользователю.

        Вызывается при отмене кампании или отклонении размещения.

        Args:
            user_id: ID пользователя.
            campaign_id: ID кампании.
            amount: Сумма для возврата.

        Returns:
            True если успешно.
        """
        async with async_session_factory() as session:
            # Создаём транзакцию возврата
            transaction_repo = TransactionRepository(session)
            await transaction_repo.create_transaction(
                user_id=user_id,
                amount=amount,
                transaction_type=TransactionType.TOPUP,
                payment_id=f"refund_campaign_{campaign_id}",
                meta_json={
                    "type": "refund",
                    "campaign_id": campaign_id,
                    "status": "refunded",
                },
            )

            logger.info(
                f"Refunded {amount} credits for campaign {campaign_id}, user {user_id}"
            )
            return True

    async def _get_frozen_amount(self, user_id: int) -> Decimal:
        """
        Получить сумму замороженных средств пользователя.

        Args:
            user_id: ID пользователя.

        Returns:
            Сумма замороженных средств.
        """
        from sqlalchemy import func, select

        async with async_session_factory() as session:
            stmt = (
                select(func.sum(Transaction.amount))
                .where(
                    Transaction.user_id == user_id,
                    Transaction.type == TransactionType.SPEND,
                )
            )
            result = await session.execute(stmt)
            frozen = result.scalar_one() or Decimal("0")
            return frozen


# Глобальный экземпляр
billing_service = BillingService()
