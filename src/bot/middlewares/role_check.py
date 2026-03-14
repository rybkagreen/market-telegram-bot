"""
RoleCheckMiddleware for user role and block checks.
"""

from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy import select

from src.db.models.reputation_score import ReputationScore
from src.db.models.user import User


class RoleCheckMiddleware(BaseMiddleware):
    """
    Middleware для проверки роли и блокировок пользователя.

    Если пользователь заблокирован — отвечает сообщением и не вызывает handler.
    """

    async def __call__(
        self,
        handler: Callable,
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Awaitable:
        user_id = event.from_user.id if event.from_user else None
        if not user_id:
            return await handler(event, data)

        session = data.get("session")
        if not session:
            return await handler(event, data)

        # Get user and reputation score
        user = await session.get(User, user_id)
        if not user:
            return await handler(event, data)

        score_result = await session.execute(
            select(ReputationScore).where(ReputationScore.user_id == user_id)
        )
        score = score_result.scalar_one_or_none()

        if not score:
            return await handler(event, data)

        role = user.current_role
        now = datetime.utcnow()

        # Check advertiser block
        if role in ("advertiser", "both") and score.is_advertiser_blocked:
            if score.advertiser_blocked_until and score.advertiser_blocked_until > now:
                if hasattr(event, "answer") and callable(event.answer):
                    await event.answer(
                        f"🚫 Аккаунт заблокирован до {score.advertiser_blocked_until.strftime('%Y-%m-%d %H:%M')}."
                    )
                return

        # Check owner block
        if role in ("owner", "both") and score.is_owner_blocked:
            if score.owner_blocked_until and score.owner_blocked_until > now:
                if hasattr(event, "answer") and callable(event.answer):
                    await event.answer(
                        f"🚫 Аккаунт заблокирован до {score.owner_blocked_until.strftime('%Y-%m-%d %H:%M')}."
                    )
                return

        return await handler(event, data)
