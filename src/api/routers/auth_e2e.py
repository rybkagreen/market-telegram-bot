"""
E2E-only auth endpoint for Playwright tests.

Mounted ONLY when settings.environment == "testing".
Grants a JWT for an arbitrary telegram_id without Telegram signature check.

Never exposed in dev/prod builds — see src/api/main.py.
"""

import logging

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from src.api.auth_utils import create_jwt_token
from src.db.repositories.user_repo import UserRepository
from src.db.session import async_session_factory

logger = logging.getLogger(__name__)

router = APIRouter()


class E2ELoginRequest(BaseModel):
    telegram_id: int


class E2ELoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


@router.post("/e2e-login")
async def e2e_login(body: E2ELoginRequest) -> E2ELoginResponse:
    """Test-only login. Creates or fetches user by telegram_id, returns JWT."""
    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(body.telegram_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Test user with telegram_id={body.telegram_id} not found. Run seed_e2e first.",
            )

    plan_value = getattr(user.plan, "value", None) or str(user.plan)
    token = create_jwt_token(
        user_id=user.id,
        telegram_id=user.telegram_id,
        plan=plan_value,
    )
    logger.info("E2E login: telegram_id=%s, plan=%s", body.telegram_id, plan_value)

    return E2ELoginResponse(
        access_token=token,
        user={
            "id": user.id,
            "telegram_id": user.telegram_id,
            "username": user.username,
            "first_name": user.first_name,
            "plan": plan_value,
            "balance_rub": str(user.balance_rub),
            "ai_generations_used": user.ai_uses_count,
            "is_admin": getattr(user, "is_admin", False),
        },
    )
