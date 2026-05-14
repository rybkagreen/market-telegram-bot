"""Trustchannelbot admin verification (BL-107 / ФЗ-303).

Provides Protocol-based cross-SDK abstraction для ``get_chat_administrators``
+ ``get_chat`` access + lazy cache для @Trustchannelbot Telegram ID resolution.
Used by Phase B.4 channel-add helper BEFORE ``check_gates_for_channel_add``
invocation — result sets ``ChannelAddContext.is_blogger_registry_verified``.

Both python-telegram-bot (used в API context) и aiogram (used в bot/services/
Celery context) expose compatible interface — single helper works для обоих
via Protocol duck-typing.

Design ref: ``BL-107_DESIGN_2026-05-14.md`` @ ``38dbc94`` § 3 (Cross-SDK
Protocol) + § 4 (Lazy cache + env override strategy).
"""

import asyncio
import logging
from typing import Any, Protocol

from src.config.settings import settings

logger = logging.getLogger(__name__)

# Module-level cache (process lifetime, не survives restart). Both API workers
# (FastAPI) и Celery workers populate independently — same ID across all
# processes, cache populates lazily on first verify call per process.
_TRUSTCHANNELBOT_ID_CACHE: int | None = None
_TRUSTCHANNELBOT_CACHE_LOCK = asyncio.Lock()


class TrustchannelbotResolutionError(Exception):
    """Trustchannelbot ID не может быть resolved.

    Raised когда:
    - settings.rkn_trustchannelbot_id is None (no env override)
    - module cache empty
    - bot.get_chat(username) API call fails

    Phase B.4 channel-add helper catches this → returns GateResult с
    ``GateReason.SUBSCRIBER_COUNT_UNKNOWN`` (channel-add blocked, owner
    informed что verification temporarily unavailable).
    """


class TelegramAdminLister(Protocol):
    """Cross-SDK Protocol для Telegram Bot API access (BL-107).

    Compatible с ``aiogram.Bot`` и ``telegram.Bot`` (python-telegram-bot).
    Both expose:
    - ``get_chat_administrators(chat_id)`` → list с ``.user.id`` attribute
    - ``get_chat(chat_id_or_username)`` → object с ``.id`` attribute

    Duck-typing на returned objects — neither SDK forces concrete class hierarchy.
    """

    async def get_chat_administrators(self, chat_id: int | str) -> list[Any]: ...

    async def get_chat(self, chat_id: int | str) -> Any: ...


async def resolve_trustchannelbot_id(bot: TelegramAdminLister) -> int:
    """Returns Trustchannelbot Telegram numeric ID. Cached для process lifetime.

    Strategy (Phase A2 design Q5 locked):
    1. ``settings.rkn_trustchannelbot_id`` set → return directly (env override path)
    2. Module cache populated → return cache (fast path, no lock)
    3. Acquire lock, double-check cache, ``bot.get_chat(username)`` → ``chat.id``,
       store в cache, return

    Lock prevents concurrent calls during cold start from issuing duplicate
    ``get_chat`` API requests. Double-check inside lock handles benign race
    where second caller acquired lock после first populated cache.

    Raises:
        TrustchannelbotResolutionError: API call fails AND cache empty AND
            no env override. Caller (Phase B.4 channel-add helper) catches и
            translates к ``GateReason.SUBSCRIBER_COUNT_UNKNOWN``.
    """
    global _TRUSTCHANNELBOT_ID_CACHE

    # Step 1: env override path — production deploy может pin ID для skip API call entirely
    if settings.rkn_trustchannelbot_id is not None:
        return settings.rkn_trustchannelbot_id

    # Step 2: cache hit fast path
    if _TRUSTCHANNELBOT_ID_CACHE is not None:
        return _TRUSTCHANNELBOT_ID_CACHE

    # Step 3: cache miss — serialize concurrent first-callers behind lock
    async with _TRUSTCHANNELBOT_CACHE_LOCK:
        if _TRUSTCHANNELBOT_ID_CACHE is not None:
            return _TRUSTCHANNELBOT_ID_CACHE

        try:
            chat = await bot.get_chat(settings.rkn_trustchannelbot_username)
            chat_id: int = chat.id
        except Exception as exc:
            logger.exception(
                "Failed to resolve Trustchannelbot ID via %s",
                settings.rkn_trustchannelbot_username,
            )
            raise TrustchannelbotResolutionError(
                f"Cannot resolve {settings.rkn_trustchannelbot_username}: {exc}"
            ) from exc

        _TRUSTCHANNELBOT_ID_CACHE = chat_id
        logger.info(
            "Resolved Trustchannelbot ID: %s (%s)",
            chat_id,
            settings.rkn_trustchannelbot_username,
        )
        return chat_id


async def verify_trustchannelbot_admin(
    bot: TelegramAdminLister,
    chat_id: int | str,
) -> bool:
    """Returns True если @Trustchannelbot is admin of given channel.

    Phase B.4 channel-add helper invocation pattern::

        try:
            is_verified = await verify_trustchannelbot_admin(bot, channel.telegram_id)
        except TrustchannelbotResolutionError:
            # → return GateResult(reason_code=SUBSCRIBER_COUNT_UNKNOWN)
            ...
        channel_data = ChannelAddContext(..., is_blogger_registry_verified=is_verified)
        gates = await legal_compliance.check_gates_for_channel_add(user, channel_data)

    Failure semantics:
    - ``TrustchannelbotResolutionError`` → propagates (caller wraps в
      ``SUBSCRIBER_COUNT_UNKNOWN`` GateResult)
    - Empty admin list (channel not found, bot lacks permission, channel deleted)
      → returns ``False`` (no raise — treat как "Trustchannelbot не admin")
    - ``get_chat_administrators`` API exception → propagates (caller decides;
      typically same as resolution error path)

    Duck-typing на returned ``admin`` objects: requires ``.user.id`` access.
    Both python-telegram-bot и aiogram return objects shaped that way.
    ``getattr(admin, "user", None) is not None`` guards against unexpected
    object shapes — returns False rather than AttributeError.
    """
    trustchannelbot_id = await resolve_trustchannelbot_id(bot)
    admins = await bot.get_chat_administrators(chat_id)
    return any(
        getattr(admin, "user", None) is not None and admin.user.id == trustchannelbot_id
        for admin in admins
    )


def _reset_cache_for_testing() -> None:
    """Test-only helper для clearing module cache между tests.

    Not part of public API — name-mangled с leading underscore. pytest
    fixtures call this в ``setup``/``teardown`` to isolate cache state
    across test cases.
    """
    global _TRUSTCHANNELBOT_ID_CACHE
    _TRUSTCHANNELBOT_ID_CACHE = None
