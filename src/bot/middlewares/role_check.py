"""RoleCheckMiddleware for user role and block checks."""

import logging
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy import select

from src.db.models.reputation_score import ReputationScore
from src.db.models.user import User

logger = logging.getLogger(__name__)


class RoleCheckMiddleware(BaseMiddleware):
    """Middleware для проверки роли и блокировок пользователя."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        event_from_user = data.get("event_from_user")
        user_id = event_from_user.id if event_from_user else None
        if not user_id:
            return await handler(event, data)

        session = data.get("session")
        if not session:
            return await handler(event, data)

        user_result = await session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            return await handler(event, data)

        score_result = await session.execute(
            select(ReputationScore).where(ReputationScore.user_id == user.id)
        )
        score = score_result.scalar_one_or_none()

        if not score:
            return await handler(event, data)

        role = user.current_role
        now = datetime.utcnow()
        bot = data.get("bot")

        if (
            role in ("advertiser", "both")
            and score.is_advertiser_blocked
            and score.advertiser_blocked_until
            and score.advertiser_blocked_until > now
        ):
            if bot:
                try:
                    await bot.send_message(user_id, f"🚫 Аккаунт заблокирован до {score.advertiser_blocked_until.strftime('%Y-%m-%d %H:%M')}.")
                except Exception as e:
                    logger.warning(f"Cannot send blocked account message to {user_id}: {e}")
            return None

        if (
            role in ("owner", "both")
            and score.is_owner_blocked
            and score.owner_blocked_until
            and score.owner_blocked_until > now
        ):
            if bot:
                try:
                    await bot.send_message(user_id, f"🚫 Аккаунт заблокирован до {score.owner_blocked_until.strftime('%Y-%m-%d %H:%M')}.")
                except Exception as e:
                    logger.warning(f"Cannot send blocked account message to {user_id}: {e}")
            return None

        return await handler(event, data)
