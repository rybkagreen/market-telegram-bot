"""
FastAPI роутер биллинга для Telegram Mini App.

Endpoints:
  GET  /api/billing/balance          — баланс, тариф, история кратко
  GET  /api/billing/history          — история платежей с пагинацией
  POST /api/billing/topup/crypto     — создать CryptoBot инвойс
  POST /api/billing/topup/stars      — создать Telegram Stars инвойс
  POST /api/billing/plan             — сменить тариф
  GET  /api/billing/invoice/{id}     — проверить статус инвойса
"""
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select, update

from src.api.dependencies import CurrentUser
from src.config.settings import settings
from src.core.services.cryptobot_service import cryptobot_service
from src.db.models.crypto_payment import CryptoPayment, PaymentMethod, PaymentStatus
from src.db.models.user import User
from src.db.repositories.user_repo import UserRepository
from src.db.session import async_session_factory

logger = logging.getLogger(__name__)
router = APIRouter(tags=["billing"])


# ─── Константы ──────────────────────────────────────────────────

CREDIT_PACKAGES = [
    {"id": "nano",     "credits": 300,  "bonus": 0,   "label": "Nano"},
    {"id": "mini",     "credits": 600,  "bonus": 0,   "label": "Mini"},
    {"id": "standard", "credits": 1200, "bonus": 100, "label": "Standard"},
    {"id": "business", "credits": 3500, "bonus": 500, "label": "Business"},
]

PLAN_COSTS = {
    "free":     0,
    "starter":  299,
    "pro":      999,
    "business": 2999,
}

CURRENCIES = ["USDT", "TON", "BTC", "ETH", "LTC"]


def _get_package(package_id: str) -> dict | None:
    return next((p for p in CREDIT_PACKAGES if p["id"] == package_id), None)


def _plan_label(plan) -> str:
    return plan.value if hasattr(plan, "value") else str(plan)


# ─── Схемы ──────────────────────────────────────────────────────

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

