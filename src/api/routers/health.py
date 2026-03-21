"""
Health check API endpoints.
S-13: Базовая проверка сервиса + инварианты балансов platform_account.
"""

import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Header, HTTPException

from src.db.repositories.platform_account_repo import PlatformAccountRepository
from src.db.repositories.payout_repo import PayoutRepository
from src.db.repositories.placement_request_repo import PlacementRequestRepository
from src.db.repositories.user_repo import UserRepository
from src.db.session import async_session_factory

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
    x_admin_key: str | None = Header(None, alias="X-Admin-Key"),
) -> dict[str, Any]:
    """
    Инварианты балансов platform_account.

    Только для admin — проверяет X-Admin-Key header.
    """
    # Проверка admin (упрощённая — в production использовать proper auth)
    if not x_admin_key:
        raise HTTPException(status_code=403, detail="Admin key required")

    discrepancies: list[str] = []

    async with async_session_factory() as session:
        # Получаем platform_account (singleton id=1)
        platform_repo = PlatformAccountRepository(session)
        platform = await platform_repo.get_platform_account()

        if not platform:
            return {
                "status": "error",
                "error": "PlatformAccount not found",
                "timestamp": datetime.now(UTC).isoformat(),
            }

        # Считаем SUM(balance_rub) FROM users
        user_repo = UserRepository(session)
        users_balance_sum = await user_repo.get_total_balance_sum()

        # Считаем SUM(earned_rub) FROM users
        users_earned_sum = await user_repo.get_total_earned_sum()

        # Считаем SUM(final_price) FROM placement_requests WHERE status='escrow'
        placement_repo = PlacementRequestRepository(session)
        db_escrow_actual = await placement_repo.get_total_escrow_sum()

        # Считаем SUM(gross_amount) FROM payouts WHERE status IN ('pending','processing')
        payout_repo = PayoutRepository(session)
        db_payout_actual = await payout_repo.get_pending_sum()

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
