"""
Сервис для работы с ЮKassa SDK.
Синхронный SDK обёрнут в asyncio.to_thread для асинхронной работы.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from yookassa import Configuration, Payment
from yookassa.domain.exceptions import ApiError

from src.config.settings import settings
from src.db.models.user import User
from src.db.models.yookassa_payment import YooKassaPayment
from src.db.session import async_session_factory

logger = logging.getLogger(__name__)


class YooKassaService:
    """Сервис для работы с платёжной системой ЮKassa."""

    def __init__(self) -> None:
        """Инициализировать сервис."""
        self.logger = logging.getLogger(__name__)
        if settings.yookassa_shop_id and settings.yookassa_secret_key:
            Configuration.account_id = settings.yookassa_shop_id
            Configuration.secret_key = settings.yookassa_secret_key
        else:
            self.logger.warning(
                "ЮKassa не настроена: YOOKASSA_SHOP_ID или YOOKASSA_SECRET_KEY пусты"
            )

    async def create_payment(
        self,
        amount_rub: Decimal,
        credits: int,
        user_id: int,
    ) -> YooKassaPayment:
        """
        Создать платёж ЮKassa.

        Args:
            amount_rub: Сумма в рублях.
            credits: Количество кредитов для зачисления.
            user_id: ID пользователя.

        Returns:
            YooKassaPayment: Запись о платеже.

        Raises:
            ApiError: Ошибка API ЮKassa.
            Exception: Неожиданная ошибка.
        """
        idempotency_key = str(uuid4())
        description = f"Пополнение баланса RekHarborBot: {credits} кредитов"

        try:
            # Вызов синхронного SDK через asyncio.to_thread
            payment_data = {
                "amount": {"value": str(amount_rub), "currency": "RUB"},
                "confirmation": {
                    "type": "redirect",
                    "return_url": settings.yookassa_return_url,
                },
                "capture": True,
                "description": description,
                "metadata": {"user_id": str(user_id), "credits": str(credits)},
            }

            payment = await asyncio.to_thread(
                Payment.create,
                payment_data,
                idempotency_key,
            )

            # Сохранить в БД
            async with async_session_factory() as session:
                record = YooKassaPayment(
                    payment_id=payment.id,
                    user_id=user_id,
                    amount_rub=amount_rub,
                    credits=credits,
                    status="pending",
                    description=description,
                    confirmation_url=payment.confirmation.confirmation_url,
                    idempotency_key=idempotency_key,
                )
                session.add(record)
                await session.commit()
                await session.refresh(record)

            self.logger.info(
                f"ЮKassa платёж создан: payment_id={payment.id}, user_id={user_id}, "
                f"amount={amount_rub} RUB, credits={credits}"
            )
            return record

        except ApiError as e:
            self.logger.error("ЮKassa API error user_id=%s: %s", user_id, e)
            raise
        except Exception as e:
            self.logger.error("ЮKassa unexpected error user_id=%s: %s", user_id, e)
            raise

    async def get_payment_status(self, payment_id: str) -> str:
        """
        Получить статус платежа.

        Args:
            payment_id: UUID платежа от ЮKassa.

        Returns:
            str: Статус платежа (pending/succeeded/canceled/failed).
        """
        payment = await asyncio.to_thread(Payment.find_one, payment_id)
        return payment.status  # pending / waiting_for_capture / succeeded / canceled

    async def handle_webhook(self, event: dict) -> None:
        """
        Обработать webhook от ЮKassa.

        Args:
            event: Событие от ЮKassa.
        """
        event_type = event.get("event", "")
        obj = event.get("object", {})
        payment_id = obj.get("id", "")

        if not payment_id:
            self.logger.warning("Webhook: payment_id не найден в событии")
            return

        async with async_session_factory() as session:
            from sqlalchemy import select

            result = await session.execute(
                select(YooKassaPayment).where(YooKassaPayment.payment_id == payment_id)
            )
            record = result.scalar_one_or_none()

            if record is None:
                self.logger.warning("Webhook: payment_id=%s не найден в БД", payment_id)
                return

            if record.status != "pending":
                self.logger.info(
                    "Webhook: payment_id=%s уже обработан (статус=%s)",
                    payment_id,
                    record.status,
                )
                return

            if event_type == "payment.succeeded":
                record.status = "succeeded"
                record.paid_at = datetime.now(UTC)
                await session.commit()
                await self._credit_user(record.user_id, record.credits, record.amount_rub, payment_id)

            elif event_type == "payment.canceled":
                record.status = "canceled"
                await session.commit()
                self.logger.info("Webhook: payment_id=%s отменён", payment_id)

    async def _credit_user(
        self,
        user_id: int,
        credits: int,
        amount_rub: Decimal,
        payment_id: str,
    ) -> None:
        """
        Начислить кредиты пользователю и отправить уведомление.

        Args:
            user_id: ID пользователя.
            credits: Количество кредитов.
            amount_rub: Сумма в рублях.
            payment_id: UUID платежа.
        """
        try:

            from sqlalchemy import select

            # Начислить кредиты напрямую через БД
            async with async_session_factory() as session:
                result = await session.execute(
                    select(User).where(User.id == user_id)
                )
                user = result.scalar_one_or_none()

                if not user:
                    self.logger.error("User %s not found for credit update", user_id)
                    return

                # Начисление средств
                balance_before = Decimal(str(user.credits))
                user.credits += credits
                balance_after = Decimal(str(user.credits))

                # Создать транзакцию
                from src.db.models.transaction import Transaction, TransactionType

                transaction = Transaction(
                    user_id=user_id,
                    amount=Decimal(str(credits)),
                    type=TransactionType.TOPUP,
                    description=f"Пополнение ЮKassa #{payment_id[:8]}",
                    reference_id=None,
                    reference_type="yookassa_payment",
                    balance_before=balance_before,
                    balance_after=balance_after,
                )
                session.add(transaction)
                await session.commit()

                new_balance = int(user.credits)

            # Отправить уведомление
            from aiogram import Bot

            from src.bot.handlers.shared.notifications import (
                format_yookassa_payment_success,
            )

            # Создать бота для отправки уведомления
            bot = Bot(token=settings.bot_token)

            if user:
                try:
                    text = format_yookassa_payment_success(
                        amount_rub=amount_rub,
                        credits=credits,
                        new_balance=new_balance,
                    )
                    await bot.send_message(chat_id=user.telegram_id, text=text, parse_mode="HTML")
                    self.logger.info("Уведомление об оплате отправлено user_id=%s", user_id)
                finally:
                    await bot.session.close()

        except Exception as e:
            self.logger.error("Ошибка отправки уведомления user_id=%s: %s", user_id, e)


# Singleton instance
yookassa_service = YooKassaService()
