"""
Topic Classifier для классификации Telegram-каналов по тематикам.
Использует rapidfuzz для нечёткого сопоставления и словаря ключевых слов.
"""

import logging
import re
from dataclasses import dataclass
from typing import Optional

try:
    from rapidfuzz import fuzz, process
except ImportError:
    fuzz = None  # type: ignore
    process = None  # type: ignore

logger = logging.getLogger(__name__)


@dataclass
class TopicMatch:
    """Результат сопоставления тематики."""

    topic: str
    score: float
    matched_keywords: list[str]


# Словари ключевых слов для каждой тематики
TOPIC_KEYWORDS: dict[str, list[str]] = {
    "business": [
        "бизнес",
        "предприниматель",
        "стартап",
        "инвестиции",
        "компания",
        "корпорация",
        "менеджмент",
        "продажи",
        "маркетинг",
        "бренд",
        "успех",
        "деньги",
        "прибыль",
        "доход",
        "финансы",
        "акции",
        "трейдинг",
        "экономика",
        "рынок",
        "конкурент",
        "стратегия",
        "лидер",
        "ceo",
        "founder",
        "entrepreneur",
    ],
    "it": [
        "программирование",
        "разработка",
        "код",
        "алгоритм",
        "python",
        "javascript",
        "java",
        "cpp",
        "golang",
        "rust",
        "веб",
        "frontend",
        "backend",
        "devops",
        "docker",
        "kubernetes",
        "cloud",
        "aws",
        "azure",
        "ai",
        "ml",
        "нейросеть",
        "искусственный интеллект",
        "data science",
        "аналитика",
        "big data",
        "blockchain",
        "крипта",
        "smart contract",
        "api",
        "database",
        "sql",
        "nosql",
        "git",
        "linux",
        "server",
        "cybersecurity",
        "хакер",
        "уязвимость",
    ],
    "news": [
        "новости",
        "события",
        "политика",
        "общество",
        "мир",
        "страна",
        "правительство",
        "президент",
        "выборы",
        "закон",
        "суд",
        "происшествия",
        "катастрофа",
        "война",
        "конфликт",
        "санкции",
        "кризис",
        "реформа",
        "депутат",
        "министр",
        "пресс",
        "медиа",
        "журналист",
        "репортаж",
        "интервью",
        "breaking news",
        "срочно",
        "главное",
    ],
    "crypto": [
        "криптовалюта",
        "биткоин",
        "ethereum",
        "btc",
        "eth",
        "binance",
        "trading",
        "defi",
        "nft",
        "токен",
        "coin",
        "майнинг",
        "блокчейн",
        "wallet",
        "exchange",
        "hodl",
        "altcoin",
        "stablecoin",
        "usdt",
        "usdc",
        "solana",
        "cardano",
        "polkadot",
        "avalanche",
        "web3",
        "metamask",
        "airdrop",
        "staking",
        "yield farming",
    ],
    "marketing": [
        "маркетинг",
        "реклама",
        "продвижение",
        "smm",
        "таргет",
        "контекст",
        "seo",
        "контент",
        "блогер",
        "influencer",
        "лиды",
        "конверсия",
        "воронка",
        "crm",
        "email",
        "рассылка",
        "бренд",
        "упаковка",
        "позиционирование",
        "целевая аудитория",
        "трафик",
        "engagement",
        "reach",
        "impression",
        "cpm",
        "cpc",
        "cpa",
        "roi",
        "romi",
    ],
    "finance": [
        "финансы",
        "банк",
        "кредит",
        "ипотека",
        "вклад",
        "депозит",
        "страхование",
        "налоги",
        "бухгалтерия",
        "отчетность",
        "аудит",
        "консалтинг",
        "wealth",
        "private banking",
        "asset management",
        "portfolio",
        "дивиденды",
        "облигации",
        "фонды",
        "etf",
        "mutual funds",
        "pension",
        "retirement",
        "budget",
        "economy",
        "inflation",
        "курс валют",
        "доллар",
        "евро",
        "рубль",
    ],
    "education": [
        "образование",
        "обучение",
        "курс",
        "школа",
        "университет",
        "институт",
        "лекция",
        "семинар",
        "вебинар",
        "тренинг",
        "мастер-класс",
        "сертификат",
        "диплом",
        "экзамен",
        "тест",
        "знания",
        "наука",
        "исследование",
        "студент",
        "преподаватель",
        "учитель",
        "профессор",
        "доктор",
        "кандидат",
        "диссертация",
        "публикация",
        "статья",
        "конференция",
        "симпозиум",
    ],
    "lifestyle": [
        "образ жизни",
        "лайфстайл",
        "хобби",
        "увлечение",
        "путешествия",
        "отдых",
        "развлечения",
        "кино",
        "музыка",
        "искусство",
        "театр",
        "выставка",
        "музей",
        "книги",
        "литература",
        "психология",
        "отношения",
        "семья",
        "дети",
        "воспитание",
        "дом",
        "уют",
        "интерьер",
        "дизайн",
        "сад",
        "огород",
        "животные",
        "питомцы",
        "кошки",
        "собаки",
    ],
    "health": [
        "здоровье",
        "медицина",
        "врач",
        "больница",
        "клиника",
        "лечение",
        "диагноз",
        "симптомы",
        "лекарства",
        "таблетки",
        "витамины",
        "спорт",
        "фитнес",
        "тренировки",
        "йога",
        "медитация",
        "питание",
        "диета",
        "похудение",
        "набор массы",
        "бодибилдинг",
        "кроссфит",
        "бег",
        "плавание",
        "велоспорт",
        "лыжи",
        "марафон",
        "зож",
        "пп",
        "иммунитет",
        "профилактика",
        "вакцинация",
    ],
    "sport": [
        "спорт",
        "футбол",
        "хоккей",
        "баскетбол",
        "теннис",
        "волейбол",
        "бокс",
        "mma",
        "ufc",
        "чемпионат",
        "турнир",
        "лига",
        "кубок",
        "медаль",
        "рекорд",
        "атлет",
        "спортсмен",
        "тренер",
        "команда",
        "клуб",
        "стадион",
        "матч",
        "игра",
        "победа",
        "поражение",
        "ничья",
        "гол",
        "счет",
        "таблица",
        "рейтинг",
        "трансфер",
        "контракт",
    ],
    "auto": [
        "авто",
        "автомобиль",
        "машина",
        "водитель",
        "дорога",
        "трафик",
        "дтп",
        "авария",
        "ремонт",
        "сервис",
        "запчасти",
        "шиномонтаж",
        "мойка",
        "страховка",
        "осаго",
        "каско",
        "права",
        "гибдд",
        "штраф",
        "парковка",
        "заправка",
        "бензин",
        "дизель",
        "электрокар",
        "tesla",
        "bmw",
        "mercedes",
        "audi",
        "toyota",
        "lada",
        "kia",
        "hyundai",
        "volkswagen",
        "ford",
        "chevrolet",
        "nissan",
        "mazda",
        "honda",
        "lexus",
        "porsche",
        "ferrari",
        "lamborghini",
    ],
    "travel": [
        "путешествия",
        "туризм",
        "отпуск",
        "каникулы",
        "отель",
        "гостиница",
        "хостел",
        "авиабилеты",
        "перелет",
        "рейс",
        "аэропорт",
        "виза",
        "паспорт",
        "таможня",
        "экскурсия",
        "гид",
        "тур",
        "туроператор",
        "пляж",
        "море",
        "океан",
        "горы",
        "лес",
        "озеро",
        "река",
        "национальный парк",
        "заповедник",
        "достопримечательности",
        "памятник",
        "музей",
        "галерея",
        "собор",
        "храм",
        "замок",
        "крепость",
    ],
    "food": [
        "еда",
        "кулинария",
        "рецепты",
        "готовка",
        "повар",
        "шеф",
        "ресторан",
        "кафе",
        "бар",
        "кухня",
        "блюдо",
        "закуска",
        "салат",
        "суп",
        "мясо",
        "рыба",
        "овощи",
        "фрукты",
        "десерт",
        "торт",
        "пирог",
        "выпечка",
        "хлеб",
        "пицца",
        "суши",
        "роллы",
        "бургер",
        "паста",
        "вино",
        "коктейль",
        "напитки",
        "кофе",
        "чай",
        "гастрономия",
        "фуд-блог",
        "обзор ресторанов",
    ],
    "fashion": [
        "мода",
        "стиль",
        "одежда",
        "обувь",
        "аксессуары",
        "бренд",
        "дизайнер",
        "коллекция",
        "показ",
        "неделя моды",
        "тренд",
        "сезон",
        "гардероб",
        "шопинг",
        "магазин",
        "распродажа",
        "скидка",
        "люкс",
        "премиум",
        "mass market",
        "vintage",
        "second hand",
        "косметика",
        "макияж",
        "уход",
        "бьюти",
        "салон",
        "парикмахер",
        "маникюр",
        "педикюр",
        "spa",
        "массаж",
    ],
    "real-estate": [
        "недвижимость",
        "квартира",
        "дом",
        "коттедж",
        "дача",
        "участок",
        "земля",
        "аренда",
        "продажа",
        "покупка",
        "ипотека",
        "застройщик",
        "новостройка",
        "вторичка",
        "риелтор",
        "агентство",
        "оценка",
        "кадастр",
        "регистрация",
        "собственность",
        "долевое",
        "жк",
        "комплекс",
        "район",
        "метро",
        "инфраструктура",
        "паркинг",
        "ремонт",
        "дизайн интерьера",
        "мебель",
    ],
    "other": [
        "разное",
        "прочее",
        "другое",
        "misc",
        "various",
    ],
}

