"""
Parser Celery tasks для обновления базы данных чатов.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import date
from typing import Any

from src.db.models.analytics import ChatType
from src.db.repositories.chat_analytics import ChatAnalyticsRepository
from src.db.session import async_session_factory, get_session
from src.tasks.celery_app import BaseTask, celery_app
from src.utils.telegram.parser import POPULAR_TOPICS, TelegramParser
from src.utils.telegram.topic_classifier import classify_topic

logger = logging.getLogger(__name__)


@dataclass
class ChatParseData:
    """Данные чата для парсера."""

    telegram_id: int
    title: str
    username: str | None
    description: str | None
    member_count: int
    topic: str | None
    is_verified: bool = False
    is_scam: bool = False
    is_fake: bool = False
    rating: float = 5.0


# Поисковые запросы для парсинга Telegram (расширенный список ~150 запросов)
# Разбит по тематикам для равномерного распределения нагрузки
SEARCH_QUERIES = [
    # Бизнес и финансы (20)
    "бизнес",
    "бизнес новости",
    "бизнес идеи",
    "стартап",
    "стартапы россия",
    "инвестиции",
    "инвестиции для начинающих",
    "фондовый рынок",
    "трейдинг",
    "крипта",
    "криптовалюта",
    "биткоин",
    "ethereum",
    "defi",
    "nft",
    "финансы",
    "финансовая грамотность",
    "деньги",
    "заработок",
    "пассивный доход",
    # Маркетинг и продажи (15)
    "маркетинг",
    "digital маркетинг",
    "smm",
    "таргетинг",
    "контекстная реклама",
    "продажи",
    "продажи b2b",
    "продажи b2c",
    "переговоры",
    "клиенты",
    "бренд",
    "pr",
    "контент маркетинг",
    "email маркетинг",
    "лидогенерация",
    # IT и технологии (25)
    "it",
    "it новости",
    "программирование",
    "разработка",
    "веб разработка",
    "python",
    "javascript",
    "java",
    "golang",
    "rust",
    "ai",
    "искусственный интеллект",
    "машинное обучение",
    "ml",
    "data science",
    "big data",
    "аналитика данных",
    "devops",
    "cloud",
    "kubernetes",
    "docker",
    "микросервисы",
    "api",
    "mobile development",
    "ios разработка",
    "android разработка",
    "flutter",
    "react native",
    "frontend",
    "backend",
    # Недвижимость (10)
    "недвижимость",
    "недвижимость москва",
    "недвижимость спб",
    "аренда",
    "купить квартиру",
    "ипотека",
    "загородная недвижимость",
    "коммерческая недвижимость",
    "инвестиции в недвижимость",
    "ремонт",
    # Авто и транспорт (10)
    "авто",
    "автомобили",
    "авто новости",
    "тест драйв",
    "автоспорт",
    "мото",
    "мотоциклы",
    "грузовики",
    "спецтехника",
    "запчасти",
    # Путешествия и туризм (15)
    "путешествия",
    "туризм",
    "отдых",
    "отпуск",
    "туры",
    "авиабилеты",
    "отели",
    "хостелы",
    "кемпинг",
    "походы",
    "европа",
    "азия",
    "россия туризм",
    "пляжный отдых",
    "горнолыжный отдых",
    "экзотические страны",
    # Еда и рестораны (10)
    "еда",
    "рестораны",
    "кафе",
    "доставка еды",
    "рецепты",
    "кулинария",
    "здоровое питание",
    "веган",
    "вегетарианство",
    "пп рецепты",
    # Мода и красота (10)
    "мода",
    "стиль",
    "одежда",
    "обувь",
    "аксессуары",
    "красота",
    "косметика",
    "уход за кожей",
    "макияж",
    "ногти",
    # Здоровье и спорт (15)
    "здоровье",
    "медицина",
    "врач",
    "диагностика",
    "профилактика",
    "спорт",
    "фитнес",
    "тренировки",
    "йога",
    "бег",
    "кроссфит",
    "бодибилдинг",
    "плавание",
    "велоспорт",
    "здоровый образ жизни",
    # Образование и наука (15)
    "образование",
    "наука",
    "онлайн обучение",
    "курсы",
    "университет",
    "школьное образование",
    "егэ",
    "оге",
    "репетитор",
    "языки",
    "английский",
    "немецкий",
    "китайский",
    "испанский",
    "французский",
    # Дом и семья (10)
    "дом",
    "дача",
    "сад",
    "огород",
    "интерьер",
    "дизайн интерьера",
    "ремонт своими руками",
    "семья",
    "дети",
    "воспитание детей",
    # Развлечения и хобби (15)
    "развлечения",
    "кино",
    "фильмы",
    "сериалы",
    "музыка",
    "игры",
    "видеоигры",
    "настольные игры",
    "книги",
    "чтение",
    "фотография",
    "рисование",
    "музыкальные инструменты",
    "танцы",
    "театр",
    # Новости и СМИ (10)
    "новости",
    "новости россии",
    "новости мира",
    "политика",
    "экономика",
    "общество",
    "происшествия",
    "технологии новости",
    "спорт новости",
    "погода",
    # Работа и карьера (10)
    "работа",
    "вакансии",
    "карьера",
    "удаленная работа",
    "фриланс",
    "резюме",
    "собеседование",
    "повышение",
    "бизнес этикет",
    "тайм менеджмент",
    # Психология и саморазвитие (10)
    "психология",
    "психолог",
    "самопомощь",
    "мотивация",
    "саморазвитие",
    "медитация",
    "осознанность",
    "эмоциональный интеллект",
    "отношения",
    "семейная психология",
]


async def _parse_and_save_chats(
    parser: TelegramParser,
    chat_repo: ChatAnalyticsRepository,
    query: str,
    limit: int = 50,
) -> int:
    """
    Распарсить и сохранить чаты по запросу.

    Args:
        parser: TelegramParser экземпляр.
        chat_repo: ChatAnalyticsRepository экземпляр.
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

        # Сохраняем каждый чат отдельно
        saved_count = 0
        for chat_info in chat_infos:
            # Классифицируем тематику
            topic = classify_topic(chat_info.title, chat_info.description or "")

            try:
                # Получаем или создаём чат
                username = chat_info.username or f"_{chat_info.telegram_id}"
                chat, is_new = await chat_repo.get_or_create_chat(username)

                # Обновляем данные
                chat.telegram_id = chat_info.telegram_id
                chat.title = chat_info.title
                chat.description = chat_info.description
                chat.member_count = chat_info.member_count or 0
                chat.topic = topic
                chat.is_verified = chat_info.is_verified or False
                chat.is_scam = chat_info.is_scam or False
                chat.is_fake = chat_info.is_fake or False
                chat.rating = 7.0 if chat.is_verified else 5.0
                chat.last_subscribers = chat_info.member_count or 0
                chat.last_parsed_at = date.today()

                await chat_repo._session.flush()
                saved_count += 1

            except Exception as e:
                logger.warning(f"Failed to save chat {chat_info.title}: {e}")
                continue

        await chat_repo._session.commit()
        logger.info(f"Saved {saved_count} chats for query '{query}'")

        return saved_count

    except Exception as e:
        logger.error(f"Error parsing query '{query}': {e}")
        return 0


