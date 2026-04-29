"""Regression: AcceptanceMiddleware blocks user on DB error (fail-closed).

Промт 15.10 — middleware previously fail-open'd on needs_accept_rules
exceptions (silent pass-through). Per BL-039, pre-prod fail-open could let
a user transact without a valid acceptance record once a real user base
exists. This module locks in fail-closed behaviour: on any exception from
needs_accept_rules, the handler chain is short-circuited and the user is
shown a "technical issue, try again later" notice.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from src.bot.middlewares.acceptance_middleware import (
    ACCEPT_PROMPT_TEXT,
    TECHNICAL_ERROR_TEXT,
    AcceptanceMiddleware,
)

pytestmark = pytest.mark.asyncio


def _make_message_event() -> AsyncMock:
    event = AsyncMock()
    event.text = "/balance"
    return event


def _build_data(*, telegram_id: int, db_user) -> dict:
    user_repo_mock = AsyncMock()
    user_repo_mock.get_by_telegram_id = AsyncMock(return_value=db_user)

    event_from_user = AsyncMock()
    event_from_user.id = telegram_id

    return {
        "event_from_user": event_from_user,
        "session": AsyncMock(),  # session truthy; UserRepository is patched
    }


async def test_middleware_blocks_on_needs_accept_rules_exception() -> None:
    """When needs_accept_rules raises (DB error) — handler NOT called, user gets technical notice."""
    middleware = AcceptanceMiddleware()
    handler = AsyncMock()
    event = _make_message_event()

    db_user = AsyncMock()
    db_user.id = 42
    data = _build_data(telegram_id=999, db_user=db_user)

    with (
        patch(
            "src.bot.middlewares.acceptance_middleware.UserRepository.get_by_telegram_id",
            new=AsyncMock(return_value=db_user),
        ),
        patch(
            "src.bot.middlewares.acceptance_middleware.ContractService.needs_accept_rules",
            new=AsyncMock(side_effect=RuntimeError("simulated DB failure")),
        ),
        patch(
            "src.bot.middlewares.acceptance_middleware.isinstance",
            side_effect=lambda _obj, cls: cls.__name__ == "Message",
        ),
    ):
        result = await middleware(handler, event, data)

    handler.assert_not_called()
    assert result is None
    event.answer.assert_called_once()
    args, _ = event.answer.call_args
    assert args[0] == TECHNICAL_ERROR_TEXT


async def test_middleware_passes_through_when_needs_false() -> None:
    """needs_accept_rules returns False — handler called normally."""
    middleware = AcceptanceMiddleware()
    handler = AsyncMock(return_value="handled")
    event = _make_message_event()

    db_user = AsyncMock()
    db_user.id = 42
    data = _build_data(telegram_id=999, db_user=db_user)

    with (
        patch(
            "src.bot.middlewares.acceptance_middleware.UserRepository.get_by_telegram_id",
            new=AsyncMock(return_value=db_user),
        ),
        patch(
            "src.bot.middlewares.acceptance_middleware.ContractService.needs_accept_rules",
            new=AsyncMock(return_value=False),
        ),
    ):
        result = await middleware(handler, event, data)

    handler.assert_called_once_with(event, data)
    assert result == "handled"
    event.answer.assert_not_called()


async def test_middleware_blocks_when_needs_true_non_exempt() -> None:
    """needs_accept_rules returns True for non-exempt event — handler NOT called, accept prompt sent."""
    middleware = AcceptanceMiddleware()
    handler = AsyncMock()
    event = _make_message_event()
    event.text = "/balance"  # not /start, so not exempt

    db_user = AsyncMock()
    db_user.id = 42
    data = _build_data(telegram_id=999, db_user=db_user)

    with (
        patch(
            "src.bot.middlewares.acceptance_middleware.UserRepository.get_by_telegram_id",
            new=AsyncMock(return_value=db_user),
        ),
        patch(
            "src.bot.middlewares.acceptance_middleware.ContractService.needs_accept_rules",
            new=AsyncMock(return_value=True),
        ),
        patch(
            "src.bot.middlewares.acceptance_middleware.isinstance",
            side_effect=lambda _obj, cls: cls.__name__ == "Message",
        ),
        patch(
            "src.bot.middlewares.acceptance_middleware._accept_prompt_keyboard",
            return_value=None,
        ),
    ):
        result = await middleware(handler, event, data)

    handler.assert_not_called()
    assert result is None
    event.answer.assert_called_once()
    args, _ = event.answer.call_args
    assert args[0] == ACCEPT_PROMPT_TEXT