# Синонимы для улучшения классификации
TOPIC_SYNONYMS: dict[str, list[str]] = {
    "it": ["технологии", "айти", "digital", "компьютеры", "софт", "приложения"],
    "crypto": ["крипта", "цифровые активы", "виртуальные валюты"],
    "business": ["деловой", "коммерция", "предпринимательство"],
    "marketing": ["продвижение", "реклама", "пиар"],
    "finance": ["финансовый", "денежный", "банковский"],
    "news": ["информация", "актуальное", "последнее"],
    "education": ["просвещение", "наука", "учеба"],
    "health": ["медицинский", "оздоровление", "велнес"],
    "sport": ["спортивный", "атлетика", "физкультура"],
    "travel": ["туристический", "поездки", "туризм"],
    "food": ["кулинарный", "гастрономический", "ресторанный"],
    "fashion": ["модный", "стильный", "имидж"],
    "auto": ["автомобильный", "транспорт", "машины"],
    "real-estate": ["жилой", "коммерческий", "строительство"],
}


class TopicClassifier:
    """
    Классификатор тематик Telegram-каналов.

    Использование:
        classifier = TopicClassifier()
        topic = classifier.classify("Бизнес новости и инвестиции")
    """

    # Порог уверенности для автоматической классификации
    CONFIDENCE_THRESHOLD = 0.3

    def __init__(self) -> None:
        """Инициализация классификатора."""
        self._keywords_cache: dict[str, list[str]] = {}
        self._build_keywords_cache()

    def _build_keywords_cache(self) -> None:
        """Построить кэш всех ключевых слов."""
        for topic, keywords in TOPIC_KEYWORDS.items():
            self._keywords_cache[topic] = [
                kw.lower() for kw in keywords
            ]

        # Добавляем синонимы
        for topic, synonyms in TOPIC_SYNONYMS.items():
            if topic in self._keywords_cache:
                self._keywords_cache[topic].extend(
                    [syn.lower() for syn in synonyms]
                )

    def classify(
        self,
        title: str,
        description: str | None = None,
    ) -> str:
        """
        Классифицировать канал по тематике.

        Args:
            title: Заголовок канала.
            description: Описание канала (опционально).

        Returns:
            Название тематики.
        """
        text = f"{title} {description or ''}".lower()

        # Находим совпадения по ключевым словам
        matches: list[TopicMatch] = []

        for topic, keywords in self._keywords_cache.items():
            if topic == "other":
                continue

            matched_keywords = []
            for keyword in keywords:
                if keyword in text:
                    matched_keywords.append(keyword)

            if matched_keywords:
                score = len(matched_keywords) / len(keywords)
                matches.append(
                    TopicMatch(
                        topic=topic,
                        score=score,
                        matched_keywords=matched_keywords,
                    )
                )

        # Сортируем по score
        matches.sort(key=lambda x: x.score, reverse=True)

        if matches and matches[0].score >= self.CONFIDENCE_THRESHOLD:
            return matches[0].topic

        # Если не нашли по ключевым словам, используем fuzzy matching
        if fuzz is not None and process is not None:
            topic = self._fuzzy_classify(title)
            if topic:
                return topic

        return "other"

    def _fuzzy_classify(self, text: str) -> str | None:
        """
        Нечёткая классификация с помощью rapidfuzz.

        Args:
            text: Текст для классификации.

        Returns:
            Название тематики или None.
        """
        if fuzz is None or process is None:
            return None

        text_lower = text.lower()
        best_match: tuple[str, float] | None = None

        for topic in self._keywords_cache.keys():
            if topic == "other":
                continue

            # Сравниваем с каждым ключевым словом
            for keyword in self._keywords_cache[topic]:
                ratio = fuzz.partial_ratio(text_lower, keyword)
                if ratio > 80:  # Порог fuzzy matching
                    if best_match is None or ratio > best_match[1]:
                        best_match = (topic, ratio)

        if best_match and best_match[1] > 80:
            return best_match[0]

        return None

    def classify_batch(
        self,
        channels: list[tuple[str, str | None]],
    ) -> list[str]:
        """
        Классифицировать несколько каналов.

        Args:
            channels: Список кортежей (title, description).

        Returns:
            Список тематик.
        """
        return [
            self.classify(title, description)
            for title, description in channels
        ]

    def get_topic_description(self, topic: str) -> str:
        """
        Получить описание тематики.

        Args:
            topic: Название тематики.

        Returns:
            Описание.
        """
        descriptions = {
            "business": "Бизнес, предпринимательство, инвестиции",
            "it": "IT, программирование, технологии",
            "news": "Новости, политика, общество",
            "crypto": "Криптовалюты, блокчейн, трейдинг",
            "marketing": "Маркетинг, реклама, продвижение",
            "finance": "Финансы, банки, инвестиции",
            "education": "Образование, наука, обучение",
            "lifestyle": "Образ жизни, хобби, развлечения",
            "health": "Здоровье, медицина, спорт",
            "sport": "Спорт, соревнования, атлетика",
            "auto": "Автомобили, транспорт, дороги",
            "travel": "Путешествия, туризм, отдых",
            "food": "Еда, кулинария, рестораны",
            "fashion": "Мода, стиль, красота",
            "real-estate": "Недвижимость, строительство, жилье",
            "other": "Прочее",
        }
        return descriptions.get(topic, "Неизвестная тематика")

    def get_all_topics(self) -> list[str]:
        """
        Получить список всех доступных тематик.

        Returns:
            Список тематик.
        """
        return [
            topic
            for topic in self._keywords_cache.keys()
            if topic != "other"
        ]


# Глобальный экземпляр
_classifier: Optional[TopicClassifier] = None


def get_classifier() -> TopicClassifier:
    """Получить глобальный экземпляр классификатора."""
    global _classifier
    if _classifier is None:
        _classifier = TopicClassifier()
    return _classifier


def classify_topic(title: str, description: str | None = None) -> str:
    """
    Классифицировать канал по тематике.

    Args:
        title: Заголовок канала.
        description: Описание канала.

    Returns:
        Название тематики.
    """
    return get_classifier().classify(title, description)
