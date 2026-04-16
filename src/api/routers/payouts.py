"""
FastAPI router для управления заявками на выплату (Payouts).

Endpoints:
  GET  /api/payouts/         — список заявок текущего пользователя
  POST /api/payouts/         — создать заявку на выплату
  GET  /api/payouts/{id}     — детали заявки
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import CurrentUser, get_db_session
from src.api.schemas.payout import PayoutCreate, PayoutResponse
from src.core.services.payout_service import PayoutService
from src.db.models.payout import PayoutRequest
from src.db.repositories.payout_repo import PayoutRepository

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Payouts"])


# ─── Helpers ──────────────────────────────────────────────────


async def _get_payout_or_404(
    payout_id: int,
    session: AsyncSession,
    current_user: CurrentUser,
) -> PayoutRequest:
    """
    Получить заявку на выплату по ID или вернуть 404.
    Проверяет что пользователь является владельцем заявки.
    """
    payout = await session.get(PayoutRequest, payout_id)
    if not payout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payout request not found",
        )

    # Проверка что пользователь — владелец заявки
    if payout.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied — not your payout request",
        )

    return payout


# ─── Endpoints ──────────────────────────────────────────────────


@router.get("/")
async def get_my_payouts(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[PayoutResponse]:
    """
    Получить список всех заявок на выплату текущего пользователя.

    Возвращает заявки в порядке создания (новые первыми).

    Args:
        current_user: Текущий авторизованный пользователь.
        session: Асинхронная сессия БД.

    Returns:
        list[PayoutResponse]: Список заявок пользователя.
    """
    repo = PayoutRepository(session)
    payouts = await repo.get_by_owner(current_user.id)

    return [PayoutResponse.model_validate(p) for p in payouts]


@router.get(
    "/{payout_id}",
    responses={404: {"description": "Payout not found"}, 403: {"description": "Access denied"}},
)
async def get_payout(
    payout_id: int,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PayoutResponse:
    """
    Получить детали конкретной заявки на выплату.

    Args:
        payout_id: ID заявки.
        current_user: Текущий авторизованный пользователь.
        session: Асинхронная сессия БД.

    Returns:
        PayoutResponse: Данные заявки.

    Raises:
        HTTPException 404: Заявка не найдена.
        HTTPException 403: Пользователь не является владельцем заявки.
    """
    payout = await _get_payout_or_404(payout_id, session, current_user)
    return PayoutResponse.model_validate(payout)


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "Amount below minimum or insufficient funds"},
        404: {"description": "User not found"},
        409: {"description": "Active payout request exists or data conflict"},
    },
)
async def create_payout(
    payout_data: PayoutCreate,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PayoutResponse:
    """
    Создать новую заявку на выплату.

    Доступно только владельцам каналов с положительным балансом earned_rub.
    Проверяет минимальную сумму выплаты и доступность средств.
    Статус заявки устанавливается в 'pending'.

    Args:
        payout_data: Данные для создания заявки.
        current_user: Текущий авторизованный пользователь.
        session: Асинхронная сессия БД.

    Returns:
        PayoutResponse: Созданная заявка.

    Raises:
        HTTPException 400: Сумма меньше минимальной или недостаточно средств.
        HTTPException 409: Уже есть активная заявка (pending/processing).
    """
    payout_service = PayoutService()
    try:
        payout = await payout_service.create_payout(
            session, current_user.id, payout_data.amount
        )
    except ValueError as e:
        error_msg = str(e)
        if "Подождите" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "payout_cooldown", "message": error_msg},
            ) from e
        elif "velocity" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "velocity_exceeded", "message": error_msg},
            ) from e
        elif "Insufficient" in error_msg or "earned_rub" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "insufficient_funds", "message": error_msg},
            ) from e
        elif "активная" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "active_payout_exists", "message": error_msg},
            ) from e
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            ) from e

    # Set requisites from request (service creates with placeholder "payout_request")
    payout.requisites = payout_data.payment_details
    await session.flush()
    await session.refresh(payout)

    logger.info(f"Payout request {payout.id} created by user {current_user.id}")

    return PayoutResponse.model_validate(payout)
