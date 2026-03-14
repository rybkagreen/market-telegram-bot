"""
Middleware для проверки роли пользователя (advertiser/owner/both).
"""

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, TelegramObject

from src.core.services.reputation_service import ReputationService
from src.db.repositories.reputation_repo import ReputationRepo
from src.db.repositories.user_repo import UserRepository
from src.db.session import async_session_factory

logger = logging.getLogger(__name__)


class RoleCheckMiddleware(BaseMiddleware):
    """
    Middleware для проверки роли пользователя и блокировок.

    Проверяет:
    1. main:analytics — требует роль advertiser/both
    2. main:owner_analytics — требует роль owner/both
    3. reputation_service.check_blocked — проверка блокировки
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        callback = data.get("callback")
        if not isinstance(callback, CallbackQuery):
            return await handler(event, data)

        user = callback.from_user
        if user is None:
            return await handler(event, data)

        # Проверка callback_data
        callback_data = callback.data
        if not callback_data:
            return await handler(event, data)

        # Проверка блокировок через reputation_service
        async with async_session_factory() as session:
            user_repo = UserRepository(session)
            db_user = await user_repo.get_by_telegram_id(user.id)

            if db_user is None:
                await callback.answer("⛔ Пользователь не найден", show_alert=True)
                return

            # Проверка блокировок
            rep_repo = ReputationRepo(session)
            rep_service = ReputationService(session, rep_repo)

            # Проверка advertiser блокировки
            if db_user.current_role in ("advertiser", "both"):
                is_blocked = await rep_service.is_blocked(db_user.id, "advertiser")
                if is_blocked:
                    await callback.answer(
                        "⛔ Вы заблокированы как рекламодатель",
                        show_alert=True,
                    )
                    return

            # Проверка owner блокировки
            if db_user.current_role in ("owner", "both"):
                is_blocked = await rep_service.is_blocked(db_user.id, "owner")
                if is_blocked:
                    await callback.answer(
                        "⛔ Вы заблокированы как владелец канала",
                        show_alert=True,
                    )
                    return

        return await handler(event, data)
