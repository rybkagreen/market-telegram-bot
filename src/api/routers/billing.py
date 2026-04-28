"""
FastAPI роутер биллинга для Telegram Mini App.

Endpoints:
  GET  /api/billing/balance          — баланс, тариф, история кратко
  GET  /api/billing/history          — история платежей с пагинацией
  POST /api/billing/topup            — создать ЮKassa платёж
  POST /webhooks/yookassa            — webhook от ЮKassa
"""

import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import CurrentUser, get_db_session
from src.config.settings import settings
from src.constants.payments import PLAN_LIMITS
from src.db.models.user import User
from src.db.repositories.user_repo import UserRepository
from src.db.session import async_session_factory

logger = logging.getLogger(__name__)
router = APIRouter(tags=["billing"])


# ─── Константы ──────────────────────────────────────────────────

# YooKassa IP ranges for webhook verification
# https://yookassa.ru/developers/api/notifications#ip-address
YOOKASSA_IPS: list[str] = [
    "185.71.76.0/27",
    "185.71.77.0/27",
    "77.75.153.0/25",
    "77.75.156.11/32",
    "77.75.156.35/32",
    "77.75.154.128/25",
    "2a02:5180::/32",
]

PLAN_COSTS = {
    "free": 0,
    "starter": settings.tariff_cost_starter,
    "pro": settings.tariff_cost_pro,
    "business": settings.tariff_cost_business,
}


def _plan_label(plan) -> str:
    return plan.value if hasattr(plan, "value") else str(plan)


# ─── Схемы ──────────────────────────────────────────────────────


class TopupRequest(BaseModel):
    """Запрос на пополнение баланса."""

    desired_amount: int = Field(..., gt=0, description="Сумма пополнения в рублях")
    method: str = Field(default="yookassa", description="Метод оплаты (yookassa)")


class TopupResponse(BaseModel):
    """Ответ с данными платежа."""

    payment_id: str
    payment_url: str
    status: str

    model_config = {"from_attributes": True}


class PlanDetail(BaseModel):
    """Детали тарифа."""

    id: str
    name: str
    price: int
    features: list[str]
    period_days: int = 30


class BalanceResponse(BaseModel):
    balance_rub: Decimal
    plan: str
    plan_expires_at: str | None = None
    ai_generations_used: int
    ai_included: int
    plan_costs: dict[str, int]


class BillingHistoryItem(BaseModel):
    """Элемент истории транзакций пользователя."""

    id: int = Field(..., description="ID транзакции")
    type: str = Field(..., description="Тип транзакции")
    amount: Decimal = Field(
        ..., description="Сумма (всегда положительная; направление определяется типом)"
    )
    description: str | None = Field(None, description="Описание операции")
    placement_request_id: int | None = Field(None, description="ID заявки (если применимо)")
    status: str = Field(..., description="'completed' | 'pending'")
    created_at: str = Field(..., description="ISO datetime")


class BillingHistoryResponse(BaseModel):
    """Ответ истории платежей с пагинацией."""

    items: list[BillingHistoryItem]
    total: int
    page: int
    pages: int


class PlanRequest(BaseModel):
    plan: str


class PlanResponse(BaseModel):
    success: bool
    plan: str
    balance_rub_remaining: Decimal
    message: str


class FrozenPlacementItem(BaseModel):
    """Элемент заморозки — PlacementRequest в escrow/pending_payment."""

    placement_id: int
    channel_title: str
    amount: Decimal
    status: Literal["escrow", "pending_payment"]
    scheduled_at: datetime | None = None
    created_at: datetime


class FrozenBalanceResponse(BaseModel):
    """Сводка заморозок средств для BalanceHero виджета."""

    total_frozen: Decimal
    escrow_count: int
    pending_payment_count: int
    items: list[FrozenPlacementItem]


# ─── Endpoints ──────────────────────────────────────────────────


# ═══════════════════════════════════════════════════════════════
# NEW UNIFIED ENDPOINTS (P5)
# ═══════════════════════════════════════════════════════════════


