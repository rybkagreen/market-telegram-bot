"""
FastAPI router для управления заявками на выплату (Payouts).

Endpoints:
  GET  /api/payouts/         — список заявок текущего пользователя
  POST /api/payouts/         — создать заявку на выплату
  GET  /api/payouts/{id}     — детали заявки
"""

import logging
import uuid
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user_from_web_portal, get_db_session
from src.api.schemas.payout import PayoutCreate, PayoutResponse, PayoutStatus
from src.constants.payments import MIN_PAYOUT, PAYOUT_FEE_RATE
from src.db.models.payout import IDEMPOTENCY_KEY_CONSTRAINT_NAME, PayoutRequest
from src.db.models.user import User
from src.db.repositories.payout_repo import PayoutRepository
from src.db.repositories.user_repo import UserRepository
from src.utils.db_errors import extract_constraint_name

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Payouts"])


# ─── Helpers ──────────────────────────────────────────────────


async def _get_payout_or_404(
    payout_id: int,
    session: AsyncSession,
    current_user: User,
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
    current_user: Annotated[User, Depends(get_current_user_from_web_portal)],
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
    current_user: Annotated[User, Depends(get_current_user_from_web_portal)],
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
    current_user: Annotated[User, Depends(get_current_user_from_web_portal)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    x_idempotency_key: Annotated[str | None, Header(alias="X-Idempotency-Key")] = None,
) -> PayoutResponse:
    """
    Создать новую заявку на выплату.

    Доступно только владельцам каналов с положительным балансом earned_rub.
    Проверяет минимальную сумму выплаты и доступность средств.
    Статус заявки устанавливается в 'pending'.

    5b.7b idempotency (Marina Q3=(а), Q4=(а), Q5=(б)):
    клиент опционально передаёт ``X-Idempotency-Key`` header → server
    собирает ключ ``payout_request:owner={user_id}:nonce={header|uuid}``.
    EXISTS-check fast-path даёт идемпотентный re-read; race-past-EXISTS на
    UNIQUE(idempotency_key) ловится IntegrityError-handler'ом, который
    отличает наш constraint от прочих (по имени) и пропускает другие
    constraint violations наружу.

    Args:
        payout_data: Данные для создания заявки.
        current_user: Текущий авторизованный пользователь.
        session: Асинхронная сессия БД.
        x_idempotency_key: Опциональный header для дедупликации запросов.

    Returns:
        PayoutResponse: Созданная (или уже существующая идемпотентная) заявка.

    Raises:
        HTTPException 400: Сумма меньше минимальной или недостаточно средств.
        HTTPException 409: Уже есть активная заявка (pending/processing).
    """
    # Проверка минимальной суммы
    if payout_data.amount < MIN_PAYOUT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Minimum payout amount is {MIN_PAYOUT} RUB",
        )

    # Проверка что у пользователя нет активной заявки
    payout_repo = PayoutRepository(session)
    existing_payout = await payout_repo.get_active_for_owner(current_user.id)
    if existing_payout:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Active payout request exists (status: {existing_payout.status.value})",
        )

    # Проверка баланса пользователя
    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(current_user.id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.earned_rub < payout_data.amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient funds. Available: {user.earned_rub} RUB, Requested: {payout_data.amount} RUB",
        )

    # 5b.7b: idempotency key — header || server-side UUID4 fallback.
    idempotency_key = f"payout_request:owner={current_user.id}:nonce=" + (
        x_idempotency_key or uuid.uuid4().hex
    )

    # 5b.7b: EXISTS-check fast path — same key → idempotent re-read.
    existing = await session.execute(
        select(PayoutRequest).where(PayoutRequest.idempotency_key == idempotency_key)
    )
    if (existing_idempotent := existing.scalar_one_or_none()) is not None:
        return PayoutResponse.model_validate(existing_idempotent)

    # Расчёт комиссии и итоговой суммы
    fee_amount = (payout_data.amount * PAYOUT_FEE_RATE).quantize(Decimal("0.01"))
    net_amount = payout_data.amount - fee_amount

    # Создаём заявку
    payout = PayoutRequest(
        owner_id=current_user.id,
        gross_amount=payout_data.amount,
        fee_amount=fee_amount,
        net_amount=net_amount,
        requisites=payout_data.payment_details,
        status=PayoutStatus.pending,
        idempotency_key=idempotency_key,
    )

    session.add(payout)
    # 5b.7b CL-1: flush() (NOT commit()) — get_db_session autocommits on
    # handler success. flush() surfaces IntegrityError synchronously without
    # committing, so the rollback below leaves the session clean for re-read.
    # Mirrors 5b.7a O.4 bot-handler fix.
    try:
        await session.flush()
    except IntegrityError as e:
        await session.rollback()
        # Strict-distinguish (Marina Q5=(б)): only race-past-EXISTS on the
        # idempotency_key UNIQUE constraint is a recoverable idempotent
        # collision; other IntegrityErrors propagate so callers see the real
        # cause instead of a misleading idempotent-replay response.
        if extract_constraint_name(e) == IDEMPOTENCY_KEY_CONSTRAINT_NAME:
            existing = await session.execute(
                select(PayoutRequest).where(PayoutRequest.idempotency_key == idempotency_key)
            )
            return PayoutResponse.model_validate(existing.scalar_one())
        raise
    await session.refresh(payout)

    logger.info(
        f"Payout request {payout.id} created by user {current_user.id} "
        f"(idempotency_key={idempotency_key})"
    )

    return PayoutResponse.model_validate(payout)
