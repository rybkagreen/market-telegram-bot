"""
Parser Celery tasks для обновления базы данных чатов.
"""

import asyncio
import logging
from typing import Any

from src.db.repositories.chat_repo import ChatData, ChatRepository
from src.db.session import async_session_factory
from src.tasks.celery_app import BaseTask, celery_app
from src.utils.telegram.parser import TelegramParser
from src.utils.telegram.tgstat_parser import POPULAR_TOPICS, TGStatParser
from src.utils.telegram.topic_classifier import classify_topic

logger = logging.getLogger(__name__)

# Поисковые запросы для парсинга Telegram
SEARCH_QUERIES = [
    "бизнес",
    "новости",
    "крипта",
    "инвестиции",
    "маркетинг",
    "it",
    "финансы",
    "спорт",
    "авто",
    "путешествия",
    "еда",
    "мода",
    "здоровье",
    "образование",
    "недвижимость",
    "startups",
    "technology",
    "crypto news",
    "business news",
    "trading",
    "forex",
    "stocks",
    "real estate",
    "travel blog",
    "food blog",
    "fitness",
    "lifestyle",
    "fashion",
    "beauty",
    "cars",
    "ai",
    "programming",
    "web development",
    "mobile apps",
    "gadgets",
    "science",
    "education",
    "online learning",
    "courses",
    "books",
    "movies",
    "music",
    "games",
    "entertainment",
]


async def _parse_and_save_chats(
    parser: TelegramParser,
    chat_repo: ChatRepository,
    query: str,
    limit: int = 50,
) -> int:
    """
    Распарсить и сохранить чаты по запросу.

    Args:
        parser: TelegramParser экземпляр.
        chat_repo: ChatRepository экземпляр.
        query: Поисковый запрос.
        limit: Максимальное количество результатов.

    Returns:
        Количество сохраненных чатов.
    """
    try:
        # Ищем чаты
        chat_infos = await parser.search_public_chats(query, limit=limit)

        if not chat_infos:
            logger.info(f"No chats found for query: {query}")
            return 0

        # Конвертируем в ChatData
        chat_data_list: list[ChatData] = []

        for chat_info in chat_infos:
            # Классифицируем тематику
            topic = classify_topic(chat_info.title, chat_info.description)

            chat_data = ChatData(
                telegram_id=chat_info.telegram_id,
                title=chat_info.title,
                username=chat_info.username,
                description=chat_info.description,
                member_count=chat_info.member_count,
                topic=topic,
                is_verified=chat_info.is_verified,
                is_scam=chat_info.is_scam,
                is_fake=chat_info.is_fake,
                is_broadcast=chat_info.is_broadcast,
                rating=7.0 if chat_info.is_verified else 5.0,
                avg_post_reach=None,
                posts_per_day=0.0,
            )
            chat_data_list.append(chat_data)

        # Сохраняем в БД
        saved_count = await chat_repo.upsert_batch(chat_data_list, update_existing=True)
        logger.info(f"Saved {saved_count} chats for query '{query}'")

        return saved_count

    except Exception as e:
        logger.error(f"Error parsing query '{query}': {e}")
        return 0


async def _parse_tgstat_and_save(
    tgstat_parser: TGStatParser,
    telegram_parser: TelegramParser,
    chat_repo: ChatRepository,
    topic: str,
) -> int:
    """
    Распарсить TGStat и сохранить чаты.

    Args:
        tgstat_parser: TGStatParser экземпляр.
        telegram_parser: TelegramParser экземпляр.
        chat_repo: ChatRepository экземпляр.
        topic: Тематика.

    Returns:
        Количество сохраненных чатов.
    """
    try:
        # Получаем username из TGStat
        usernames = await tgstat_parser.fetch_tgstat_catalog(topic, max_pages=3)

        if not usernames:
            logger.info(f"No usernames found for topic '{topic}' on TGStat")
            return 0

        # Валидируем через Telegram
        chat_details_list = await telegram_parser.batch_validate(usernames, semaphore_count=5)

        if not chat_details_list:
            logger.info(f"No valid chats found for topic '{topic}'")
            return 0

        # Конвертируем в ChatData
        chat_data_list: list[ChatData] = []

        for chat_details in chat_details_list:
            # Классифицируем тематику (может быть более точной)
            topic_classified = classify_topic(chat_details.title, chat_details.description)

            chat_data = ChatData(
                telegram_id=chat_details.telegram_id,
                title=chat_details.title,
                username=chat_details.username,
                description=chat_details.description,
                member_count=chat_details.member_count,
                topic=topic_classified,
                is_verified=chat_details.is_verified,
                is_scam=chat_details.is_scam,
                is_fake=chat_details.is_fake,
                is_broadcast=chat_details.is_broadcast,
                rating=chat_details.rating,
                avg_post_reach=chat_details.avg_post_reach,
                posts_per_day=chat_details.posts_per_day,
            )
            chat_data_list.append(chat_data)

        # Сохраняем в БД
        saved_count = await chat_repo.upsert_batch(chat_data_list, update_existing=True)
        logger.info(f"Saved {saved_count} chats from TGStat for topic '{topic}'")

        return saved_count

    except Exception as e:
        logger.error(f"Error parsing TGStat topic '{topic}': {e}")
        return 0


