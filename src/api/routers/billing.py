"""
FastAPI роутер биллинга для Telegram Mini App.

Endpoints:
  GET  /api/billing/balance          — баланс, тариф, история кратко
  GET  /api/billing/history          — история платежей с пагинацией
  POST /api/billing/topup/crypto     — создать CryptoBot инвойс
  POST /api/billing/topup/stars      — создать Telegram Stars инвойс
  POST /api/billing/topup/yookassa   — создать ЮKassa платёж
  POST /webhooks/yookassa            — webhook от ЮKassa
  GET  /api/billing/invoice/{id}     — проверить статус инвойса
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import update

from src.api.dependencies import CurrentUser
from src.db.models.user import User
from src.db.repositories.user_repo import UserRepository
from src.db.session import async_session_factory

logger = logging.getLogger(__name__)
router = APIRouter(tags=["billing"])


# ─── Константы ──────────────────────────────────────────────────

CREDIT_PACKAGES = [
    {"id": "nano", "credits": 300, "bonus": 0, "label": "Nano"},
    {"id": "mini", "credits": 600, "bonus": 0, "label": "Mini"},
    {"id": "standard", "credits": 1200, "bonus": 100, "label": "Standard"},
    {"id": "business", "credits": 3500, "bonus": 500, "label": "Business"},
]

PLAN_COSTS = {
    "free": 0,
    "starter": 299,
    "pro": 999,
    "business": 2999,
}

CURRENCIES = ["USDT", "TON", "BTC", "ETH", "LTC"]


def _get_package(package_id: str) -> dict | None:
    return next((p for p in CREDIT_PACKAGES if p["id"] == package_id), None)


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
    credits: int
    plan: str
    plan_expires_at: str | None
    ai_generations_used: int
    ai_included: int
    packages: list[dict]
    plan_costs: dict[str, int]


class PaymentHistoryItem(BaseModel):
    id: int
    method: str
    currency: str | None
    credits: int
    bonus_credits: int
    status: str
    created_at: str


class HistoryResponse(BaseModel):
    items: list[PaymentHistoryItem]
    total: int
    page: int
    pages: int


class CryptoTopupRequest(BaseModel):
    package_id: str
    currency: str


class CryptoTopupResponse(BaseModel):
    pay_url: str
    invoice_id: str
    credits: int
    bonus_credits: int
    amount: str
    currency: str


class StarsTopupRequest(BaseModel):
    package_id: str


class StarsTopupResponse(BaseModel):
    invoice_link: str
    credits: int
    bonus_credits: int
    stars_amount: int


class PlanRequest(BaseModel):
    plan: str


class PlanResponse(BaseModel):
    success: bool
    plan: str
    credits_remaining: int
    message: str


class InvoiceStatusResponse(BaseModel):
    invoice_id: str
    status: str
    credits: int
    credited: bool


# ─── Endpoints ──────────────────────────────────────────────────


# ═══════════════════════════════════════════════════════════════
# NEW UNIFIED ENDPOINTS (P5)
# ═══════════════════════════════════════════════════════════════


@router.post("/topup", response_model=TopupResponse)
async def create_unified_topup(
    body: TopupRequest,
    current_user: CurrentUser,
) -> TopupResponse:
    """
    Создать единый запрос на пополнение баланса через ЮKassa.

    Принимает desired_amount и method (yookassa), создаёт платёж
    и возвращает ссылку на оплату.

    Args:
        body: Данные пополнения (desired_amount, method).
        current_user: Текущий пользователь.

    Returns:
        TopupResponse: Данные платежа (payment_id, payment_url, status).

    Raises:
        HTTPException 400: Некорректная сумма или метод оплаты.
    """
    from decimal import Decimal

    from src.constants.payments import MAX_TOPUP, MIN_TOPUP
    from src.core.services.billing_service import BillingService

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

    # Создание платежа через billing_service
    billing_service = BillingService()
    payment_data = await billing_service.create_payment(
        user_id=current_user.id,
        amount=desired_amount,
        payment_method="yookassa",
    )

    logger.info(f"Unified topup created: user={current_user.id}, amount={desired_amount}")

    return TopupResponse(
        payment_id=payment_data["payment_id"],
        payment_url=payment_data["payment_url"],
        status=payment_data["status"],
    )


@router.get("/topup/{payment_id}/status")
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


@router.get("/plans", response_model=list[PlanDetail])
async def get_plans() -> list[PlanDetail]:
    """
    Получить список тарифных планов.

    Возвращает тарифы из констант с информацией о цене,
    возможностях и периоде действия.

    Returns:
        list[PlanDetail]: Список тарифов.
    """
    from src.constants.tariffs import PLAN_DISPLAY_NAMES, PLAN_EMOJIS, TARIFF_CREDIT_COST

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
        cost = TARIFF_CREDIT_COST.get(plan_id, 0)

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


@router.get("/balance", response_model=BalanceResponse)
async def get_balance(current_user: CurrentUser) -> BalanceResponse:
    """Баланс пользователя + информация для Billing страницы."""
    plan_str = _plan_label(current_user.plan)
    ai_included = {"pro": 5, "business": 20}.get(plan_str, 0)

    expires_str = None
    if current_user.plan_expires_at:
        expires_str = current_user.plan_expires_at.isoformat()

    # v4.2: ЮKassa only — USDT конвертация удалена
    # Добавляем total_credits к каждому пакету
    packages_with_price: list[dict[str, Any]] = []
    for pkg in CREDIT_PACKAGES:
        total = int(str(pkg["credits"])) + int(str(pkg["bonus"]))
        packages_with_price.append(
            {
                **pkg,
                "total_credits": total,
            }
        )

    return BalanceResponse(
        credits=current_user.credits,
        plan=plan_str,
        plan_expires_at=expires_str,
        ai_generations_used=current_user.ai_generations_used,
        ai_included=ai_included,
        packages=packages_with_price,
        plan_costs=PLAN_COSTS,
    )


@router.get("/history", response_model=HistoryResponse)
async def get_history(
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=50),
) -> HistoryResponse:
    """История платежей пользователя."""
    # CryptoPayment model removed — return empty history
    return HistoryResponse(items=[], total=0, page=page, pages=1)


@router.post("/topup/crypto", response_model=CryptoTopupResponse)
async def create_crypto_invoice(
    body: CryptoTopupRequest,
    current_user: CurrentUser,
) -> CryptoTopupResponse:
    """CryptoBot пополнение удалено. Используйте ЮKassa."""
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="CryptoBot пополнение удалено. Используйте ЮKassa.",
    )


@router.post("/topup/stars", response_model=StarsTopupResponse)
async def create_stars_invoice(
    body: StarsTopupRequest,
    current_user: CurrentUser,
) -> StarsTopupResponse:
    """
    Создать Telegram Stars инвойс.
    Возвращает invoice_link для открытия через Telegram.
    """

    package = _get_package(body.package_id)
    if not package:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown package: {body.package_id}",
        )

    credits = package["credits"]
    bonus = package["bonus"]
    credits + bonus

    # v4.2: Stars удалены — возвращаем ошибку
    raise HTTPException(
        status_code=400,
        detail="Telegram Stars не поддерживаются. Используйте ЮKassa."
    )


@router.post("/plan", response_model=PlanResponse)
async def change_plan(
    body: PlanRequest,
    current_user: CurrentUser,
) -> PlanResponse:
    """
    Сменить тариф. Списывает кредиты за новый тариф.
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
    if cost > 0 and current_user.credits < cost:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Insufficient credits. Need {cost}, have {current_user.credits}",
        )

    # Применяем тариф
    async with async_session_factory() as session:
        repo = UserRepository(session)
        if cost > 0:
            await repo.update_credits(current_user.id, -cost)

        expires_at = datetime.now(UTC) + timedelta(days=30) if plan_str != "free" else None

        await session.execute(
            update(User)
            .where(User.id == current_user.id)
            .values(
                plan=plan_str,
                plan_expires_at=expires_at,
                ai_generations_used=0,
            )
        )
        await session.commit()

    remaining = current_user.credits - cost

    plan_labels = {
        "free": "FREE",
        "starter": "STARTER",
        "pro": "PRO",
        "business": "BUSINESS",
    }

    return PlanResponse(
        success=True,
        plan=plan_str,
        credits_remaining=remaining,
        message=f"Тариф {plan_labels.get(plan_str, plan_str)} активирован на 30 дней",
    )


