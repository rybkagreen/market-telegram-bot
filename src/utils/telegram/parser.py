"""
Telegram Parser для поиска и валидации публичных чатов.
Использует Telethon (User API) для поиска каналов и чатов.
"""

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC
from typing import Any

from telethon import TelegramClient
from telethon.errors import (
    ChannelInvalidError,
    ChannelPrivateError,
    FloodWaitError,
    UsernameInvalidError,
    UsernameNotOccupiedError,
)
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.types import (
    Channel,
    Chat,
)

from src.config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class ChatInfo:
    """Информация о чате/канале."""

    telegram_id: int
    title: str
    username: str | None
    description: str | None
    member_count: int
    is_verified: bool
    is_scam: bool
    is_fake: bool
    is_broadcast: bool
    linked_chat_id: int | None = None
    can_view_participants: bool = False
    can_send_messages: bool = False


@dataclass
class ChatDetails:
    """Детальная информация о чате после полной проверки."""

    telegram_id: int
    title: str
    username: str | None
    description: str | None
    member_count: int
    topic: str | None
    is_verified: bool
    is_scam: bool
    is_fake: bool
    is_broadcast: bool
    is_active: bool
    rating: float
    avg_post_reach: int | None
    posts_per_day: float
    last_checked: float | None = None


@dataclass
class ChatFullInfo:
    """
    Унифицированная модель данных Telegram чата.
    Объединяет поля ChatInfo + ChatDetails + ChatMetrics.
    Используется во всех слоях: парсер → репозиторий → обработчик.
    """

    # Идентификация
    telegram_id: int
    username: str
    title: str
    description: str | None = None

    # Тип и доступность
    chat_type: str = "channel"  # channel | group | supergroup
    is_public: bool = True
    can_post: bool = False

    # Метаданные TGStat/Telegram
    is_verified: bool = False
    is_scam: bool = False
    is_fake: bool = False
    rating: float = 0.0

    # Метрики (заполняются при полном парсинге)
    subscribers: int = 0
    avg_views: int = 0
    max_views: int = 0
    min_views: int = 0
    posts_analyzed: int = 0
    er: float = 0.0
    post_frequency: float = 0.0  # постов в день за 30 дней
    posts_last_30d: int = 0

    # Статус парсинга
    error: str | None = None

    @classmethod
    def from_chat_info(cls, info: ChatInfo) -> "ChatFullInfo":
        """Конвертер из ChatInfo (для обратной совместимости)."""
        return cls(
            telegram_id=info.telegram_id,
            username=info.username or "",
            title=info.title,
            description=info.description,
            is_verified=info.is_verified,
            is_scam=info.is_scam,
            is_fake=info.is_fake,
            subscribers=info.member_count,
        )

    @classmethod
    def from_chat_details(cls, details: ChatDetails) -> "ChatFullInfo":
        """Конвертер из ChatDetails (для обратной совместимости)."""
        return cls(
            telegram_id=details.telegram_id,
            username=details.username or "",
            title=details.title,
            description=details.description,
            is_verified=details.is_verified,
            is_scam=details.is_scam,
            is_fake=details.is_fake,
            rating=details.rating,
            subscribers=details.member_count,
            avg_views=details.avg_post_reach or 0,
            post_frequency=details.posts_per_day,
        )


