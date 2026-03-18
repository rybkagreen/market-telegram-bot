"""
Parser Celery tasks для обновления базы данных чатов.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

from src.constants.parser import POPULAR_TOPICS
from src.db.models.telegram_chat import ChatType
from src.db.repositories.telegram_chat_repo import TelegramChatRepository
from src.db.session import async_session_factory, get_session
from src.tasks.celery_app import BaseTask, celery_app
from src.utils.telegram.channel_rules_checker import check_channel_rules
from src.utils.telegram.llm_classifier import classify_channel_with_llm
from src.utils.telegram.parser import TelegramParser
from src.utils.telegram.russian_lang_detector import is_russian_text
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


# Поисковые запросы для парсинга Telegram (ОПТИМИЗИРОВАННЫЕ)
# Используем конкретные фразы + английские запросы для лучшего покрытия
SEARCH_QUERIES = [
    # Бизнес и финансы (25) — конкретные фразы
    "telegram business channel",
    "russian business news",
    "startup russia",
    "investments crypto",
    "trading signals",
    "forex trading",
    "stock market analysis",
    "passive income ideas",
    "entrepreneur mindset",
    "small business tips",
    "self employed russia",
    "ip russia business",
    "business coaching",
    "transformator business",
    "radishevsky business",
    "slishko business",
    "academy trading",
    "investment school",
    "business management",
    "corporate governance",
    "business strategy",
    "scale business",
    "franchise business",
    "business ideas 2026",
    "finance news russia",
    # Маркетинг и продажи (30)
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
    "воронка продаж",
    "crm система",
    "скрипты продаж",
    "холодные звонки",
    "маркетолог",
    "брендинг",
    "упаковка бизнеса",
    "позиционирование",
    "целевая аудитория",
    "аналитика маркетинг",
    "вебинары",
    "запуск продукта",
    "инфобизнес",
    "онлайн школа",
    "продвижение instagram",
    # IT и технологии (40)
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
    "fullstack",
    "нейросети",
    "chatgpt",
    "openai",
    "blockchain",
    "smart contracts",
    "web3",
    "кибербезопасность",
    "пентест",
    "разработка игр",
    # Недвижимость (15)
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
    "дизайн интерьера",
    "застройщик",
    "новостройки",
    "вторичное жилье",
    "риелтор",
    # Авто и транспорт (15)
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
    "автосервис",
    "тюнинг",
    "автокредит",
    "страховка осаго",
    "права пдд",
    # Путешествия и туризм (20)
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
    # Еда и рестораны (20)
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
    "шеф повар",
    "гастрономия",
    "винный клуб",
    "кофейня",
    "бары рестораны",
    "фуд блог",
    "обзор ресторанов",
    "мишлен",
    "кулинарная школа",
    "выпечка торты",
    # Мода и красота (20)
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
    "стилист",
    "шоппинг",
    "бьюти блог",
    "парикмахер",
    "салон красоты",
    "маникюр педикюр",
    "люксовые бренды",
    "mass market одежда",
    "тренды моды",
    "имидж стиль",
    # Здоровье и спорт (25)
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
    "лфк массаж",
    "реабилитация",
    "диетология",
    "похудение",
    "набор массы",
    "гормоны здоровье",
    "витамины добавки",
    "сон отдых",
    "стресс депрессия",
    "женское здоровье",
    # Образование и наука (25)
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
    "подготовка к экзаменам",
    "олимпиады школьников",
    "аспирантура",
    "диссертация",
    "научные статьи",
    "конференции",
    "гранты исследования",
    "повышение квалификации",
    "проф переподготовка",
    "детское образование",
    # Дом и семья (20)
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
    "беременность роды",
    "грудное вскармливание",
    "развивашки дети",
    "подростки психология",
    "усыновление опека",
    "многодетная семья",
    "семейный бюджет",
    "совместные покупки",
    "handmade поделки",
    "комнатные растения",
    # Развлечения и хобби (25)
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
    "концерты мероприятия",
    "клубы вечеринки",
    "рыбалка охота",
    "туризм походы",
    "коллекционирование",
    "астрология эзотерика",
    "животные питомцы",
    "аквариум рыбки",
    "собаки кошки",
    "юмор комедия",
    # Новости и СМИ (20)
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
    "срочные новости",
    "главное за день",
    "аналитика новости",
    "расследования журналисты",
    "факты проверка",
    "фейки новости",
    "мировые события",
    # Работа и карьера (20)
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
    "поиск работы",
    "head hunter hh",
    "зарплата переговоры",
    "профориентация",
    "стажировка практика",
    "нетворкинг связи",
    "деловая переписка",
    "презентация выступления",
    "лидерство управление",
    "продуктивность эффективность",
    # Психология и саморазвитие (20)
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
    "личностный рост",
    "уверенность себе",
    "прокрастинация лень",
    "целеполагание планы",
    "дисциплина привычки",
    "психосоматика здоровье",
    "тревога паника",
    "самооценка любовь",
    "манипуляции токсичные",
    "коучинг тренинги",
]


async def _parse_and_save_chats(
    parser: TelegramParser,
    chat_repo: TelegramChatRepository,
    query: str,
    limit: int = 50,
    require_russian: bool = True,  # Новый параметр
) -> int:
    """
    Распарсить и сохранить чаты по запросу.

    Args:
        parser: TelegramParser экземпляр.
        chat_repo: TelegramChatRepository экземпляр.
        query: Поисковый запрос.
        limit: Максимальное количество результатов.
        require_russian: Требовать русскоязычность канала.

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
        blocked_count = 0
        non_russian_count = 0

        for chat_info in chat_infos:
            # Проверяем русскоязычность (если требуется)
            if require_russian:
                description = chat_info.description or ""
                title = chat_info.title or ""

                # Проверяем описание или название на русский язык
                if description and not is_russian_text(description):
                    non_russian_count += 1
                    logger.debug(f"Skipping non-Russian channel: {title}")
                    continue
                elif not description and not is_russian_text(title):
                    non_russian_count += 1
                    logger.debug(f"Skipping non-Russian channel (title only): {title}")
                    continue

            # Проверяем правила канала на запрет рекламы
            if chat_info.username:
                try:
                    rules_result = await check_channel_rules(parser._client, chat_info.username)
                    if not rules_result.allows_ads:
                        logger.info(
                            f"Channel @{chat_info.username} skipped: {rules_result.reject_reason}"
                        )
                except Exception as e:
                    logger.debug(f"Rules check failed for @{chat_info.username}: {e}")

            # Проверяем контент канала (название + описание)
            from src.utils.content_filter.filter import check as content_filter_check

            channel_content = f"{chat_info.title} {chat_info.description or ''}"
            filter_result = await content_filter_check(channel_content)

            if not filter_result.passed:
                blocked_count += 1
                logger.debug(
                    f"Channel '{chat_info.title}' blocked by content filter: "
                    f"{filter_result.categories}"
                )
                continue

            # Классифицируем тематику
            topic = classify_topic(chat_info.title, chat_info.description or "")

            # Автоклассификация подкатегории
            from src.utils.categories import classify_subcategory

            subcategory = classify_subcategory(
                title=chat_info.title or "",
                description=chat_info.description or "",
                topic=topic,
            )

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
                chat.subcategory = subcategory
                chat.is_scam = chat_info.is_scam or False
                chat.is_fake = chat_info.is_fake or False
                chat.rating = getattr(chat_info, "rating", None) or 5.0
                chat.last_subscribers = chat_info.member_count or 0
                chat.last_parsed_at = date.today()

                # Сохраняем информацию о языке
                if chat_info.meta_json:
                    chat.language = chat_info.meta_json.get("language", "ru")
                    chat.russian_score = chat_info.meta_json.get("russian_score", 1.0)
                else:
                    chat.language = "ru"
                    chat.russian_score = 1.0

                # LLM-классификация для новых каналов
                if is_new:
                    try:
                        # Собираем recent posts
                        entity = await parser.client.get_entity(chat.telegram_id)
                        recent_posts = await parser._collect_recent_posts_texts(entity, limit=5)

                        # Классифицируем через LLM
                        classification = await classify_channel_with_llm(
                            ai_service=None,  # Не используется
                            title=chat.title or "",
                            username=chat.username or "",
                            member_count=chat.member_count or 0,
                            language=chat.language,
                            description=chat.description or "",
                            posts=[p["text"] for p in recent_posts] if recent_posts else [],
                        )

                        # Обновляем канал
                        chat.topic = classification.topic
                        chat.subcategory = classification.subcategory or subcategory
                        chat.rating = classification.rating
                        chat.last_classified_at = datetime.now(UTC)
                        chat.llm_confidence = classification.confidence
                        chat.recent_posts = recent_posts

                        if classification.used_fallback:
                            logger.warning(f"LLM classification fallback for @{chat.username}")
                        else:
                            logger.info(
                                f"LLM classified @{chat.username}: {classification.topic} (confidence={classification.confidence:.2f})"
                            )

                    except Exception as e:
                        logger.warning(f"LLM classification failed for @{chat.username}: {e}")
                        # Не бросаем исключение — парсинг не должен падать

                await chat_repo._session.flush()
                saved_count += 1

            except Exception as e:
                logger.warning(f"Failed to save chat {chat_info.title}: {e}")
                continue

        await chat_repo._session.commit()

        log_msg = f"Saved {saved_count} chats for query '{query}'"
        if blocked_count > 0:
            log_msg += f" (blocked {blocked_count} by content filter)"
        if non_russian_count > 0:
            log_msg += f" (skipped {non_russian_count} non-Russian)"

        logger.info(log_msg)

        return saved_count

    except Exception as e:
        logger.error(f"Error parsing query '{query}': {e}")
        return 0