@router.post("/topup", responses={400: {"description": "Bad request"}})
async def create_unified_topup(
    body: TopupRequest,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TopupResponse:
    """
    Создать единый запрос на пополнение баланса через ЮKassa.

    Принимает desired_amount и method (yookassa), создаёт платёж
    и возвращает ссылку на оплату.

    Args:
        body: Данные пополнения (desired_amount, method).
        current_user: Текущий пользователь.
        session: DB-сессия (caller-controlled, commits via dependency).

    Returns:
        TopupResponse: Данные платежа (payment_id, payment_url, status).

    Raises:
        HTTPException 400: Некорректная сумма или метод оплаты.
        HTTPException 503: ЮKassa временно недоступна.
    """
    from decimal import Decimal

    from src.constants.payments import MAX_TOPUP, MIN_TOPUP
    from src.core.services.billing_service import PaymentProviderError
    from src.core.services.yookassa_service import YooKassaService

    # Валидация метода оплаты
    if body.method != "yookassa":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported payment method: {body.method}. Use 'yookassa'.",
        )

    # Валидация суммы
    desired_amount = Decimal(str(body.desired_amount))
    if desired_amount < MIN_TOPUP:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Minimum topup amount is {MIN_TOPUP} RUB",
        )
    if desired_amount > MAX_TOPUP:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum topup amount is {MAX_TOPUP} RUB",
        )

    # Создание платежа через YooKassaService (caller-controlled session, S-48)
    yookassa_service = YooKassaService()
    try:
        payment_data = await yookassa_service.create_topup_payment(
            session=session,
            user_id=current_user.id,
            desired_balance=desired_amount,
        )
    except PaymentProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "message": (
                    "Платёжный сервис временно недоступен."
                    " Попробуйте позже или обратитесь в поддержку."
                ),
                "provider_error_code": exc.code,
                "provider_request_id": exc.request_id,
            },
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    logger.info(f"Unified topup created: user={current_user.id}, amount={desired_amount}")

    return TopupResponse(
        payment_id=payment_data["payment_id"],
        payment_url=payment_data["payment_url"],
        status=payment_data["status"],
    )


@router.get("/topup/{payment_id}/status", responses={404: {"description": "Not found"}})
async def get_topup_status(
    payment_id: str,
    current_user: CurrentUser,
) -> dict[str, str]:
    """
    Получить статус платежа.

    Alias для GET /invoice/{invoice_id}. Возвращает статус в формате,
    ожидаемом фронтендом: pending|succeeded|canceled.

    Args:
        payment_id: ID платежа.
        current_user: Текущий пользователь.

    Returns:
        dict: {"status": "pending"|"succeeded"|"canceled"}

    Raises:
        HTTPException 404: Платёж не найден.
    """
    from src.core.services.billing_service import BillingService

    billing_service = BillingService()

    try:
        payment_data = await billing_service.check_payment(
            payment_id=payment_id,
            user_id=current_user.id,
        )
        raw_status = payment_data.get("status", "pending")

        # Маппинг статусов YooKassa на фронтенд-формат
        status_map = {
            "pending": "pending",
            "waiting_for_capture": "pending",
            "succeeded": "succeeded",
            "succeeded_pending_withdrawal": "succeeded",
            "canceled": "canceled",
            "failed": "canceled",
        }
        mapped_status = status_map.get(raw_status, "pending")

        return {"status": mapped_status}

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment not found: {e}",
        ) from e