@router.get("/invoice/{invoice_id}", response_model=InvoiceStatusResponse)
async def get_invoice_status(
    invoice_id: str,
    current_user: CurrentUser,
) -> InvoiceStatusResponse:
    """CryptoBot инвойсы удалены."""
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")


# =============================================================================
# YOOKASSA WEBHOOK
# =============================================================================


@router.post("/webhooks/yookassa", status_code=200)
async def yookassa_webhook(
    request: Request,
) -> dict[str, str]:
    """
    Webhook от ЮKassa для обработки событий платежей.

    ЮKassa требует ответ 200 при любом исходе — иначе будет ретрай.

    v4.2: Зачислять metadata['desired_balance'] в balance_rub (НЕ gross_amount).
    """
    try:
        from decimal import Decimal

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
                # Получить метаданные из YooKassaPayment
                from sqlalchemy import select

                from src.db.models.yookassa_payment import YooKassaPayment

                result = await session.execute(
                    select(YooKassaPayment).where(YooKassaPayment.payment_id == payment_id)
                )
                record = result.scalar_one_or_none()

                if record:
                    # Извлечь desired_balance из metadata (строка)
                    metadata = {
                        "desired_balance": str(record.credits),  # credits = desired_balance в v4.2
                        "user_id": str(record.user_id),
                    }
                    gross_amount = Decimal(str(record.amount_rub))

                    await billing_service.process_topup_webhook(
                        session=session,
                        payment_id=payment_id,
                        gross_amount=gross_amount,
                        metadata=metadata,
                    )
                    logger.info(
                        f"Topup processed: payment_id={payment_id}, "
                        f"desired={metadata['desired_balance']}, gross={gross_amount}"
                    )
                else:
                    logger.warning(f"YooKassaPayment record not found for {payment_id}")

    except Exception as e:
        logger.error("Ошибка обработки webhook ЮKassa: %s", e)
    return {"status": "ok"}