class TelegramParser:
    """
    Парсер Telegram для поиска и валидации публичных чатов.

    Использование:
        parser = TelegramParser()
        await parser.start()
        chats = await parser.search_public_chats("бизнес", limit=50)
        await parser.stop()
    """

    def __init__(self) -> None:
        """Инициализация парсера."""
        self._client: TelegramClient | None = None
        self._is_started = False

    async def start(self) -> None:
        """
        Запустить клиент Telethon.

        Raises:
            RuntimeError: Если клиент уже запущен.
        """
        if self._is_started:
            raise RuntimeError("Parser already started")

        self._client = TelegramClient(
            "market_bot_parser",
            settings.api_id,
            settings.api_hash,
        )

        await self._client.start(bot_token=settings.bot_token)
        self._is_started = True
        logger.info("Telegram parser started")

    async def stop(self) -> None:
        """
        Остановить клиент Telethon.
        """
        if self._client and self._is_started:
            await self._client.disconnect()
            self._is_started = False
            logger.info("Telegram parser stopped")

    async def __aenter__(self) -> "TelegramParser":
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: Any
    ) -> None:
        """Async context manager exit."""
        await self.stop()

    @property
    def client(self) -> TelegramClient:
        """Получить клиент Telethon."""
        if not self._client or not self._is_started:
            raise RuntimeError("Parser not started. Call start() first.")
        return self._client

    async def search_public_chats(
        self,
        query: str,
        limit: int = 50,
    ) -> list[ChatInfo]:
        """
        Искать публичные каналы по запросу.

        Args:
            query: Поисковый запрос (например, "бизнес", "новости").
            limit: Максимальное количество результатов.

        Returns:
            Список найденных чатов.
        """
        results: list[ChatInfo] = []

        try:
            # Поиск через Telegram
            search_results = await self.client.get_entity(query)

            if isinstance(search_results, list):
                entities = search_results[:limit]
            else:
                entities = [search_results]

            for entity in entities:
                chat_info = await self._process_entity(entity)
                if chat_info:
                    results.append(chat_info)

        except FloodWaitError as e:
            logger.warning(f"FloodWait: {e.seconds} seconds")
            await asyncio.sleep(e.seconds + 5)
        except Exception as e:
            logger.error(f"Error searching for '{query}': {e}")

        return results

    async def resolve_and_validate(self, username: str) -> ChatDetails | None:
        """
        Разрешить username и полностью проверить чат.

        Args:
            username: Username канала (например, "business_news").

        Returns:
            ChatDetails или None если чат не подходит.
        """
        try:
            # Убираем @ если есть
            username = username.lstrip("@")

            # Получаем entity
            entity = await self.client.get_entity(username)

            if not isinstance(entity, Channel):
                logger.warning(f"{username} is not a channel")
                return None

            # Проверка на restrictions
            if entity.restricted:
                logger.warning(f"{username} is restricted")
                return None

            # Проверка что это канал (не группа и не пользователь)
            if not entity.broadcast:
                logger.info(f"{username} is not a broadcast channel")

            # Получаем полную информацию
            full_channel = await self.client(GetFullChannelRequest(entity))

            return await self._create_chat_details(entity, full_channel)

        except (ChannelInvalidError, ChannelPrivateError):
            logger.warning(f"Channel {username} is invalid or private")
            return None
        except FloodWaitError as e:
            logger.warning(f"FloodWait for {username}: {e.seconds}s")
            await asyncio.sleep(e.seconds + 5)
            return None
        except Exception as e:
            logger.error(f"Error resolving {username}: {e}")
            return None

    async def batch_validate(
        self,
        usernames: list[str],
        semaphore_count: int = 10,
    ) -> list[ChatDetails]:
        """
        Пакетная проверка списка username.

        Args:
            usernames: Список username для проверки.
            semaphore_count: Количество одновременных запросов.

        Returns:
            Список валидных ChatDetails.
        """
        semaphore = asyncio.Semaphore(semaphore_count)
        results: list[ChatDetails] = []

        async def validate_with_semaphore(username: str) -> None:
            async with semaphore:
                result = await self.resolve_and_validate(username)
                if result:
                    results.append(result)
                # Небольшая задержка между запросами
                await asyncio.sleep(0.5)

        tasks = [validate_with_semaphore(username) for username in usernames]
        await asyncio.gather(*tasks, return_exceptions=True)

        return results

    async def _process_entity(self, entity: Any) -> ChatInfo | None:
        """
        Обработать entity и вернуть ChatInfo.

        Args:
            entity: Telegram entity.

        Returns:
            ChatInfo или None.
        """
        if not isinstance(entity, Channel):
            return None

        # Проверка что канал публичный
        if not entity.username:
            logger.debug(f"Channel {entity.title} is private (no username)")
            return None

        try:
            full_channel = await self.client(GetFullChannelRequest(entity))

            return ChatInfo(
                telegram_id=entity.id,
                title=entity.title,
                username=entity.username,
                description=getattr(full_channel.full_chat, "about", None),
                member_count=getattr(full_channel.full_chat, "participants_count", 0),
                is_verified=entity.verified,
                is_scam=entity.scam,
                is_fake=entity.fake,
                is_broadcast=entity.broadcast,
                linked_chat_id=getattr(full_channel.full_chat, "linked_chat_id", None),
                can_view_participants=True,
                can_send_messages=getattr(full_channel.full_chat, "participants_admin_rights", None)
                is None,
            )

        except Exception as e:
            logger.error(f"Error processing entity {entity.title}: {e}")
            return None

    async def _create_chat_details(
        self,
        entity: Channel,
        full_channel: GetFullChannelRequest,
    ) -> ChatDetails:
        """
        Создать ChatDetails из entity и полной информации.

        Args:
            entity: Channel entity.
            full_channel: Полная информация о канале.

        Returns:
            ChatDetails.
        """
        from datetime import datetime

        full_chat = full_channel.full_chat

        # Базовая валидация
        is_active = (
            not entity.restricted
            and not entity.scam
            and not entity.fake
            and getattr(full_chat, "participants_count", 0) >= 100
        )

        return ChatDetails(
            telegram_id=entity.id,
            title=entity.title,
            username=entity.username,
            description=getattr(full_chat, "about", None),
            member_count=getattr(full_chat, "participants_count", 0),
            topic=None,  # Будет определена в topic_classifier
            is_verified=entity.verified,
            is_scam=entity.scam,
            is_fake=entity.fake,
            is_broadcast=entity.broadcast,
            is_active=is_active,
            rating=5.0,  # Default rating
            avg_post_reach=None,  # Может быть обновлен позже
            posts_per_day=0.0,  # Может быть обновлен позже
            last_checked=datetime.now(tz=UTC).timestamp(),
        )

    async def get_chat_members_count(self, chat_id: int) -> int:
        """
        Получить количество участников чата.

        Args:
            chat_id: Telegram ID чата.

        Returns:
            Количество участников.
        """
        try:
            entity = await self.client.get_entity(chat_id)
            match entity:
                case Channel() | Chat():
                    return getattr(entity, "participants_count", 0)
        except Exception as e:
            logger.error(f"Error getting members count for {chat_id}: {e}")
        return 0

    # ──────────────────────────────────────────────────────
    # Методы сбора метрик (из TelegramChatParser)
    # ──────────────────────────────────────────────────────

    # Константы для метрик
    POSTS_SAMPLE: int = 30  # постов для расчёта avg_views
    FREQUENCY_DAYS: int = 30  # дней для расчёта частоты публикаций
    REQUEST_DELAY: float = 2.0  # секунд между запросами

    async def parse_chat_metrics(self, username: str) -> ChatFullInfo:
        """
        Собрать полные метрики чата: подписчики, просмотры, ER, частота.
        Включает FloodWait handling и retry логику.
        Заменяет TelegramChatParser.parse_chat().

        Args:
            username: Username канала (с @ или без).

        Returns:
            ChatFullInfo с метриками или error полем.
        """
        username = username.lstrip("@").lower()
        try:
            return await self._collect_full_metrics(username)
        except FloodWaitError as e:
            wait_sec = e.seconds + 5
            logger.warning(f"FloodWait {wait_sec}s для @{username}, жду...")
            await asyncio.sleep(wait_sec)
            try:
                return await self._collect_full_metrics(username)
            except Exception as retry_err:
                return self._error_result(username, str(retry_err))
        except (ChannelPrivateError, UsernameNotOccupiedError, UsernameInvalidError) as e:
            return self._error_result(username, f"Недоступен: {type(e).__name__}")
        except Exception as e:
            logger.error(f"Ошибка парсинга @{username}: {e}")
            return self._error_result(username, str(e)[:200])

    async def _collect_full_metrics(self, username: str) -> ChatFullInfo:
        """Внутренний метод: собрать все данные для одного чата."""
        await self._rate_limit()
        entity = await self.client.get_entity(username)
        await self._rate_limit()

        full = await self.client(GetFullChannelRequest(entity))
        await self._rate_limit()

        chat_type, can_post, is_public = self._detect_chat_type(entity, full)
        subscribers = getattr(full.full_chat, "participants_count", 0) or 0
        description = getattr(full.full_chat, "about", "") or ""
        title = getattr(entity, "title", username)
        telegram_id = entity.id

        posts_data = await self._collect_posts_metrics(entity)
        await self._rate_limit()
        frequency, posts_30d = await self._collect_post_frequency(entity)

        er = 0.0
        if subscribers > 0 and posts_data["avg_views"] > 0:
            er = round(posts_data["avg_views"] / subscribers * 100, 2)

        return ChatFullInfo(
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

    async def _rate_limit(self) -> None:
        """Пауза между запросами для соблюдения лимитов Telegram API."""
        now = asyncio.get_event_loop().time()
        elapsed = now - getattr(self, "_last_request_time", 0.0)
        if elapsed < self.REQUEST_DELAY:
            await asyncio.sleep(self.REQUEST_DELAY - elapsed)
        self._last_request_time = asyncio.get_event_loop().time()

    def _detect_chat_type(self, entity: Channel | Chat, full: Any) -> tuple[str, bool, bool]:
        """
        Определить тип чата и возможность постинга.

        Args:
            entity: Channel или Chat entity.
            full: Полная информация о канале.

        Returns:
            Кортеж (chat_type, can_post, is_public).
        """
        is_megagroup = getattr(entity, "megagroup", False)
        is_broadcast = getattr(entity, "broadcast", False)
        default_ban_rights = getattr(full.full_chat, "default_banned_rights", None)

        if is_broadcast:
            chat_type, can_post = "channel", False
        elif is_megagroup:
            chat_type = "supergroup"
            can_post = (
                not getattr(default_ban_rights, "send_messages", True)
                if default_ban_rights
                else True
            )
        else:
            chat_type, can_post = "group", True

        is_public = bool(getattr(entity, "username", None))
        return chat_type, can_post, is_public

    async def _collect_posts_metrics(self, entity: Channel | Chat) -> dict:
        """
        Собрать метрики просмотров по последним N постам.

        Args:
            entity: Channel или Chat entity.

        Returns:
            Dict с полями avg_views, max_views, min_views, count.
        """
        views_list = []
        try:
            async for message in self.client.iter_messages(entity, limit=self.POSTS_SAMPLE):
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

    async def _collect_post_frequency(self, entity: Channel | Chat) -> tuple[float, int]:
        """
        Частота публикаций за последние 30 дней.

        Args:
            entity: Channel или Chat entity.

        Returns:
            Кортеж (posts_per_day, total_posts_30d).
        """
        from datetime import datetime, timedelta

        since = datetime.now(tz=UTC) - timedelta(days=self.FREQUENCY_DAYS)
        count = 0
        try:
            async for message in self.client.iter_messages(entity):
                if message.date < since:
                    break
                if not message.action:
                    count += 1
        except Exception as e:
            logger.debug(f"Ошибка подсчёта частоты: {e}")
        return round(count / self.FREQUENCY_DAYS, 2), count

    async def parse_chats_batch(
        self,
        usernames: list[str],
        on_progress: Callable[[int, int], None] | None = None,
    ) -> list[ChatFullInfo]:
        """
        Парсить батч чатов через единый клиент.
        Заменяет parse_chats_batch() из chat_parser.py.

        Args:
            usernames: Список username для парсинга.
            on_progress: Callback(done, total) для логирования.

        Returns:
            Список ChatFullInfo.
        """
        results = []
        for i, username in enumerate(usernames):
            result = await self.parse_chat_metrics(username)
            results.append(result)
            if on_progress:
                on_progress(i + 1, len(usernames))
        return results

    @staticmethod
    def _error_result(username: str, error: str) -> ChatFullInfo:
        """Создать ChatFullInfo с ошибкой."""
        return ChatFullInfo(
            username=username,
            telegram_id=0,
            title=username,
            error=error,
        )