@router.get("/plans")
async def get_plans() -> list[PlanDetail]:
    """
    Получить список тарифных планов.

    Возвращает тарифы из констант с информацией о цене,
    возможностях и периоде действия.

    Returns:
        list[PlanDetail]: Список тарифов.
    """
    from src.constants.tariffs import PLAN_DISPLAY_NAMES, PLAN_EMOJIS

    # Тарифы из констант
    plans_data = {
        "free": {
            "features": [
                "1 активная кампания",
                "0 ИИ-генераций в месяц",
                "Только формат post_24h",
            ],
        },
        "starter": {
            "features": [
                "5 активных кампаний",
                "3 ИИ-генерации в месяц",
                "Форматы post_24h, post_48h",
                "Приоритетная поддержка",
            ],
        },
        "pro": {
            "features": [
                "20 активных кампаний",
                "20 ИИ-генераций в месяц",
                "Все форматы постов",
                "Расширенная аналитика",
                "Приоритетная поддержка",
            ],
        },
        "business": {
            "features": [
                "Безлимитные кампании",
                "Безлимитные ИИ-генерации",
                "Все форматы включая закрепы",
                "Полная аналитика",
                "Персональный менеджер",
            ],
        },
    }

    plans = []
    for plan_id, plan_info in plans_data.items():
        display_name = PLAN_DISPLAY_NAMES.get(plan_id, plan_id)
        emoji = PLAN_EMOJIS.get(plan_id, "")
        cost = PLAN_COSTS.get(plan_id, 0)

        plans.append(
            PlanDetail(
                id=plan_id,
                name=f"{emoji} {display_name}",
                price=cost,
                features=plan_info["features"],
                period_days=30,
            )
        )

    return plans


# ═══════════════════════════════════════════════════════════════
# LEGACY ENDPOINTS (сохранены для обратной совместимости)
# ═══════════════════════════════════════════════════════════════


@router.get("/balance")
async def get_balance(current_user: CurrentUser) -> BalanceResponse:
    """Баланс пользователя + информация для Billing страницы."""
    plan_str = _plan_label(current_user.plan)
    ai_included = PLAN_LIMITS.get(plan_str, {}).get("ai_per_month", 0)

    expires_str = None
    if current_user.plan_expires_at:
        expires_str = current_user.plan_expires_at.isoformat()

    return BalanceResponse(
        balance_rub=current_user.balance_rub,
        plan=plan_str,
        plan_expires_at=expires_str,
        ai_generations_used=current_user.ai_uses_count,
        ai_included=ai_included,
        plan_costs=PLAN_COSTS,
    )


