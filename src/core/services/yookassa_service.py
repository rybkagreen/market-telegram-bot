"""
Сервис для работы с ЮKassa SDK.
Синхронный SDK обёрнут в asyncio.to_thread для асинхронной работы.
"""

from __future__ import annotations

import asyncio
import logging
from decimal import Decimal
from uuid import uuid4

from yookassa import Configuration, Payment
from yookassa.domain.exceptions import ApiError

from src.config.settings import settings
from src.db.models.yookassa_payment import YookassaPayment as YooKassaPayment
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
        user_id: int,
    ) -> YooKassaPayment:
        """
        Создать платёж ЮKassa.

        Args:
            amount_rub: Сумма в рублях.
            user_id: ID пользователя.

        Returns:
            YooKassaPayment: Запись о платеже.

        Raises:
            ApiError: Ошибка API ЮKassa.
            Exception: Неожиданная ошибка.
        """
        idempotency_key = str(uuid4())
        description = f"Пополнение баланса RekHarborBot: {amount_rub} ₽"

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
                "metadata": {"user_id": str(user_id), "amount_rub": str(amount_rub)},
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
                    credits=int(amount_rub),  # legacy column, keep 1:1 for now
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
                f"amount={amount_rub} RUB"
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


# Singleton instance
yookassa_service = YooKassaService()