@router.get("/balance", response_model=BalanceResponse)
async def get_balance(current_user: CurrentUser) -> BalanceResponse:
    """Баланс пользователя + информация для Billing страницы."""
    plan_str = _plan_label(current_user.plan)
    ai_included = {"pro": 5, "business": 20}.get(plan_str, 0)

    expires_str = None
    if current_user.plan_expires_at:
        expires_str = current_user.plan_expires_at.isoformat()

    # Добавляем примерные суммы в USDT к каждому пакету
    packages_with_price: list[dict[str, Any]] = []
    for pkg in CREDIT_PACKAGES:
        total = int(str(pkg["credits"])) + int(str(pkg["bonus"]))
        usdt = round(total / settings.credits_per_usdt, 2)
        packages_with_price.append({
            **pkg,
            "total_credits": total,
            "usdt_approx": usdt,
        })

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
    async with async_session_factory() as session:
        count_result = await session.execute(
            select(func.count(CryptoPayment.id))
            .where(CryptoPayment.user_id == current_user.id)
        )
        total = count_result.scalar() or 0

        offset = (page - 1) * limit
        result = await session.execute(
            select(CryptoPayment)
            .where(CryptoPayment.user_id == current_user.id)
            .order_by(CryptoPayment.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        payments = result.scalars().all()

    items = []
    for p in payments:
        method_str = p.method.value if hasattr(p.method, "value") else str(p.method)
        status_str = p.status.value if hasattr(p.status, "value") else str(p.status)
        items.append(PaymentHistoryItem(
            id=p.id,
            method=method_str,
            currency=getattr(p, "currency", None),
            credits=p.credits or 0,
            bonus_credits=p.bonus_credits or 0,
            status=status_str,
            created_at=p.created_at.isoformat() if p.created_at else "",
        ))

    pages = max(1, (total + limit - 1) // limit)
    return HistoryResponse(items=items, total=total, page=page, pages=pages)


@router.post("/topup/crypto", response_model=CryptoTopupResponse)
async def create_crypto_invoice(
    body: CryptoTopupRequest,
    current_user: CurrentUser,
) -> CryptoTopupResponse:
    """
    Создать CryptoBot инвойс для пополнения через криптовалюту.
    Возвращает pay_url для открытия в браузере/боте.
    """
    package = _get_package(body.package_id)
    if not package:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown package: {body.package_id}",
        )

    currency = body.currency.upper()
    if currency not in CURRENCIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported currency: {currency}",
        )

    credits = package["credits"]
    bonus  = package["bonus"]
    total_credits = credits + bonus

    # Считаем сумму в выбранной валюте
    rate = settings.currency_rates.get(currency)
    if not rate:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No rate configured for {currency}",
        )
    amount = round(total_credits / rate, 8)
    amount_str = f"{amount:.8f}".rstrip("0").rstrip(".")

    # Описание инвойса
    description = (
        f"Market Bot: {total_credits} кредитов"
        + (f" (+{bonus} бонус)" if bonus else "")
    )

    # Payload для идентификации при вебхуке
    payload = f"miniapp:{current_user.id}:{body.package_id}"

    # Создаём инвойс через CryptoBot API
    try:
        invoice = await cryptobot_service.create_invoice(
            currency=currency,
            amount=amount,  # Передаём float
            payload=payload,
            description=description,
            expires_in=3600,
        )
    except Exception as e:
        logger.error(f"CryptoBot invoice error: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to create CryptoBot invoice",
        )

    # Сохраняем в БД
    async with async_session_factory() as session:
        payment = CryptoPayment(
            user_id=current_user.id,
            method=PaymentMethod.CRYPTOBOT,
            invoice_id=str(invoice.invoice_id),
            currency=currency,
            amount=amount,
            credits=credits,
            bonus_credits=bonus,
            status=PaymentStatus.PENDING,
            payload={"package_id": body.package_id},
        )
        session.add(payment)
        await session.commit()

    return CryptoTopupResponse(
        pay_url=invoice.pay_url,
        invoice_id=str(invoice.invoice_id),
        credits=credits,
        bonus_credits=bonus,
        amount=amount_str,
        currency=currency,
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
    from aiogram import Bot
    from aiogram.types import LabeledPrice

    package = _get_package(body.package_id)
    if not package:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown package: {body.package_id}",
        )

    credits = package["credits"]
    bonus  = package["bonus"]
    total_credits = credits + bonus

    # Считаем количество Stars
    stars_amount = max(1, round(total_credits / settings.credits_per_star))

    # Создаём инвойс через Telegram Bot API
    try:
        bot = Bot(token=settings.bot_token)
        invoice_link = await bot.create_invoice_link(
            title=f"Market Bot — {package['label']}",
            description=f"{total_credits} кредитов" + (f" (+{bonus} бонус)" if bonus else ""),
            payload=f"miniapp_stars:{current_user.id}:{body.package_id}",
            currency="XTR",
            prices=[LabeledPrice(label="Кредиты", amount=stars_amount)],
        )
        await bot.session.close()
    except Exception as e:
        logger.error(f"Stars invoice error: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to create Stars invoice",
        )

    # Сохраняем pending платёж
    async with async_session_factory() as session:
        payment = CryptoPayment(
            user_id=current_user.id,
            method=PaymentMethod.STARS,
            invoice_id=f"stars_{current_user.id}_{body.package_id}",
            stars_amount=stars_amount,
            credits=credits,
            bonus_credits=bonus,
            status=PaymentStatus.PENDING,
            payload={"package_id": body.package_id},
        )
        session.add(payment)
        await session.commit()

    return StarsTopupResponse(
        invoice_link=invoice_link,
        credits=credits,
        bonus_credits=bonus,
        stars_amount=stars_amount,
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
    """
    Проверить статус CryptoBot инвойса.
    Используется фронтендом для polling статуса оплаты.
    """
    async with async_session_factory() as session:
        result = await session.execute(
            select(CryptoPayment).where(
                CryptoPayment.invoice_id == invoice_id,
                CryptoPayment.user_id == current_user.id,
            )
        )
        payment = result.scalar_one_or_none()

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found",
        )

    payment_status = (
        payment.status.value if hasattr(payment.status, "value")
        else str(payment.status)
    )

    # Если уже оплачен — возвращаем сразу
    if payment_status == "paid":
        return InvoiceStatusResponse(
            invoice_id=invoice_id,
            status="paid",
            credits=payment.credits + payment.bonus_credits,
            credited=True,
        )

    # Проверяем актуальный статус через CryptoBot API
    try:
        invoice_data = await cryptobot_service.get_invoice(invoice_id)
        remote_status = invoice_data.status
    except Exception as e:
        logger.warning(f"CryptoBot status check failed: {e}")
        remote_status = payment_status

    return InvoiceStatusResponse(
        invoice_id=invoice_id,
        status=remote_status,
        credits=payment.credits + payment.bonus_credits,
        credited=payment_status == "paid",
    )