@router.get("/frozen")
async def get_frozen_balance(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> FrozenBalanceResponse:
    """
    Заморозка средств рекламодателя — placements в escrow/pending_payment.

    Используется в BalanceHero (§7.6) для строки «Заморожено» и в
    NotificationsCard (§7.9) для агрегата «N кампаний в ожидании».

    ВАЖНО: Этот эндпоинт должен быть объявлен ДО `/history` и других
    статик-path GET'ов с int-параметрами (см. project_fastapi_route_ordering.md).
    """
    from src.db.repositories.placement_request_repo import PlacementRequestRepository

    repo = PlacementRequestRepository(session)
    placements = await repo.get_frozen_for_advertiser(advertiser_id=current_user.id)

    items: list[FrozenPlacementItem] = []
    total_frozen = Decimal("0")
    escrow_count = 0
    pending_payment_count = 0

    for p in placements:
        amount = p.final_price if p.final_price is not None else p.proposed_price
        total_frozen += amount

        status_value = p.status.value if hasattr(p.status, "value") else str(p.status)
        if status_value == "escrow":
            escrow_count += 1
        elif status_value == "pending_payment":
            pending_payment_count += 1

        channel_title = p.channel.title if p.channel else f"Channel #{p.channel_id}"
        items.append(
            FrozenPlacementItem(
                placement_id=p.id,
                channel_title=channel_title,
                amount=amount,
                status=status_value,  # type: ignore[arg-type]
                scheduled_at=p.final_schedule or p.proposed_schedule,
                created_at=p.created_at,
            )
        )

    return FrozenBalanceResponse(
        total_frozen=total_frozen,
        escrow_count=escrow_count,
        pending_payment_count=pending_payment_count,
        items=items,
    )


# Типы транзакций, видимые пользователю в истории.
# Примечание: payout / cancel_penalty / refund_partial / failed_permissions_refund
# существуют только как enum-значения — в БД не пишутся.
# Выводы средств записываются как refund_full с meta_json["type"]=="payout_request".
_VISIBLE_TX_TYPES = {
    "topup",
    "escrow_freeze",
    "escrow_release",
    "credits_buy",
    "spend",
    "payout_fee",
    "refund_full",
    "bonus",
}


@router.get("/history")
async def get_history(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> BillingHistoryResponse:
    """
    История всех транзакций пользователя.

    Включает: пополнения, эскроу, разблокировку эскроу, конвертацию кредитов,
    оплату тарифов (spend), выводы средств, возвраты, бонусы.

    Args:
        current_user: Текущий пользователь.
        page: Номер страницы (default: 1).
        limit: Количество записей (default: 20, max: 100).

    Returns:
        BillingHistoryResponse: Список транзакций с пагинацией.
    """
    from src.db.repositories.transaction_repo import TransactionRepository

    repo = TransactionRepository(session)
    txs, total = await repo.list_by_user_id(
        user_id=current_user.id,
        types_filter=_VISIBLE_TX_TYPES,
        page=page,
        limit=limit,
    )

    items = []
    for tx in txs:
        tx_type = tx.type.value if hasattr(tx.type, "value") else str(tx.type)
        # refund_full с meta_json["type"]=="payout_request" — это фактически вывод средств
        if tx_type == "refund_full" and isinstance(tx.meta_json, dict):
            meta_type = tx.meta_json.get("type", "")
            if meta_type == "payout_request":
                tx_type = "payout"

        items.append(
            BillingHistoryItem(
                id=tx.id,
                type=tx_type,
                amount=tx.amount,
                description=tx.description,
                placement_request_id=tx.placement_request_id,
                status=tx.payment_status if tx.payment_status else "completed",
                created_at=tx.created_at.isoformat()
                if tx.created_at
                else datetime.now(UTC).isoformat(),
            )
        )

    pages = (total + limit - 1) // limit if total > 0 else 0

    return BillingHistoryResponse(
        items=items,
        total=total,
        page=page,
        pages=pages,
    )


@router.post(
    "/credits",
    responses={400: {"description": "Bad request"}, 402: {"description": "Insufficient balance"}},
)
async def buy_credits(
    body: TopupRequest,
    current_user: CurrentUser,
) -> dict:
    """Оплатить тариф с рублёвого баланса (кредиты удалены, единая валюта ₽)."""
    from src.core.services.billing_service import BillingService, InsufficientFundsError

    amount = Decimal(str(body.desired_amount))
    if current_user.balance_rub < amount:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Недостаточно средств на балансе: {current_user.balance_rub} < {amount}",
        )

    try:
        billing_service = BillingService()
        amount_paid, _, _ = await billing_service.buy_credits_for_plan(current_user.id, amount)
    except InsufficientFundsError as e:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Недостаточно средств на балансе",
        ) from e

    logger.info(f"User #{current_user.id} paid {amount} ₽ for plan")
    return {"amount_rub": body.desired_amount}


@router.post("/plan", responses={400: {"description": "Bad request"}})
async def change_plan(
    body: PlanRequest,
    current_user: CurrentUser,
) -> PlanResponse:
    """
    Сменить тариф. Списывает ₽ с баланса за новый тариф.
    Нельзя перейти на тот же тариф.
    """
    plan_str = body.plan.lower()
    if plan_str not in PLAN_COSTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown plan: {plan_str}",
        )

    current_plan_str = _plan_label(current_user.plan)
    if plan_str == current_plan_str:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Already on this plan",
        )

    cost = PLAN_COSTS[plan_str]

    # Проверяем баланс
    if cost > 0 and current_user.balance_rub < Decimal(str(cost)):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Insufficient balance. Need {cost} ₽, have {current_user.balance_rub} ₽",
        )

    # Применяем тариф
    async with async_session_factory() as session:
        repo = UserRepository(session)
        if cost > 0:
            await repo.update_balance_rub(current_user.id, -Decimal(str(cost)))

        expires_at = datetime.now(UTC) + timedelta(days=30) if plan_str != "free" else None

        await session.execute(
            update(User)
            .where(User.id == current_user.id)
            .values(
                plan=plan_str,
                plan_expires_at=expires_at,
                ai_uses_count=0,
            )
        )
        try:
            await session.commit()
        except IntegrityError as e:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Конфликт данных: запись уже существует или нарушено ограничение",
            ) from e

    remaining = current_user.balance_rub - Decimal(str(cost))

    plan_labels = {
        "free": "FREE",
        "starter": "STARTER",
        "pro": "PRO",
        "business": "BUSINESS",
    }

    return PlanResponse(
        success=True,
        plan=plan_str,
        balance_rub_remaining=remaining,
        message=f"Тариф {plan_labels.get(plan_str, plan_str)} активирован на 30 дней",
    )


