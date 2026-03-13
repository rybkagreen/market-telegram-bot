"""
Health check API endpoints.
S-13: Базовая проверка сервиса + инварианты балансов platform_account.
"""

import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db_session
from src.db.models.payout import Payout, PayoutStatus
from src.db.models.placement_request import PlacementRequest, PlacementStatus
from src.db.models.platform_account import PlatformAccount
from src.db.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health_check() -> dict[str, Any]:
    """
    Базовая проверка — сервис жив.

    Returns:
        {"status": "ok", "timestamp": "ISO datetime"}
    """
    return {
        "status": "ok",
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/balances")
async def health_balances(
    session: AsyncSession = Depends(get_db_session),
    x_admin_key: str | None = Header(None, alias="X-Admin-Key"),
) -> dict[str, Any]:
    """
    Инварианты балансов platform_account.

    Только для admin — проверяет X-Admin-Key header.

    Проверяет:
    - platform.escrow_reserved == SUM(final_price WHERE status='escrow')
    - platform.payout_reserved == SUM(gross_amount WHERE status IN ('pending','processing'))

    Returns:
        {
            "status": "ok | warning",
            "platform_account": {...},
            "users_balance_sum": ...,
            "users_earned_sum": ...,
            "invariants": {
                "escrow_match": true/false,
                "payout_match": true/false
            },
            "discrepancies": [...]
        }
    """
    # Проверка admin (упрощённая — в production использовать proper auth)
    if not x_admin_key:
        raise HTTPException(status_code=403, detail="Admin key required")

    discrepancies: list[str] = []

    # Получаем platform_account (singleton id=1)
    platform_stmt = select(PlatformAccount).where(PlatformAccount.id == 1)
    platform_result = await session.execute(platform_stmt)
    platform = platform_result.scalar_one_or_none()

    if not platform:
        return {
            "status": "error",
            "error": "PlatformAccount not found",
            "timestamp": datetime.now(UTC).isoformat(),
        }

    # Считаем SUM(balance_rub) FROM users
    balance_sum_stmt = select(func.coalesce(func.sum(User.balance_rub), 0))
    balance_sum_result = await session.execute(balance_sum_stmt)
    users_balance_sum = balance_sum_result.scalar_one() or Decimal("0")

    # Считаем SUM(earned_rub) FROM users
    earned_sum_stmt = select(func.coalesce(func.sum(User.earned_rub), 0))
    earned_sum_result = await session.execute(earned_sum_stmt)
    users_earned_sum = earned_sum_result.scalar_one() or Decimal("0")

    # Считаем SUM(final_price) FROM placement_requests WHERE status='escrow'
    escrow_stmt = select(func.coalesce(func.sum(PlacementRequest.final_price), 0)).where(
        PlacementRequest.status == PlacementStatus.ESCROW
    )
    escrow_result = await session.execute(escrow_stmt)
    db_escrow_actual = escrow_result.scalar_one() or Decimal("0")

    # Считаем SUM(gross_amount) FROM payouts WHERE status IN ('pending','processing')
    payout_stmt = select(func.coalesce(func.sum(Payout.gross_amount), 0)).where(
        Payout.status.in_([PayoutStatus.PENDING, PayoutStatus.PROCESSING])
    )
    payout_result = await session.execute(payout_stmt)
    db_payout_actual = payout_result.scalar_one() or Decimal("0")

    # Проверяем инварианты
    escrow_match = platform.escrow_reserved == db_escrow_actual
    payout_match = platform.payout_reserved == db_payout_actual

    if not escrow_match:
        discrepancies.append(
            f"Escrow mismatch: platform.escrow_reserved={platform.escrow_reserved} != "
            f"db_escrow_actual={db_escrow_actual}"
        )

    if not payout_match:
        discrepancies.append(
            f"Payout mismatch: platform.payout_reserved={platform.payout_reserved} != "
            f"db_payout_actual={db_payout_actual}"
        )

    status = "ok" if not discrepancies else "warning"

    return {
        "status": status,
        "timestamp": datetime.now(UTC).isoformat(),
        "platform_account": {
            "escrow_reserved": float(platform.escrow_reserved),
            "payout_reserved": float(platform.payout_reserved),
            "profit_accumulated": float(platform.profit_accumulated),
            "total_topups": float(platform.total_topups),
            "total_payouts": float(platform.total_payouts),
        },
        "users_balance_sum": float(users_balance_sum),
        "users_earned_sum": float(users_earned_sum),
        "db_escrow_actual": float(db_escrow_actual),
        "db_payout_actual": float(db_payout_actual),
        "invariants": {
            "escrow_match": escrow_match,
            "payout_match": payout_match,
        },
        "discrepancies": discrepancies,
    }
