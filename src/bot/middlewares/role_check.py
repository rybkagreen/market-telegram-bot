"""RoleCheckMiddleware for user role and block checks."""

import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy import select

from src.db.models.reputation_score import ReputationScore
from src.db.models.user import User

logger = logging.getLogger(__name__)


async def _notify_blocked(bot: Any, user_id: int, blocked_until: datetime) -> None:
    """Send a block notification to the user, suppressing send errors."""
    if not bot:
        return
    try:
        await bot.send_message(
            user_id,
            f"🚫 Аккаунт заблокирован до {blocked_until.strftime('%Y-%m-%d %H:%M')}.",
        )
    except Exception as e:
        logger.warning(f"Cannot send blocked account message to {user_id}: {e}")


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

        user_result = await session.execute(select(User).where(User.telegram_id == user_id))
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
        now = datetime.now(UTC)
        bot = data.get("bot")

        advertiser_active = role in ("advertiser", "both")
        if (
            advertiser_active
            and score.is_advertiser_blocked
            and score.advertiser_blocked_until
            and score.advertiser_blocked_until > now
        ):
            await _notify_blocked(bot, user_id, score.advertiser_blocked_until)
            return None

        owner_active = role in ("owner", "both")
        if (
            owner_active
            and score.is_owner_blocked
            and score.owner_blocked_until
            and score.owner_blocked_until > now
        ):
            await _notify_blocked(bot, user_id, score.owner_blocked_until)
            return None

        return await handler(event, data)