# =============================================================================
# YOOKASSA WEBHOOK
# =============================================================================


@router.post("/webhooks/yookassa", status_code=200, responses={403: {"description": "Forbidden"}})
async def yookassa_webhook(
    request: Request,
) -> dict[str, str]:
    """
    Webhook от ЮKassa для обработки событий платежей.

    ЮKassa требует ответ 200 при любом исходе — иначе будет ретрай.

    v4.2: Зачислять metadata['desired_balance'] в balance_rub (НЕ gross_amount).
    """
    # Верификация IP-адреса YooKassa
    from ipaddress import ip_address, ip_network

    client_ip = request.client.host if request.client else ""
    if not client_ip:
        logger.warning("YooKassa webhook with no client IP")
        raise HTTPException(
            status_code=403,
            detail="Forbidden: request not from YooKassa IP",
        )
    if not any(ip_address(client_ip) in ip_network(net) for net in YOOKASSA_IPS):
        logger.warning(f"YooKassa webhook from unknown IP: {client_ip}")
        raise HTTPException(
            status_code=403,
            detail="Forbidden: request not from YooKassa IP",
        )

    try:
        from src.core.services.billing_service import BillingService

        body = await request.json()
        logger.info("ЮKassa webhook event: %s", body.get("event", "unknown"))

        event_type = body.get("event", "")
        obj = body.get("object", {})
        payment_id = obj.get("id", "")

        if event_type == "payment.succeeded" and payment_id:
            # v4.2: Использовать billing_service.process_topup_webhook
            # который зачисляет metadata['desired_balance'] в balance_rub
            billing_service = BillingService()
            async with async_session_factory() as session:
                from src.db.repositories.yookassa_payment_repo import YookassaPaymentRepository

                repo = YookassaPaymentRepository(session)
                record = await repo.get_by_payment_id(payment_id)

                if record:
                    # Sprint A.2: извлечь и сохранить payment_method и receipt
                    payment_method = obj.get("payment_method", {})
                    receipt = obj.get("receipt", {})

                    record.payment_method_type = (
                        payment_method.get("type") if payment_method else None
                    )
                    record.receipt_id = receipt.get("id") if receipt else None
                    record.yookassa_metadata = obj  # сохраняем полный payload

                    # Извлечь desired_balance из metadata (строка)
                    metadata = {
                        "desired_balance": str(
                            record.desired_balance
                        ),  # credits = desired_balance в v4.2
                        "user_id": str(record.user_id),
                    }
                    gross_amount = record.gross_amount

                    await billing_service.process_topup_webhook(
                        session=session,
                        payment_id=payment_id,
                        gross_amount=gross_amount,
                        metadata=metadata,
                    )

                    # Обновить статус платежа на succeeded
                    record.status = "succeeded"
                    record.processed_at = datetime.now(UTC)
                    await session.commit()

                    logger.info(
                        f"Topup processed: payment_id={payment_id}, "
                        f"desired={metadata['desired_balance']}, gross={gross_amount}, "
                        f"method={record.payment_method_type}, receipt={record.receipt_id}"
                    )
                else:
                    logger.warning(f"YooKassaPayment record not found for {payment_id}")

    except (ValueError, KeyError, TypeError) as e:
        logger.error("Invalid webhook payload from YooKassa: %s", e)
        return {"status": "error", "detail": "Invalid webhook payload"}
    except Exception as e:
        logger.error("Unexpected error processing YooKassa webhook: %s", e, exc_info=True)
        # Return error so YooKassa retries
        return {"status": "error", "detail": "Webhook processing failed"}
    return {"status": "ok"}
