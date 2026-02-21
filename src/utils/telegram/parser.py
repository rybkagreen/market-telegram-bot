"""
Telegram Parser для поиска и валидации публичных чатов.
Использует Telethon (User API) для поиска каналов и чатов.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC

from telethon import TelegramClient
from telethon.errors import (
    ChannelInvalidError,
    ChannelPrivateError,
    FloodWaitError,
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

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
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

    async def _process_entity(self, entity) -> ChatInfo | None:
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
                can_send_messages=getattr(full_channel.full_chat, "participants_admin_rights", None) is None,
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
            if isinstance(entity, (Channel, Chat)):
                return getattr(entity, "participants_count", 0)
        except Exception as e:
            logger.error(f"Error getting members count for {chat_id}: {e}")
        return 0
