"""
Billing router для управления балансом и платежами.
"""

import logging
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.api.dependencies import CurrentUser
from src.db.models.user import User
from src.db.repositories.transaction_repo import TransactionRepository
from src.db.repositories.user_repo import UserRepository
from src.db.session import async_session_factory

logger = logging.getLogger(__name__)

router = APIRouter()


# === Pydantic схемы ===

class BalanceResponse(BaseModel):
    """Ответ с балансом."""

    balance: str
    currency: str = "RUB"


class TransactionResponse(BaseModel):
    """Транзакция."""

    id: int
    amount: str
    type: str
    payment_id: str | None
    created_at: str

    class Config:
        from_attributes = True


class TransactionListResponse(BaseModel):
    """Список транзакций."""

    transactions: list[TransactionResponse]
    total: int
    page: int
    page_size: int


class TopUpRequest(BaseModel):
    """Запрос на пополнение."""

    amount: Decimal = Field(..., gt=0, le=100000)
    payment_method: str = "yookassa"


class TopUpResponse(BaseModel):
    """Ответ на пополнение."""

    payment_id: str
    payment_url: str
    amount: str
    status: str


# === Эндпоинты ===

@router.get("/balance", response_model=BalanceResponse)
async def get_balance(current_user: CurrentUser):
    """
    Получить баланс пользователя.

    Args:
        current_user: Текущий пользователь.

    Returns:
        Баланс пользователя.
    """
    return BalanceResponse(balance=str(current_user.balance))


@router.get("/history", response_model=TransactionListResponse)
async def get_transaction_history(
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    transaction_type: str | None = Query(None),
):
    """
    Получить историю транзакций.

    Args:
        current_user: Текущий пользователь.
        page: Номер страницы.
        page_size: Размер страницы.
        transaction_type: Фильтр по типу (topup/spend).

    Returns:
        Список транзакций.
    """
    from src.db.models.transaction import TransactionType

    async with async_session_factory() as session:
        transaction_repo = TransactionRepository(session)

        # Фильтр по типу
        type_filter = None
        if transaction_type:
            try:
                type_filter = TransactionType(transaction_type)
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid transaction type: {transaction_type}",
                ) from e

        transactions, total = await transaction_repo.get_by_user(
            user_id=current_user.id,
            transaction_type=type_filter,
            page=page,
            page_size=page_size,
        )

        return TransactionListResponse(
            transactions=[TransactionResponse.model_validate(t) for t in transactions],
            total=total,
            page=page,
            page_size=page_size,
        )


@router.post("/topup", response_model=TopUpResponse)
async def create_topup(
    request: TopUpRequest,
    current_user: CurrentUser,
):
    """
    Создать платёж на пополнение баланса.

    Args:
        request: Данные платежа.
        current_user: Текущий пользователь.

    Returns:
        Платёжные данные.
    """
    from src.core.services.billing_service import billing_service

    try:
        # Создаём платёж через billing service
        payment = await billing_service.create_payment(
            user_id=current_user.id,
            amount=request.amount,
            payment_method=request.payment_method,
        )

        logger.info(f"Payment {payment['payment_id']} created for user {current_user.id}")

        return TopUpResponse(
            payment_id=payment["payment_id"],
            payment_url=payment["payment_url"],
            amount=str(request.amount),
            status="pending",
        )

    except Exception as e:
        logger.error(f"Error creating payment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Payment creation failed: {str(e)}",
        ) from e


@router.get("/topup/{payment_id}")
async def check_payment(
    payment_id: str,
    current_user: CurrentUser,
):
    """
    Проверить статус платежа.

    Args:
        payment_id: ID платежа.
        current_user: Текущий пользователь.

    Returns:
        Статус платежа.
    """
    from src.core.services.billing_service import billing_service

    try:
        payment_status = await billing_service.check_payment(
            payment_id=payment_id,
            user_id=current_user.id,
        )

        return {
            "payment_id": payment_id,
            "status": payment_status["status"],
            "amount": payment_status["amount"],
            "credited": payment_status.get("credited", False),
        }

    except Exception as e:
        logger.error(f"Error checking payment: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment not found: {payment_id}",
        ) from e


@router.post("/spend")
async def spend_balance(  # noqa: B008
    current_user: CurrentUser,
    amount: Decimal = Field(..., gt=0),
    description: str = "",
):
    """
    Списать средства с баланса.

    Args:
        amount: Сумма для списания.
        description: Описание списания.
        current_user: Текущий пользователь.

    Returns:
        Результат списания.
    """
    from src.core.services.billing_service import billing_service

    async with async_session_factory() as session:
        user_repo = UserRepository(session)

        # Проверяем баланс
        user = await user_repo.get_by_id(current_user.id)
        if not user or user.balance < amount:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Insufficient balance",
            )

        # Списываем
        await billing_service.deduct_balance(
            user_id=current_user.id,
            amount=amount,
            description=description,
        )

        logger.info(f"Spend {amount} RUB from user {current_user.id}")

        return {
            "status": "success",
            "amount": str(amount),
            "new_balance": str(user.balance - amount),
        }


@router.get("/referral")
async def get_referral_info(current_user: CurrentUser):
    """
    Получить информацию о реферальной программе.

    Args:
        current_user: Текущий пользователь.

    Returns:
        Реферальная информация.
    """
    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_id(current_user.id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # Считаем количество рефералов
        from sqlalchemy import func, select

        query = select(func.count(User.id)).where(User.referred_by_id == current_user.id)
        result = await session.execute(query)
        referrals_count = result.scalar_one() or 0

        return {
            "referral_code": user.referral_code,
            "referral_link": f"https://t.me/your_bot?start={user.referral_code}",
            "referrals_count": referrals_count,
            "bonus_percentage": 10,  # 10% от пополнения реферала
        }
