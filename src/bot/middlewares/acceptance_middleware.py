"""AcceptanceMiddleware — blocks bot interaction until user accepts current rules.

Activates re-acceptance loop at CONTRACT_TEMPLATE_VERSION mismatch (Промт 15.9):
once a user has a DB record but their latest signed acceptance template_version
differs from the current CONTRACT_TEMPLATE_VERSION constant (or no acceptance
exists at all), every Telegram interaction is intercepted and replaced with a
prompt to (re-)accept.

Sub-stages (BL-037 fail-fast):
    10a. Extract user_id from event_from_user.
    10b. Open DB lookup; user exists? otherwise pass through to onboarding.
    10c. Run service.needs_accept_rules — if True, send accept prompt + block.
    10d. Otherwise pass through to handler.

Failure handling: needs_accept_rules raises (DB unavailable, etc.) → log and
pass through (fail-open). Surfaced finding for prod: fail-closed may be safer
once a real user base exists.

Exempt event patterns (always passed through, even when needs_accept is True):
- /start command — initial onboarding always allowed.
- terms:* callbacks — pre-platform-rules terms acceptance step.
- contract:accept_rules callback — the accept action itself.
"""

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message, TelegramObject
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.config.settings import settings
from src.core.services.contract_service import ContractService
from src.db.repositories.user_repo import UserRepository

logger = logging.getLogger(__name__)

ACCEPT_PROMPT_TEXT = (
    "📋 Платформа обновила правила. Чтобы продолжить пользоваться ботом, "
    "пожалуйста, примите актуальную редакцию."
)


def _accept_prompt_keyboard() -> InlineKeyboardMarkup:
    """Both fast in-bot accept and WebApp deep-link to mini_app /accept-rules."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text="✅ Принимаю правила",
        callback_data="contract:accept_rules",
    )
    if settings.web_portal_url:
        builder.button(
            text="🌐 Открыть в браузере",
            url=f"{settings.web_portal_url.rstrip('/')}/accept-rules",
        )
    builder.adjust(1)
    return builder.as_markup()


def _is_exempt_message(event: Message) -> bool:
    text = (event.text or "").strip()
    return text.startswith("/start")


def _is_exempt_callback(event: CallbackQuery) -> bool:
    data = event.data or ""
    return data == "contract:accept_rules" or data.startswith("terms:")


class AcceptanceMiddleware(BaseMiddleware):
    """Block bot interactions when user must (re-)accept current platform rules."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        # 10a — identify user
        event_from_user = data.get("event_from_user")
        telegram_id = event_from_user.id if event_from_user else None
        if telegram_id is None:
            return await handler(event, data)

        session = data.get("session")
        if session is None:
            return await handler(event, data)

        # 10b — DB user lookup; new users (no record yet) flow through to /start
        db_user = await UserRepository(session).get_by_telegram_id(telegram_id)
        if db_user is None:
            return await handler(event, data)

        # 10c — version-aware acceptance check (fail-open on errors)
        try:
            needs = await ContractService(session).needs_accept_rules(db_user.id)
        except Exception:
            logger.exception(
                "AcceptanceMiddleware: needs_accept_rules failed for user_id=%s — passing through",
                db_user.id,
            )
            return await handler(event, data)

        if not needs:
            return await handler(event, data)

        # Block path — but allow /start, terms:*, contract:accept_rules through
        if isinstance(event, Message) and _is_exempt_message(event):
            return await handler(event, data)
        if isinstance(event, CallbackQuery) and _is_exempt_callback(event):
            return await handler(event, data)

        # 10d (block) — surface accept prompt and stop the chain
        try:
            if isinstance(event, Message):
                await event.answer(
                    ACCEPT_PROMPT_TEXT,
                    reply_markup=_accept_prompt_keyboard(),
                )
            elif isinstance(event, CallbackQuery):
                await event.answer(
                    "Сначала примите обновлённые правила платформы.",
                    show_alert=True,
                )
                if isinstance(event.message, Message):
                    await event.message.answer(
                        ACCEPT_PROMPT_TEXT,
                        reply_markup=_accept_prompt_keyboard(),
                    )
        except Exception:
            logger.exception(
                "AcceptanceMiddleware: failed to send accept prompt for user_id=%s",
                db_user.id,
            )
        return None