async def _refresh_chats_async() -> dict[str, Any]:
    """
    Асинхронная функция для обновления базы чатов.

    Returns:
        Статистика обновления.
    """
    stats = {
        "telegram_search": 0,
        "tgstat": 0,
        "total": 0,
        "errors": 0,
    }

    async with async_session_factory() as session:
        chat_repo = ChatRepository(session)

        # 1. Парсим через Telegram search
        async with TelegramParser() as parser:
            for query in SEARCH_QUERIES:
                try:
                    count = await _parse_and_save_chats(parser, chat_repo, query, limit=30)
                    stats["telegram_search"] += count
                    stats["total"] += count

                    # Задержка между запросами
                    await asyncio.sleep(1)

                except Exception as e:
                    logger.error(f"Error in Telegram search for '{query}': {e}")
                    stats["errors"] += 1

        # 2. Парсим через TGStat
        async with TGStatParser() as tgstat_parser, TelegramParser() as telegram_parser:
            for topic in POPULAR_TOPICS[:10]:  # Ограничиваем количество
                try:
                    count = await _parse_tgstat_and_save(
                        tgstat_parser, telegram_parser, chat_repo, topic
                    )
                    stats["tgstat"] += count
                    stats["total"] += count

                    # Задержка между запросами
                    await asyncio.sleep(2)

                except Exception as e:
                    logger.error(f"Error in TGStat parsing for '{topic}': {e}")
                    stats["errors"] += 1

    return stats


# Celery задача будет определена после создания celery_app
# Импортируем celery_app динамически чтобы избежать circular imports


@celery_app.task(bind=True, base=BaseTask, name="parser:refresh_chat_database")
def refresh_chat_database(self) -> dict[str, Any]:
    """
    Celery задача для обновления базы данных чатов.

    Запускается по расписанию (каждые 24 часа).
    Собирает данные из Telegram и TGStat.

    Returns:
        Статистика обновления.
    """
    logger.info("Starting chat database refresh...")

    try:
        stats = asyncio.run(_refresh_chats_async())

        logger.info(
            f"Chat database refresh completed. "
            f"Total: {stats['total']}, "
            f"Telegram: {stats['telegram_search']}, "
            f"TGStat: {stats['tgstat']}, "
            f"Errors: {stats['errors']}"
        )

        return stats

    except Exception as e:
        logger.error(f"Error in refresh_chat_database: {e}")
        return {"error": str(e)}


async def _validate_username_async(username: str) -> dict[str, Any] | None:
    """
    Асинхронная валидация username.

    Args:
        username: Username для проверки.

    Returns:
        ChatData или None.
    """
    async with TelegramParser() as parser:
        chat_details = await parser.resolve_and_validate(username)

        if not chat_details:
            return None

        async with async_session_factory() as session:
            chat_repo = ChatRepository(session)

            topic = classify_topic(chat_details.title, chat_details.description)

            from src.db.repositories.chat_repo import ChatData

            chat_data = ChatData(
                telegram_id=chat_details.telegram_id,
                title=chat_details.title,
                username=chat_details.username,
                description=chat_details.description,
                member_count=chat_details.member_count,
                topic=topic,
                is_verified=chat_details.is_verified,
                is_scam=chat_details.is_scam,
                is_fake=chat_details.is_fake,
                is_broadcast=chat_details.is_broadcast,
                rating=chat_details.rating,
                avg_post_reach=chat_details.avg_post_reach,
                posts_per_day=chat_details.posts_per_day,
            )

            await chat_repo.upsert_batch([chat_data], update_existing=True)

            return {"telegram_id": chat_details.telegram_id, "title": chat_details.title}


def validate_username(username: str) -> dict[str, Any] | None:
    """
    Проверить и сохранить информацию о канале.

    Args:
        username: Username канала (с @ или без).

    Returns:
        Информация о канале или None.
    """
    try:
        return asyncio.run(_validate_username_async(username))
    except Exception as e:
        logger.error(f"Error validating username {username}: {e}")
        return None


async def _update_chat_rating_async(chat_id: int) -> float | None:
    """
    Обновить рейтинг чата на основе активности.

    Args:
        chat_id: Telegram ID чата.

    Returns:
        Новый рейтинг или None.
    """
    async with TelegramParser() as parser:
        # Получаем информацию о чате
        entity = await parser.client.get_entity(chat_id)

        if not entity:
            return None

        # Вычисляем рейтинг на основе:
        # - количества участников
        # - наличия верификации
        # - активности (можно добавить позже)
        base_rating = 5.0

        if hasattr(entity, "verified") and entity.verified:
            base_rating += 3.0

        member_count = getattr(entity, "participants_count", 0)
        if member_count > 100000:
            base_rating += 2.0
        elif member_count > 10000:
            base_rating += 1.0
        elif member_count < 100:
            base_rating -= 2.0

        # Ограничиваем диапазон 0-10
        new_rating = max(0.0, min(10.0, base_rating))

        async with async_session_factory() as session:
            chat_repo = ChatRepository(session)
            await chat_repo.update_rating(chat_id, new_rating)

        return new_rating


def update_chat_rating(chat_id: int) -> float | None:
    """
    Обновить рейтинг чата.

    Args:
        chat_id: Telegram ID чата.

    Returns:
        Новый рейтинг или None.
    """
    try:
        return asyncio.run(_update_chat_rating_async(chat_id))
    except Exception as e:
        logger.error(f"Error updating rating for chat {chat_id}: {e}")
        return None