async def _parse_tgstat_and_save(
    telegram_parser: TelegramParser,
    chat_repo: ChatAnalyticsRepository,
    topic: str,
) -> int:
    """
    Распарсить TGStat и сохранить чаты.

    Args:
        telegram_parser: TelegramParser экземпляр.
        chat_repo: ChatAnalyticsRepository экземпляр.
        topic: Тематика.

    Returns:
        Количество сохраненных чатов.
    """
    try:
        # Получаем username из TGStat
        usernames = await telegram_parser.fetch_tgstat_catalog(topic, max_pages=3)

        if not usernames:
            logger.info(f"No usernames found for topic '{topic}' on TGStat")
            return 0

        # Валидируем через Telegram
        chat_details_list = await telegram_parser.batch_validate(usernames, semaphore_count=5)

        if not chat_details_list:
            logger.info(f"No valid chats found for topic '{topic}'")
            return 0

        # Сохраняем каждый чат отдельно
        saved_count = 0
        for chat_details in chat_details_list:
            try:
                # Получаем или создаём чат
                username = chat_details.username or f"_{chat_details.telegram_id}"
                chat, is_new = await chat_repo.get_or_create_chat(username)

                # Обновляем данные
                chat.telegram_id = chat_details.telegram_id
                chat.title = chat_details.title
                chat.description = chat_details.description
                chat.member_count = chat_details.member_count or 0
                chat.topic = topic
                chat.is_verified = chat_details.is_verified or False
                chat.is_scam = chat_details.is_scam or False
                chat.is_fake = chat_details.is_fake or False
                chat.rating = chat_details.rating or 5.0
                chat.last_subscribers = chat_details.member_count or 0
                chat.last_avg_views = chat_details.avg_post_reach or 0
                chat.last_parsed_at = date.today()

                await chat_repo._session.flush()
                saved_count += 1

            except Exception as e:
                logger.warning(f"Failed to save chat {chat_details.title}: {e}")
                continue

        await chat_repo._session.commit()
        logger.info(f"Saved {saved_count} chats from TGStat for topic '{topic}'")

        return saved_count

    except Exception as e:
        logger.error(f"Error parsing TGStat topic '{topic}': {e}")
        return 0


