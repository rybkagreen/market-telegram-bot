"""
Сервис для работы с ЮKassa SDK.
Синхронный SDK обёрнут в asyncio.to_thread для асинхронной работы.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass
from decimal import Decimal
from ipaddress import ip_address, ip_network
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from yookassa import Configuration, Payment
from yookassa.domain.exceptions import (
    ApiError,
    BadRequestError,
    ForbiddenError,
    NotFoundError,
    ResponseProcessingError,
    TooManyRequestsError,
    UnauthorizedError,
)

from src.config.settings import settings
from src.core.services.billing_service import PaymentProviderError
from src.db.models.transaction import TransactionType
from src.db.models.yookassa_payment import YookassaPayment as YooKassaPayment
from src.db.repositories.transaction_repo import TransactionRepository
from src.db.repositories.user_repo import UserRepository

logger = logging.getLogger(__name__)


YOOKASSA_IP_NETWORKS: tuple[str, ...] = (
    "185.71.76.0/27",
    "185.71.77.0/27",
    "77.75.153.0/25",
    "77.75.156.11/32",
    "77.75.156.35/32",
    "77.75.154.128/25",
    "2a02:5180::/32",
)


@dataclass(frozen=True)
class WebhookEvent:
    """Parsed YooKassa webhook event.

    Service-level DTO. Не attached к ORM, не coupled к БД.
    Caller (router) использует поля для бизнес-диспатча.
    """

    event_type: str
    payment_id: str
    payload: dict[str, Any]


class WebhookAuthError(Exception):
    """Raised when webhook source authentication fails.

    For YooKassa: IP whitelist check failed (request from unauthorized IP,
    or client_ip header missing/malformed).
    See https://yookassa.ru/developers/api/notifications#ip-address.

    Future-proof: same exception fits HMAC-based providers if added later.
    """


class InvalidPayloadError(Exception):
    """Webhook body не парсится или структурно невалиден."""


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

    async def create_topup_payment(
        self,
        session: AsyncSession,
        *,
        user_id: int,
        desired_balance: Decimal,
    ) -> dict[str, Any]:
        """Создать платёж пополнения в ЮKassa с caller-controlled session.

        S-48 contract: caller владеет транзакцией, метод не делает commit.

        Workflow:
        1. Pre-flight: проверить существование пользователя (через session).
        2. Посчитать fee + gross.
        3. Сформировать payload для ЮKassa.
        4. Вызвать SDK Payment.create — ВНЕ DB-транзакции (charge integrity).
        5. Persist YookassaPayment + pending Transaction (caller commits).

        Args:
            session: Caller-controlled async session.
            user_id: ID пользователя в локальной БД.
            desired_balance: Чистая сумма к зачислению (без комиссии), руб.

        Returns:
            dict с полями payment_id, payment_url, amount (gross),
            credits (= int(desired_balance)), status="pending".

        Raises:
            ValueError: пользователь не найден или некорректная сумма.
            PaymentProviderError: любая SDK-ошибка ЮKassa
                (forbidden / api_error / network / timeout / etc.).
            RuntimeError: ЮKassa не настроена или не вернула confirmation_url.
        """
        from decimal import Decimal as Dec

        from src.constants.fees import YOOKASSA_FEE_RATE

        # 1. Pre-flight user check
        user_repo = UserRepository(session)
        user = await user_repo.get_by_id(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        # 2. Compute amounts (1:1 credits — legacy field)
        credits_amount = int(desired_balance)
        desired_balance_dec = Dec(str(desired_balance))
        fee_amount = (desired_balance_dec * YOOKASSA_FEE_RATE).quantize(Dec("0.01"))
        gross_amount = desired_balance_dec + fee_amount

        # 3. YooKassa SDK config
        if not settings.yookassa_shop_id or not settings.yookassa_secret_key:
            raise RuntimeError(
                "YooKassa credentials are not configured "
                "(YOOKASSA_SHOP_ID / YOOKASSA_SECRET_KEY)"
            )

        Configuration.account_id = settings.yookassa_shop_id
        Configuration.secret_key = settings.yookassa_secret_key

        idempotency_key = str(uuid.uuid4())
        payment_request = {
            "amount": {"value": str(gross_amount), "currency": "RUB"},
            "confirmation": {
                "type": "redirect",
                "return_url": settings.yookassa_return_url,
            },
            "capture": True,
            "description": f"Пополнение баланса RekHarborBot: {desired_balance_dec} ₽",
            "metadata": {
                "user_id": str(user_id),
                "desired_balance": str(desired_balance_dec),
                "fee_amount": str(fee_amount),
                "gross_amount": str(gross_amount),
            },
        }

        # 4. SDK call OUTSIDE DB transaction.
        # Ordering invariant: SDK call MUST run before any DB write so
        # that a failed SDK call leaves zero local rows. Moving this
        # inside session.begin() / after flush would create a
        # "real charge, no local record" footgun on rollback.
        try:
            yk_payment = await asyncio.to_thread(
                Payment.create, payment_request, idempotency_key
            )
        except (
            ApiError,
            BadRequestError,
            ForbiddenError,
            NotFoundError,
            ResponseProcessingError,
            TooManyRequestsError,
            UnauthorizedError,
        ) as exc:
            content = getattr(exc, "content", None) or {}
            err_code = str(content.get("code") or "unknown")
            err_description = str(content.get("description") or exc)
            err_request_id = str(content.get("request_id") or "unknown")
            logger.error(
                "YooKassa API error for user %s: code=%s, description=%s,"
                " request_id=%s",
                user_id,
                err_code,
                err_description,
                err_request_id,
            )
            raise PaymentProviderError(
                code=err_code,
                description=err_description,
                request_id=err_request_id,
            ) from exc

        payment_id = yk_payment.id
        confirmation = yk_payment.confirmation
        confirmation_url = (
            confirmation.confirmation_url if confirmation is not None else None
        )
        if not confirmation_url:
            raise RuntimeError(
                f"YooKassa did not return a confirmation URL for payment {payment_id}"
            )

        # 5. Persist via session — caller commits.
        yookassa_record = YooKassaPayment(
            payment_id=payment_id,
            user_id=user_id,
            gross_amount=gross_amount,
            desired_balance=desired_balance_dec,
            fee_amount=fee_amount,
            status="pending",
            payment_url=confirmation_url,
        )
        session.add(yookassa_record)
        await session.flush()

        transaction_repo = TransactionRepository(session)
        await transaction_repo.create({
            "user_id": user_id,
            "amount": gross_amount,
            "type": TransactionType.topup,
            "yookassa_payment_id": payment_id,
            "meta_json": {
                "status": "pending",
                "method": "yookassa",
                "credits": credits_amount,
                "desired_balance": str(desired_balance_dec),
                "fee_amount": str(fee_amount),
                "gross_amount": str(gross_amount),
            },
        })

        logger.info(
            f"Payment {payment_id} created for user {user_id}: "
            f"desired={desired_balance_dec}, fee={fee_amount}, gross={gross_amount} RUB"
        )

        return {
            "payment_id": payment_id,
            "payment_url": confirmation_url,
            "amount": str(gross_amount),
            "credits": credits_amount,
            "status": "pending",
        }

    async def process_webhook(
        self,
        body: bytes,
        client_ip: str | None,
    ) -> WebhookEvent:
        """Verify источник + распарсить YooKassa webhook payload.

        S-48 contract: метод НЕ трогает БД, не открывает session,
        не commit'ит. Возвращает DTO; caller (router) распоряжается
        бизнес-логикой и lifecycle транзакции.

        Authorization: YooKassa аутентифицирует webhook'и по IP
        whitelist (а не HMAC). Источник публичен:
        https://yookassa.ru/developers/api/notifications#ip-address

        Args:
            body: Raw request body (bytes).
            client_ip: request.client.host от FastAPI; None если
                request пришёл без peer info.

        Returns:
            WebhookEvent с event_type, payment_id, payload (full
            ``object`` payload — caller может извлечь
            payment_method/receipt/metadata по необходимости).

        Raises:
            WebhookAuthError: client_ip отсутствует или вне
                YOOKASSA_IP_NETWORKS.
            InvalidPayloadError: body не parseable как JSON, либо
                отсутствует обязательное поле ``event`` /
                ``object.id``.
        """
        if not client_ip:
            raise WebhookAuthError("client IP is missing")
        try:
            ip = ip_address(client_ip)
        except ValueError as exc:
            raise WebhookAuthError(f"client IP is malformed: {client_ip}") from exc
        if not any(ip in ip_network(net) for net in YOOKASSA_IP_NETWORKS):
            raise WebhookAuthError(f"client IP {client_ip} not in YooKassa whitelist")

        try:
            data = json.loads(body)
        except (json.JSONDecodeError, ValueError, TypeError) as exc:
            raise InvalidPayloadError(f"webhook body is not valid JSON: {exc}") from exc

        if not isinstance(data, dict):
            raise InvalidPayloadError("webhook body must be a JSON object")

        event_type = data.get("event")
        obj = data.get("object")
        if not isinstance(event_type, str) or not event_type:
            raise InvalidPayloadError("webhook payload missing 'event' field")
        if not isinstance(obj, dict):
            raise InvalidPayloadError("webhook payload missing 'object' field")

        payment_id = obj.get("id")
        if not isinstance(payment_id, str) or not payment_id:
            raise InvalidPayloadError("webhook payload missing 'object.id' field")

        return WebhookEvent(
            event_type=event_type,
            payment_id=payment_id,
            payload=obj,
        )

    async def get_payment_status(self, payment_id: str) -> str | None:
        """
        Получить статус платежа.

        SDK без type stubs возвращает Any → return type honest str | None.
        Каждый caller обязан handle None case.

        Args:
            payment_id: UUID платежа от ЮKassa.

        Returns:
            Статус платежа (pending/waiting_for_capture/succeeded/canceled),
            либо None если SDK не вернул status field.
        """
        payment = await asyncio.to_thread(Payment.find_one, payment_id)
        status = getattr(payment, "status", None)
        return status if isinstance(status, str) else None


# Singleton instance
yookassa_service = YooKassaService()