async def _parse_and_save_chats_by_topic(
    parser: TelegramParser,
    chat_repo: TelegramChatRepository,
    topic: str,
    limit_per_query: int = 30,
    require_russian: bool = True,
) -> int:
    """
    Распарсить и сохранить чаты по теме используя множество поисковых запросов.
    Использует TOPIC_SEARCH_QUERIES для расширенного поиска.

    Args:
        parser: TelegramParser экземпляр.
        chat_repo: TelegramChatRepository экземпляр.
        topic: Тема из TOPIC_SEARCH_QUERIES (например, "бизнес", "it").
        limit_per_query: Каналов на каждый поисковый запрос.
        require_russian: Требовать русскоязычность канала.

    Returns:
        Количество сохраненных чатов.
    """
    try:
        # Ищем чаты по теме с использованием всех запросов из словаря
        chat_infos = await parser.search_by_topic(topic, limit_per_query=limit_per_query)

        if not chat_infos:
            logger.info(f"No chats found for topic: {topic}")
            return 0

        # Сохраняем каждый чат отдельно
        saved_count = 0
        blocked_count = 0
        non_russian_count = 0

        for chat_info in chat_infos:
            # Проверяем русскоязычность (если требуется)
            if require_russian:
                description = chat_info.description or ""
                title = chat_info.title or ""

                # Проверяем описание или название на русский язык
                if description and not is_russian_text(description):
                    non_russian_count += 1
                    logger.debug(f"Skipping non-Russian channel: {title}")
                    continue
                elif not description and not is_russian_text(title):
                    non_russian_count += 1
                    logger.debug(f"Skipping non-Russian channel (title only): {title}")
                    continue

            # Проверяем правила канала на запрет рекламы
            if chat_info.username:
                try:
                    rules_result = await check_channel_rules(parser._client, chat_info.username)
                    if not rules_result.allows_ads:
                        logger.info(
                            f"Channel @{chat_info.username} skipped: {rules_result.reject_reason}"
                        )
                except Exception as e:
                    logger.debug(f"Rules check failed for @{chat_info.username}: {e}")

            # Проверяем контент канала (название + описание)
            from src.utils.content_filter.filter import check as content_filter_check

            channel_content = f"{chat_info.title} {chat_info.description or ''}"
            filter_result = await content_filter_check(channel_content)

            if not filter_result.passed:
                blocked_count += 1
                logger.debug(
                    f"Channel '{chat_info.title}' blocked by content filter: "
                    f"{filter_result.categories}"
                )
                continue

            # Классифицируем тематику
            topic_classified = classify_topic(chat_info.title, chat_info.description or "")

            # Автоклассификация подкатегории
            from src.utils.categories import classify_subcategory

            subcategory = classify_subcategory(
                title=chat_info.title or "",
                description=chat_info.description or "",
                topic=topic_classified,
            )

            try:
                # Получаем или создаём чат
                username = chat_info.username or f"_{chat_info.telegram_id}"
                chat, is_new = await chat_repo.get_or_create_chat(username)

                # Обновляем данные
                chat.telegram_id = chat_info.telegram_id
                chat.title = chat_info.title
                chat.description = chat_info.description
                chat.member_count = chat_info.member_count or 0
                chat.topic = topic_classified
                chat.subcategory = subcategory
                chat.is_scam = chat_info.is_scam or False
                chat.is_fake = chat_info.is_fake or False
                chat.rating = getattr(chat_info, "rating", None) or 5.0
                chat.last_subscribers = chat_info.member_count or 0
                chat.last_parsed_at = date.today()

                # Сохраняем информацию о языке
                if chat_info.meta_json:
                    chat.language = chat_info.meta_json.get("language", "ru")
                    chat.russian_score = chat_info.meta_json.get("russian_score", 1.0)
                else:
                    chat.language = "ru"
                    chat.russian_score = 1.0

                # LLM-классификация для новых каналов
                if is_new:
                    try:
                        # Собираем recent posts
                        entity = await parser.client.get_entity(chat.telegram_id)
                        recent_posts = await parser._collect_recent_posts_texts(entity, limit=5)

                        # Классифицируем через LLM
                        classification = await classify_channel_with_llm(
                            ai_service=None,  # Не используется
                            title=chat.title or "",
                            username=chat.username or "",
                            member_count=chat.member_count or 0,
                            language=chat.language,
                            description=chat.description or "",
                            posts=[p["text"] for p in recent_posts] if recent_posts else [],
                        )

                        # Обновляем канал
                        chat.topic = classification.topic
                        chat.subcategory = classification.subcategory or subcategory
                        chat.rating = classification.rating
                        chat.last_classified_at = datetime.now(UTC)
                        chat.llm_confidence = classification.confidence
                        chat.recent_posts = recent_posts

                        if classification.used_fallback:
                            logger.warning(f"LLM classification fallback for @{chat.username}")
                        else:
                            logger.info(
                                f"LLM classified @{chat.username}: {classification.topic} (confidence={classification.confidence:.2f})"
                            )

                    except Exception as e:
                        logger.warning(f"LLM classification failed for @{chat.username}: {e}")
                        # Не бросаем исключение — парсинг не должен падать

                await chat_repo._session.flush()
                saved_count += 1

            except Exception as e:
                logger.warning(f"Failed to save chat {chat_info.title}: {e}")
                continue

        await chat_repo._session.commit()

        log_msg = f"Saved {saved_count} chats for topic '{topic}'"
        if blocked_count > 0:
            log_msg += f" (blocked {blocked_count} by content filter)"
        if non_russian_count > 0:
            log_msg += f" (skipped {non_russian_count} non-Russian)"

        logger.info(log_msg)

        return saved_count

    except Exception as e:
        logger.error(f"Error parsing topic '{topic}': {e}")
        return 0


