"""
DEPRECATED: Этот файл устарел.

Используй src.utils.telegram.parser.TelegramParser.parse_chat_metrics()

Оставлен для обратной совместимости. Будет удалён в следующем спринте.
"""
from __future__ import annotations

import warnings

warnings.warn(
    "chat_parser.py устарел. Используй TelegramParser.parse_chat_metrics()",
    DeprecationWarning,
    stacklevel=2,
)

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from telethon import TelegramClient
from telethon.errors import (
    ChannelPrivateError,
    FloodWaitError,
    UsernameInvalidError,
    UsernameNotOccupiedError,
)
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.types import Channel, ChannelFull, Chat

from src.config.settings import settings

# Импортируем новые классы для обратной совместимости
from src.utils.telegram.parser import ChatFullInfo as ChatMetrics  # noqa: F401
from src.utils.telegram.parser import TelegramParser

logger = logging.getLogger(__name__)


class TelegramChatParser:
    """
    Устаревший класс. Используй TelegramParser напрямую.

    Оставлен для обратной совместимости.
    """

    async def __aenter__(self) -> "TelegramChatParser":
        warnings.warn(
            "TelegramChatParser устарел, используй TelegramParser",
            DeprecationWarning,
            stacklevel=2,
        )
        self._parser = TelegramParser()
        await self._parser.start()
        return self

    async def __aexit__(self, *args) -> None:
        await self._parser.stop()

    async def parse_chat(self, username: str) -> ChatMetrics:
        """Прокси для TelegramParser.parse_chat_metrics()."""
        warnings.warn(
            "TelegramChatParser.parse_chat устарел, используй TelegramParser.parse_chat_metrics()",
            DeprecationWarning,
            stacklevel=2,
        )
        return await self._parser.parse_chat_metrics(username)


async def parse_chats_batch(
    usernames: list[str],
    on_progress: callable | None = None,
) -> list[ChatMetrics]:
    """
    Прокси для TelegramParser.parse_chats_batch().

    Устарел, используй TelegramParser напрямую.
    """
    warnings.warn(
        "parse_chats_batch устарел, используй TelegramParser.parse_chats_batch()",
        DeprecationWarning,
        stacklevel=2,
    )
    async with TelegramParser() as parser:
        return await parser.parse_chats_batch(usernames, on_progress)