async def _refresh_chats_async(query_category: str | None = None) -> dict[str, Any]:
    """
    Асинхронная функция для обновления базы чатов.

    Args:
        query_category: Категория запросов для парсинга. Если None — все категории.

    Returns:
        Статистика обновления.
    """
    stats = {
        "telegram_search": 0,
        "tgstat": 0,
        "total": 0,
        "errors": 0,
    }

    # Определяем какие запросы парсить
    if query_category and query_category in SEARCH_QUERIES_BY_CATEGORY:
        queries_to_parse = SEARCH_QUERIES_BY_CATEGORY[query_category]
        logger.info(f"Parsing category '{query_category}': {len(queries_to_parse)} queries")
    else:
        queries_to_parse = SEARCH_QUERIES
        logger.info(f"Parsing all categories: {len(queries_to_parse)} queries")

    async with async_session_factory() as session:
        chat_repo = ChatAnalyticsRepository(session)

        # 1. Парсим через Telegram search
        async with TelegramParser() as parser:
            for query in queries_to_parse:
                try:
                    count = await _parse_and_save_chats(parser, chat_repo, query, limit=30)
                    stats["telegram_search"] += count
                    stats["total"] += count

                    # Задержка между запросами для соблюдения лимитов Telegram
                    # Telegram лимит: ~10-20 запросов в минуту на поиск
                    await asyncio.sleep(2)

                except Exception as e:
                    logger.error(f"Error in Telegram search for '{query}': {e}")
                    stats["errors"] += 1

        # 2. Парсим через TGStat (только если категория не указана или это первая категория)
        if not query_category:
            async with TelegramParser() as telegram_parser:
                for topic in POPULAR_TOPICS[:10]:  # Ограничиваем количество
                    try:
                        count = await _parse_tgstat_and_save(telegram_parser, chat_repo, topic)
                        stats["tgstat"] += count
                        stats["total"] += count

                        # Задержка между запросами
                        await asyncio.sleep(2)

                    except Exception as e:
                        logger.error(f"Error in TGStat parsing for '{topic}': {e}")
                        stats["errors"] += 1

        # Коммитим все изменения
        await session.commit()

    return stats


# Категории поисковых запросов для распределения по слотам
SEARCH_QUERIES_BY_CATEGORY = {
    "business": SEARCH_QUERIES[0:20],  # Бизнес и финансы (20)
    "marketing": SEARCH_QUERIES[20:35],  # Маркетинг и продажи (15)
    "it": SEARCH_QUERIES[35:60],  # IT и технологии (25)
    "lifestyle": SEARCH_QUERIES[60:85],  # Недвижимость, Авто, Путешествия (25)
    "health": SEARCH_QUERIES[85:110],  # Еда, Мода, Здоровье (25)
    "education": SEARCH_QUERIES[110:135],  # Образование, Дом, Развлечения (25)
    "news": SEARCH_QUERIES[135:155],  # Новости, Работа, Психология (20)
}


# Celery задача будет определена после создания celery_app
# Импортируем celery_app динамически чтобы избежать circular imports


