"""
Парсер метрик Telegram каналов и групп через Telethon MTProto.

Ограничения Telegram API:
- Публичные каналы/группы — только через username
- ~30 req/мин до FloodWait
- Просмотры доступны только для последних ~100 постов канала
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

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

logger = logging.getLogger(__name__)


@dataclass
class ChatMetrics:
    """Результат парсинга одного чата."""

    username: str
    telegram_id: int
    title: str
    description: str
    chat_type: str  # channel | group | supergroup
    is_public: bool
    can_post: bool  # True = открытая группа без вступления

    subscribers: int
    avg_views: int
    max_views: int
    min_views: int
    posts_analyzed: int
    er: float  # avg_views / subscribers * 100

    post_frequency: float  # постов в день за 30 дней
    posts_last_30d: int

    error: str | None = None


class TelegramChatParser:
    """
    Парсер с rate limiting и FloodWait handling.
    Используй как async context manager:

        async with TelegramChatParser() as parser:
            metrics = await parser.parse_chat("durov")
    """

    # Пауза между запросами в секундах
    REQUEST_DELAY = 2.0
    # Сколько постов брать для расчёта avg_views
    POSTS_SAMPLE = 30
    # За сколько дней считать частоту публикаций
    FREQUENCY_DAYS = 30

    def __init__(self) -> None:
        self._client = TelegramClient(
            session="parser_session",
            api_id=settings.api_id,
            api_hash=settings.api_hash,
        )
        self._request_count = 0
        self._last_request_time = 0.0

    async def __aenter__(self) -> "TelegramChatParser":
        await self._client.start()
        return self

    async def __aexit__(self, *args) -> None:
        await self._client.disconnect()

    async def _rate_limit(self) -> None:
        """Пауза между запросами для соблюдения лимитов."""
        now = asyncio.get_event_loop().time()
        elapsed = now - self._last_request_time
        if elapsed < self.REQUEST_DELAY:
            await asyncio.sleep(self.REQUEST_DELAY - elapsed)
        self._last_request_time = asyncio.get_event_loop().time()
        self._request_count += 1

    async def parse_chat(self, username: str) -> ChatMetrics:
        """
        Собрать все метрики для одного чата.
        Возвращает ChatMetrics с полями error=None при успехе.
        """
        username = username.lstrip("@").lower()
        try:
            return await self._collect_metrics(username)
        except FloodWaitError as e:
            wait_sec = e.seconds + 5
            logger.warning(f"FloodWait {wait_sec}s для @{username}, жду...")
            await asyncio.sleep(wait_sec)
            # Повтор после ожидания
            try:
                return await self._collect_metrics(username)
            except Exception as retry_err:
                return self._error_result(username, str(retry_err))
        except (ChannelPrivateError, UsernameNotOccupiedError, UsernameInvalidError) as e:
            return self._error_result(username, f"Недоступен: {type(e).__name__}")
        except Exception as e:
            logger.error(f"Ошибка парсинга @{username}: {e}")
            return self._error_result(username, str(e)[:200])

    async def _collect_metrics(self, username: str) -> ChatMetrics:
        await self._rate_limit()

        # 1. Получить базовую информацию о чате
        entity = await self._client.get_entity(username)
        await self._rate_limit()

        # 2. Получить полную информацию (описание, настройки)
        full = await self._client(GetFullChannelRequest(entity))
        await self._rate_limit()

        # 3. Определить тип и доступность постинга
        chat_type, can_post, is_public = self._detect_chat_type(entity, full)

        subscribers = getattr(full.full_chat, "participants_count", 0) or 0
        description = getattr(full.full_chat, "about", "") or ""
        title = getattr(entity, "title", username)
        telegram_id = entity.id

        # 4. Собрать последние посты для расчёта охвата
        posts_data = await self._collect_posts_metrics(entity)
        await self._rate_limit()

        # 5. Считать частоту публикаций за 30 дней
        frequency, posts_30d = await self._collect_post_frequency(entity)

        # 6. Рассчитать ER
        er = 0.0
        if subscribers > 0 and posts_data["avg_views"] > 0:
            er = round(posts_data["avg_views"] / subscribers * 100, 2)

        return ChatMetrics(
            username=username,
            telegram_id=telegram_id,
            title=title,
            description=description,
            chat_type=chat_type,
            is_public=is_public,
            can_post=can_post,
            subscribers=subscribers,
            avg_views=posts_data["avg_views"],
            max_views=posts_data["max_views"],
            min_views=posts_data["min_views"],
            posts_analyzed=posts_data["count"],
            er=er,
            post_frequency=frequency,
            posts_last_30d=posts_30d,
        )

    def _detect_chat_type(
        self, entity: Channel | Chat, full: ChannelFull
    ) -> tuple[str, bool, bool]:
        """
        Определить тип чата и можно ли в него постить.
        can_post = True если это открытая группа (megagroup) без ограничений.
        """
        is_megagroup = getattr(entity, "megagroup", False)
        is_broadcast = getattr(entity, "broadcast", False)
        default_ban_rights = getattr(full.full_chat, "default_banned_rights", None)

        if is_broadcast:
            chat_type = "channel"
            can_post = False  # В каналы постит только владелец
        elif is_megagroup:
            chat_type = "supergroup"
            # can_post = True если нет запрета на отправку сообщений
            if default_ban_rights:
                can_post = not getattr(default_ban_rights, "send_messages", True)
            else:
                can_post = True
        else:
            chat_type = "group"
            can_post = True

        is_public = bool(getattr(entity, "username", None))
        return chat_type, can_post, is_public

    async def _collect_posts_metrics(self, entity: Channel | Chat) -> dict:
        """Собрать метрики просмотров по последним N постам."""
        views_list = []
        try:
            async for message in self._client.iter_messages(
                entity, limit=self.POSTS_SAMPLE
            ):
                if message.views and message.views > 0:
                    views_list.append(message.views)
        except Exception as e:
            logger.debug(f"Не удалось получить посты: {e}")

        if not views_list:
            return {"avg_views": 0, "max_views": 0, "min_views": 0, "count": 0}

        return {
            "avg_views": int(sum(views_list) / len(views_list)),
            "max_views": max(views_list),
            "min_views": min(views_list),
            "count": len(views_list),
        }

    async def _collect_post_frequency(
        self, entity: Channel | Chat
    ) -> tuple[float, int]:
        """
        Считает частоту публикаций за последние 30 дней.
        Возвращает (постов_в_день, всего_постов_за_30д).
        """
        since = datetime.now(tz=timezone.utc) - timedelta(days=self.FREQUENCY_DAYS)
        count = 0
        try:
            async for message in self._client.iter_messages(entity, offset_date=None):
                if message.date < since:
                    break
                if not message.action:  # только реальные посты, не служебные
                    count += 1
        except Exception as e:
            logger.debug(f"Ошибка при подсчёте частоты: {e}")

        frequency = round(count / self.FREQUENCY_DAYS, 2)
        return frequency, count

    @staticmethod
    def _error_result(username: str, error: str) -> ChatMetrics:
        return ChatMetrics(
            username=username,
            telegram_id=0,
            title=username,
            description="",
            chat_type="channel",
            is_public=True,
            can_post=False,
            subscribers=0,
            avg_views=0,
            max_views=0,
            min_views=0,
            posts_analyzed=0,
            er=0.0,
            post_frequency=0.0,
            posts_last_30d=0,
            error=error,
        )


async def parse_chats_batch(
    usernames: list[str],
    on_progress: callable | None = None,
) -> list[ChatMetrics]:
    """
    Парсит батч чатов с единым клиентом.
    on_progress(done, total) — callback для логирования прогресса.
    """
    results = []
    async with TelegramChatParser() as parser:
        for i, username in enumerate(usernames):
            metrics = await parser.parse_chat(username)
            results.append(metrics)
            if on_progress:
                on_progress(i + 1, len(usernames))
    return results