async def _parse_tgstat_and_save(
    telegram_parser: TelegramParser,
    chat_repo: TelegramChatRepository,
    topic: str,
) -> int:
    """
    Распарсить TGStat и сохранить чаты.

    Args:
        telegram_parser: TelegramParser экземпляр.
        chat_repo: TelegramChatRepository экземпляр.
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
        blocked_count = 0

        for chat_details in chat_details_list:
            # Проверяем контент канала (название + описание)
            from src.utils.content_filter.filter import check as content_filter_check

            channel_content = f"{chat_details.title} {chat_details.description or ''}"
            filter_result = await content_filter_check(channel_content)

            if not filter_result.passed:
                blocked_count += 1
                logger.debug(
                    f"Channel '{chat_details.title}' blocked by content filter: "
                    f"{filter_result.categories}"
                )
                continue

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
        logger.info(
            f"Saved {saved_count} chats from TGStat for topic '{topic}' "
            f"(blocked {blocked_count} by content filter)"
        )

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
        chat_repo = TelegramChatRepository(session)

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

        # 1.5. Парсим через Telegram search по русскоязычным темам (TOPIC_SEARCH_QUERIES)
        # Используем новые методы с пагинацией и расширенными запросами
        if not query_category:  # Только для полного обновления
            async with TelegramParser() as parser:
                # Парсим ключевые русскоязычные темы
                russian_topics = ["бизнес", "it", "маркетинг", "финансы", "крипто", "новости"]
                for topic in russian_topics:
                    try:
                        count = await _parse_and_save_chats_by_topic(
                            parser, chat_repo, topic, limit_per_query=30
                        )
                        stats["telegram_search"] += count
                        stats["total"] += count

                        # Задержка между темами
                        await asyncio.sleep(3)

                    except Exception as e:
                        logger.error(f"Error in Telegram topic search for '{topic}': {e}")
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


@celery_app.task(
    bind=True,
    base=BaseTask,
    name="parser:refresh_chat_database",
    max_retries=3,
    default_retry_delay=300,  # 5 минут между попытками
    autoretry_for=(Exception,),
    retry_kwargs={"exc": Exception("Parser error"), "countdown": 300},
)
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
        # Health check Redis перед запуском
        from redis.asyncio import Redis as AsyncRedis

        from src.config.settings import settings

        try:
            redis_client = AsyncRedis.from_url(
                str(settings.redis_url), socket_timeout=5, socket_connect_timeout=5
            )
            asyncio.run(redis_client.ping())
            asyncio.run(redis_client.close())
            logger.debug("Redis health check passed")
        except Exception as redis_error:
            logger.warning(f"Redis health check failed: {redis_error}")
            # Не прерываем задачу, просто логируем

        # Используем правильный подход для async в Celery worker
        try:
            asyncio.get_running_loop()
            # Loop уже существует — запускаем в отдельном потоке
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(asyncio.run, _refresh_chats_async(query_category))
                stats = future.result(timeout=1800)  # 30 минут таймаут
        except RuntimeError:
            # Нет активного loop — используем обычный asyncio.run()
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
        # Retry при ошибках подключения
        if any(x in str(e).lower() for x in ["connection", "timeout", "redis", "telethon"]):
            raise self.retry(
                args=self.request.args,
                kwargs=self.request.kwargs,
                countdown=300 * (self.request.retries + 1),
            ) from e
        return {"error": str(e)}


# Алиасы для 7 слотов парсинга (каждая категория — отдельная задача для Beat)
# Используем правильный паттерн регистрации алиасов с пробросом query_category
def _make_category_task(category: str):
    """Создать task wrapper для категории."""

    @celery_app.task(bind=True, base=BaseTask, name=f"parser:refresh_chat_database_{category}")
    def category_task(self):
        return refresh_chat_database(self, query_category=category)

    return category_task


refresh_chat_database_business = _make_category_task("business")
refresh_chat_database_marketing = _make_category_task("marketing")
refresh_chat_database_it = _make_category_task("it")
refresh_chat_database_lifestyle = _make_category_task("lifestyle")
refresh_chat_database_health = _make_category_task("health")
refresh_chat_database_education = _make_category_task("education")
refresh_chat_database_news = _make_category_task("news")


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
            chat_repo = TelegramChatRepository(session)

            topic = classify_topic(chat_details.title, chat_details.description or "")

            # Автоклассификация подкатегории
            from src.utils.categories import classify_subcategory

            subcategory = classify_subcategory(
                title=chat_details.title or "",
                description=chat_details.description or "",
                topic=topic,
            )

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
                chat.subcategory = subcategory
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

            from src.db.models.telegram_chat import TelegramChat

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
        repo = TelegramChatRepository(session)
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
        repo = TelegramChatRepository(session)
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

        from src.db.models.telegram_chat import TelegramChat
        from src.utils.categories import classify_subcategory

        # Получаем текущий topic из БД
        chat = await session.get(TelegramChat, chat_id)
        topic = chat.topic if chat else None

        subcategory = classify_subcategory(
            title=metrics.title or "",
            description=metrics.description or "",
            topic=topic or "",
        )

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
            subcategory=subcategory,
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
        repo = TelegramChatRepository(session)
        break  # Выходим после первого yield

    chat, is_new = await repo.get_or_create_chat(username)

    # Автоклассификация подкатегории
    from src.utils.categories import classify_subcategory

    subcategory = classify_subcategory(
        title=metrics.title or "",
        description=metrics.description or "",
        topic=(chat.topic if chat else None) or "",
    )

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
        subcategory=subcategory,
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


@celery_app.task(name="parser:recheck_channel_rules", queue="parser")
def recheck_channel_rules_task() -> None:
    """
    Периодически перепроверять правила существующих активных каналов.
    Запускается через Celery Beat раз в 30 дней.
    """
    asyncio.run(_recheck_channel_rules_async())


async def _recheck_channel_rules_async() -> None:
    """Асинхронная реализация recheck_channel_rules_task."""
    from sqlalchemy import and_, select

    from src.db.models.telegram_chat import TelegramChat
    from src.utils.telegram.channel_rules_checker import check_channel_rules
    from src.utils.telegram.parser import TelegramParser

    batch_size = 50
    checked = 0
    deactivated = 0

    async with TelegramParser() as parser, async_session_factory() as session:
        stmt = (
            select(TelegramChat)
            .where(
                and_(
                    TelegramChat.is_active == True,  # noqa: E712
                    TelegramChat.username.isnot(None),
                    TelegramChat.is_blacklisted == False,  # noqa: E712
                )
            )
            .limit(batch_size)
        )
        result = await session.execute(stmt)
        chats = result.scalars().all()

        for chat in chats:
            rules_result = await check_channel_rules(parser._client, chat.username)
            checked += 1

            if not rules_result.allows_ads:
                chat.is_active = False
                deactivated += 1
                logger.info(
                    f"Channel @{chat.username} deactivated after recheck: "
                    f"{rules_result.reject_reason}"
                )

        await session.commit()

    logger.info(f"recheck_channel_rules: checked={checked}, deactivated={deactivated}")


# ══════════════════════════════════════════════════════════════
# LLM-КЛАССИФИКАЦИЯ КАНАЛОВ
# ══════════════════════════════════════════════════════════════

CLASSIFY_BATCH_SIZE = 50


@celery_app.task(name="parser:llm_reclassify_all", bind=True)
def llm_reclassify_all_task(self, batch_size: int = CLASSIFY_BATCH_SIZE) -> dict:
    """
    Переклассифицировать все каналы в базе через LLM.
    Обрабатывает батчами — безопасно для больших баз.
    Возвращает статистику: total, updated, failed, skipped.
    """
    import asyncio
    import sys

    # Python 3.13+ требует SelectorEventLoop для Celery prefork
    if sys.platform != "win32":
        # Linux/Mac используем SelectorEventLoop
        asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())

    # Создаём новый event loop для этой задачи
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(_llm_reclassify_all_async(batch_size))
    finally:
        # Отменяем все pending tasks перед закрытием
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()
        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        loop.close()


async def _llm_reclassify_all_async(batch_size: int) -> dict:
    """Асинхронная реализация LLM-переклассификации."""
    from datetime import datetime, timedelta

    from sqlalchemy import or_, select

    from src.db.models.telegram_chat import TelegramChat

    stats = {"total": 0, "updated": 0, "failed": 0, "skipped": 0}

    async with async_session_factory() as session:
        # Берём каналы которые:
        # - активны (is_active=True)
        # - не в чёрном списке
        # - никогда не классифицировались LLM ИЛИ классифицировались >30 дней назад
        cutoff = datetime.now(UTC) - timedelta(days=30)
        stmt = (
            select(TelegramChat)
            .where(
                TelegramChat.is_active == True,  # noqa: E712
                TelegramChat.is_blacklisted == False,  # noqa: E712
                or_(
                    TelegramChat.last_classified_at.is_(None),
                    TelegramChat.last_classified_at < cutoff,
                ),
            )
            .order_by(TelegramChat.last_classified_at.asc().nullsfirst())
            .limit(batch_size)
        )
        result = await session.execute(stmt)
        chats = result.scalars().all()
        stats["total"] = len(chats)

        for chat in chats:
            try:
                # Собираем recent posts если есть
                posts = chat.recent_posts or []
                posts_texts = [p["text"] for p in posts] if posts else []

                classification = await classify_channel_with_llm(
                    ai_service=None,  # Не используется
                    title=chat.title or "",
                    username=chat.username or "",
                    member_count=chat.member_count or 0,
                    language=chat.language or "unknown",
                    description=chat.description or "",
                    posts=posts_texts,
                )

                # Обновляем канал
                chat.topic = classification.topic
                chat.subcategory = classification.subcategory or ""
                chat.rating = classification.rating
                chat.last_classified_at = datetime.now(UTC)
                chat.llm_confidence = classification.confidence

                if classification.used_fallback:
                    stats["failed"] += 1
                else:
                    stats["updated"] += 1

                logger.info(
                    f"Classified @{chat.username}: {classification.topic} "
                    f"(confidence={classification.confidence:.2f})"
                )

            except Exception as e:
                logger.error(f"Failed to classify @{chat.username}: {e}")
                stats["failed"] += 1

        await session.commit()

    logger.info(f"LLM reclassify complete: {stats}")
    return stats


# ─────────────────────────────────────────────
# Авто-классификация каналов без подкатегории (Спринт 12)
# ─────────────────────────────────────────────


@celery_app.task(name="parser:autoclassify_channels", queue="parser")
def autoclassify_channels(limit: int = 50) -> dict:
    """
    Автоматически классифицировать каналы без подкатегории.
    Использует MistralAIService.classify_channel().

    Args:
        limit: Максимальное количество каналов для обработки.

    Returns:
        Статистика классификации.
    """

    async def _classify_async() -> dict:
        from sqlalchemy import select

        from src.core.services.mistral_ai_service import mistral_ai_service
        from src.db.models.telegram_chat import TelegramChat

        stats = {"classified": 0, "errors": 0, "low_confidence": 0}

        async with async_session_factory() as session:
            # Выбираем каналы без подкатегории
            query = (
                select(TelegramChat)
                .where(
                    TelegramChat.is_active,
                    (TelegramChat.subcategory.is_(None)) | (TelegramChat.subcategory == ""),
                )
                .limit(limit)
            )
            result = await session.execute(query)
            channels = result.scalars().all()

            for channel in channels:
                try:
                    # Используем async метод Mistral
                    ai_result = await mistral_ai_service.classify_channel(
                        title=channel.title or "",
                        description=channel.description or "",
                        username=channel.username or "",
                        member_count=channel.member_count or 0,
                    )

                    if ai_result.confidence >= 0.7:
                        channel.topic = ai_result.topic
                        channel.subcategory = ai_result.subcategory or ""
                        stats["classified"] += 1
                        logger.info(
                            f"Classified channel '{channel.title}': "
                            f"{ai_result.topic}/{ai_result.subcategory} "
                            f"(confidence={ai_result.confidence:.2f})"
                        )
                    else:
                        stats["low_confidence"] += 1
                        logger.warning(
                            f"Low confidence for channel '{channel.title}': {ai_result.confidence:.2f}"
                        )

                except Exception as e:
                    logger.error(f"Error classifying channel {channel.id}: {e}")
                    stats["errors"] += 1

            await session.commit()

        logger.info(f"Auto-classification complete: {stats}")
        return stats

    try:
        return asyncio.run(_classify_async())
    except Exception as e:
        logger.error(f"autoclassify_channels failed: {e}")
        return {"error": str(e)}