@celery_app.task(bind=True, base=BaseTask, name="parser:refresh_chat_database")
def refresh_chat_database(self, query_category: str | None = None) -> dict[str, Any]:
    """
    Celery задача для обновления базы данных чатов.

    Запускается по расписанию (каждые 24 часа) или для конкретной категории.
    Собирает данные из Telegram и TGStat.

    Args:
        query_category: Категория запросов (business, marketing, it, lifestyle,
                       health, education, news). Если None — все категории.

    Returns:
        Статистика обновления.
    """
    logger.info(f"Starting chat database refresh (category: {query_category or 'all'})...")

    try:
        stats = asyncio.run(_refresh_chats_async(query_category))

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
        Данные чата или None.
    """
    async with TelegramParser() as parser:
        chat_details = await parser.resolve_and_validate(username)

        if not chat_details:
            return None

        async with async_session_factory() as session:
            chat_repo = ChatAnalyticsRepository(session)

            topic = classify_topic(chat_details.title, chat_details.description or "")

            try:
                # Получаем или создаём чат
                username_clean = chat_details.username or f"_{chat_details.telegram_id}"
                chat, is_new = await chat_repo.get_or_create_chat(username_clean)

                # Обновляем данные
                chat.telegram_id = chat_details.telegram_id
                chat.title = chat_details.title
                chat.description = chat_details.description
                chat.member_count = chat_details.member_count or 0
                chat.topic = topic
                chat.is_verified = chat_details.is_verified or False
                chat.is_scam = chat_details.is_scam or False
                chat.is_fake = chat_details.is_fake or False
                chat.rating = chat_details.rating or 5.0
                chat.last_subscribers = chat_details.member_count or 0
                chat.last_avg_views = chat_details.avg_post_reach or 0
                chat.last_parsed_at = date.today()

                await chat_repo._session.commit()

                return {
                    "telegram_id": chat.telegram_id,
                    "title": chat.title,
                    "username": chat.username,
                    "member_count": chat.member_count,
                    "topic": chat.topic,
                }

            except Exception as e:
                logger.error(f"Failed to save chat {username}: {e}")
                return None


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
            # Обновляем рейтинг напрямую через модель
            from sqlalchemy import select

            from src.db.models.analytics import TelegramChat

            result = await session.execute(
                select(TelegramChat).where(TelegramChat.telegram_id == chat_id)
            )
            chat = result.scalar_one_or_none()
            if chat:
                chat.rating = new_rating
                await session.flush()

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


# ──────────────────────────────────────────────────────
# Analytics Chat Parser Tasks
# ──────────────────────────────────────────────────────


@celery_app.task(
    bind=True,
    base=BaseTask,
    name="parser:collect_all_chats_stats",
    queue="parser",
    max_retries=3,
    default_retry_delay=300,  # 5 минут между retry
    soft_time_limit=6 * 3600,  # 6 часов максимум
)
def collect_all_chats_stats(self) -> dict[str, Any]:
    """
    Главная задача: собрать статистику всех активных чатов.
    Нарезает чаты на батчи по 50 и запускает sub-задачи.
    """
    return asyncio.run(_collect_all_chats_stats_async(self))


async def _collect_all_chats_stats_async(task) -> dict[str, Any]:
    """Асинхронная реализация collect_all_chats_stats."""
    async for session in get_session():
        repo = ChatAnalyticsRepository(session)
        chats = await repo.get_all_active()
        break  # Выходим после первого yield

    if not chats:
        logger.info("Нет активных чатов для парсинга")
        return {"total": 0, "processed": 0, "errors": 0}

    logger.info(f"Начинаю парсинг {len(chats)} чатов")

    # Нарезаем на батчи по 50
    batch_size = 50
    batches = [chats[i : i + batch_size] for i in range(0, len(chats), batch_size)]

    total_processed = 0
    total_errors = 0

    for batch_num, batch in enumerate(batches, 1):
        logger.info(f"Батч {batch_num}/{len(batches)}: {len(batch)} чатов")
        usernames = [c.username for c in batch]
        chat_ids = {c.username: c.id for c in batch}

        # Запустить парсинг батча
        result = await _process_batch(usernames, chat_ids)
        total_processed += result["processed"]
        total_errors += result["errors"]

        logger.info(
            f"Батч {batch_num} завершён: {result['processed']} OK, {result['errors']} ошибок"
        )

    logger.info(
        f"Парсинг завершён. Всего: {len(chats)}, успешно: {total_processed}, ошибок: {total_errors}"
    )
    return {"total": len(chats), "processed": total_processed, "errors": total_errors}


async def _process_batch(usernames: list[str], chat_ids: dict[str, int]) -> dict[str, int]:
    """Обработать один батч чатов и сохранить в БД."""
    today = date.today()
    processed = 0
    errors = 0

    def log_progress(done: int, total: int) -> None:
        logger.debug(f"  Прогресс батча: {done}/{total}")

    async with TelegramParser() as parser:
        metrics_list = await parser.parse_chats_batch(usernames, on_progress=log_progress)

    async for session in get_session():
        repo = ChatAnalyticsRepository(session)
        break  # Выходим после первого yield

    for metrics in metrics_list:
        chat_id = chat_ids.get(metrics.username)
        if not chat_id:
            continue

        if metrics.error:
            await repo.mark_parse_error(chat_id, metrics.error)
            errors += 1
            continue

        # Обновить мета-данные чата
        await repo.update_chat_meta(
            chat_id,
            telegram_id=metrics.telegram_id,
            title=metrics.title,
            description=metrics.description,
            chat_type=ChatType(metrics.chat_type),
            can_post=metrics.can_post,
            is_public=metrics.is_public,
            last_subscribers=metrics.subscribers,
            last_avg_views=metrics.avg_views,
            last_er=metrics.er,
            last_post_frequency=metrics.post_frequency,
        )

        # Сохранить снимок за сегодня
        await repo.upsert_snapshot(
            chat_id=chat_id,
            snapshot_date=today,
            subscribers=metrics.subscribers,
            avg_views=metrics.avg_views,
            max_views=metrics.max_views,
            min_views=metrics.min_views,
            posts_analyzed=metrics.posts_analyzed,
            er=metrics.er,
            post_frequency=metrics.post_frequency,
            posts_last_30d=metrics.posts_last_30d,
            can_post=metrics.can_post,
        )
        processed += 1

    return {"processed": processed, "errors": errors}


@celery_app.task(bind=True, base=BaseTask, name="parser:parse_single_chat", queue="parser")
def parse_single_chat(self, username: str) -> dict[str, Any]:
    """
    Парсинг одного чата по запросу пользователя (не по расписанию).
    Используется когда пользователь добавляет новый чат через бота.
    """
    return asyncio.run(_parse_single_chat_async(username))


async def _parse_single_chat_async(username: str) -> dict[str, Any]:
    """Асинхронная реализация parse_single_chat."""
    async with TelegramParser() as parser:
        metrics = await parser.parse_chat_metrics(username)

    if metrics.error:
        return {"success": False, "error": metrics.error}

    async for session in get_session():
        repo = ChatAnalyticsRepository(session)
        break  # Выходим после первого yield

    chat, is_new = await repo.get_or_create_chat(username)
    await repo.update_chat_meta(
        chat.id,
        telegram_id=metrics.telegram_id,
        title=metrics.title,
        description=metrics.description,
        chat_type=ChatType(metrics.chat_type),
        can_post=metrics.can_post,
        is_public=metrics.is_public,
        last_subscribers=metrics.subscribers,
        last_avg_views=metrics.avg_views,
        last_er=metrics.er,
        last_post_frequency=metrics.post_frequency,
    )
    await repo.upsert_snapshot(
        chat_id=chat.id,
        snapshot_date=date.today(),
        subscribers=metrics.subscribers,
        avg_views=metrics.avg_views,
        max_views=metrics.max_views,
        min_views=metrics.min_views,
        posts_analyzed=metrics.posts_analyzed,
        er=metrics.er,
        post_frequency=metrics.post_frequency,
        posts_last_30d=metrics.posts_last_30d,
        can_post=metrics.can_post,
    )

    return {
        "success": True,
        "is_new": is_new,
        "title": metrics.title,
        "subscribers": metrics.subscribers,
        "er": metrics.er,
        "can_post": metrics.can_post,
    }
