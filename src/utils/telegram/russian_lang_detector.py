"""
Детектор русского языка для фильтрации каналов.
"""

import re

# Часто используемые русские слова (маркеры русского языка)
RUSSIAN_MARKERS = {
    "и",
    "в",
    "не",
    "на",
    "я",
    "что",
    "этот",
    "как",
    "а",
    "то",
    "все",
    "она",
    "так",
    "его",
    "но",
    "да",
    "ты",
    "к",
    "у",
    "же",
    "вы",
    "бы",
    "по",
    "только",
    "он",
    "с",
    "м",
    "из",
    "нам",
    "при",
    "о",
    "ни",
    "под",
    "них",
    "была",
    "было",
    "были",
    "будет",
    "будут",
    "будь",
    "который",
    "которая",
    "которые",
    "которого",
    "которой",
    "которых",
    "которому",
    "которым",
    "котором",
    "какой",
    "какая",
    "какое",
    "какие",
    "какого",
    "каким",
    "каких",
    "свой",
    "своя",
    "своё",
    "свои",
    "своего",
    "своей",
    "своём",
    "своим",
    "своих",
    "себя",
    "себе",
    "собой",
    "собою",
    "кто",
    "куда",
    "откуда",
    "где",
    "когда",
    "зачем",
    "почему",
    "мой",
    "моя",
    "моё",
    "мои",
    "твой",
    "твоя",
    "твоё",
    "твои",
    "наш",
    "наша",
    "наше",
    "наши",
    "ваш",
    "ваша",
    "ваше",
    "ваши",
    "тот",
    "та",
    "те",
    "того",
    "той",
    "том",
    "тем",
    "тех",
    "этого",
    "этой",
    "этом",
    "этим",
    "этих",
    "эти",
    "эта",
    "это",
    "сам",
    "сама",
    "само",
    "сами",
    "самого",
    "самой",
    "самом",
    "самим",
    "самих",
    "другой",
    "другая",
    "другое",
    "другие",
    "другого",
    "другом",
    "весь",
    "вся",
    "всё",
    "всего",
    "всей",
    "всём",
    "всем",
    "всех",
    "быть",
    "был",
    "буду",
    "будешь",
    "будем",
    "будете",
    "есть",
    "говорить",
    "говорю",
    "говоришь",
    "говорит",
    "говорим",
    "говорите",
    "говорят",
    "делать",
    "делаю",
    "делаешь",
    "делает",
    "делаем",
    "делаете",
    "делают",
    "знать",
    "знаю",
    "знаешь",
    "знает",
    "знаем",
    "знаете",
    "знают",
    "мочь",
    "могу",
    "можешь",
    "может",
    "можем",
    "можете",
    "могут",
    "хотеть",
    "хочу",
    "хочешь",
    "хочет",
    "хотим",
    "хотите",
    "хотят",
    "видеть",
    "вижу",
    "видишь",
    "видит",
    "видим",
    "видите",
    "видят",
    "понимать",
    "понимаю",
    "понимаешь",
    "понимает",
    "понимаем",
    "понимаете",
    "понимают",
    "россия",
    "москва",
    "санкт-петербург",
    "казань",
    "новосибирск",
    "екатеринбург",
    "украина",
    "киев",
    "минск",
    "беларусь",
    "казахстан",
    "алматы",
    "русский",
    "русская",
    "русское",
    "русские",
    "новости",
    "бизнес",
    "маркетинг",
    "продажи",
    "инвестиции",
    "финансы",
    "канал",
    "телеграм",
    "telegram",
    "чат",
    "группа",
}

# Английские маркеры (для исключения)
ENGLISH_MARKERS = {
    "the",
    "and",
    "or",
    "but",
    "in",
    "on",
    "at",
    "to",
    "for",
    "of",
    "with",
    "by",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "have",
    "has",
    "had",
    "do",
    "does",
    "did",
    "will",
    "would",
    "could",
    "should",
    "may",
    "might",
    "must",
    "i",
    "you",
    "he",
    "she",
    "it",
    "we",
    "they",
    "my",
    "your",
    "his",
    "her",
    "its",
    "our",
    "their",
    "this",
    "that",
    "these",
    "those",
    "what",
    "where",
    "when",
    "why",
    "how",
    "who",
    "which",
    "all",
    "any",
    "some",
    "no",
    "not",
    "only",
    "own",
    "same",
    "can",
    "get",
    "make",
    "go",
    "know",
    "take",
    "see",
    "come",
    "think",
    "look",
    "want",
    "give",
    "use",
    "find",
    "tell",
    "ask",
    "work",
    "seem",
    "feel",
    "try",
    "leave",
    "call",
    "good",
    "new",
    "first",
    "last",
    "long",
    "great",
    "little",
    "other",
    "old",
    "right",
    "big",
    "high",
    "different",
    "small",
    "large",
    "next",
    "early",
    "young",
    "important",
    "channel",
    "telegram",
    "chat",
    "group",
    "news",
    "business",
    "crypto",
    "bitcoin",
    "trading",
    "investment",
    "marketing",
}

# Чёрный список англоязычных ключей (автоматическая блокировка)
# Каналы с этими словами в названии или описании считаются англоязычными
ENGLISH_BLACKLIST = [
    # Криптовалюты и трейдинг
    "crypto signals",
    "crypto news",
    "crypto trading",
    "bitcoin signals",
    "bitcoin trading",
    "btc trading",
    "trading signals",
    "forex signals",
    "forex trading",
    "pump signals",
    "pump group",
    "binance signals",
    "nft drops",
    "nft collection",
    "nft mint",
    "defi yields",
    "yield farming",
    "staking rewards",
    "altcoins gems",
    "crypto gems",
    "100x gems",
    # Бизнес и финансы
    "business insider",
    "business news",
    "financial times",
    "wall street",
    "stock market",
    "stock trading",
    "investing.com",
    "bloomberg",
    "reuters",
    # Маркетинг и SMM
    "marketing pro",
    "digital marketing",
    "social media marketing",
    "smm tips",
    "smm tools",
    "smm services",
    "seo tips",
    "seo tools",
    "content marketing",
    # Технологии
    "tech crunch",
    "tech news",
    "tech daily",
    "ai news",
    "artificial intelligence",
    "machine learning",
    "startup news",
    "startup digest",
    "y combinator",
    # Новости
    "daily news",
    "world news",
    "breaking news",
    "news today",
    "news update",
    "news daily",
    "cnn",
    "bbc",
    "reuters",
    "associated press",
    # Развлечения
    "hollywood news",
    "celebrity news",
    "entertainment tonight",
    "music news",
    "movie trailers",
    "netflix series",
    # Спорт
    "espn",
    "sports news",
    "football news",
    "basketball news",
    "nba news",
    "premier league",
    # Путешествия
    "travel blog",
    "travel guide",
    "travel tips",
    "lonely planet",
    "tripadvisor",
    "booking.com",
    # Еда
    "food network",
    "food blog",
    "recipe blog",
    "tasty recipes",
    "buzzfeed food",
    # Мода и красота
    "vogue",
    "fashion week",
    "fashion blog",
    "beauty tips",
    "makeup tutorial",
    "skincare routine",
    # Образование
    "online courses",
    "coursera",
    "udemy",
    "learn english",
    "english course",
    "english lessons",
    "duolingo",
    "ted talks",
    "masterclass",
    # Недвижимость
    "real estate",
    "property for sale",
    "luxury homes",
    "zillow",
    "realtor.com",
    "property investment",
    # Автомобили
    "car news",
    "auto blog",
    "supercars",
    "tesla news",
    "electric vehicles",
    "car review",
    # Здоровье
    "health tips",
    "medical news",
    "wellness blog",
    "fitness tips",
    "gym workout",
    "healthline",
    # Наука
    "science daily",
    "nature journal",
    "science news",
    "scientific american",
    "new scientist",
    # Игры
    "gaming news",
    "pc gamer",
    "ign",
    "game reviews",
    "esports news",
    "twitch streamers",
    # Искусство
    "art news",
    "contemporary art",
    "art gallery",
    "photography blog",
    "photo daily",
    "artistic",
    # Политика
    "political news",
    "politics today",
    "government news",
    "election news",
    "capitol hill",
    "white house",
]

# Кириллические символы
CYRILLIC_PATTERN = re.compile(r"[\u0400-\u04FF]+")

# Минимальное количество слов для анализа
MIN_WORDS_FOR_ANALYSIS = 3


def is_in_english_blacklist(text: str) -> bool:
    """
    Проверить, содержится ли текст в чёрном списке англоязычных ключей.

    Args:
        text: Текст для проверки (название или описание канала).

    Returns:
        True если текст содержит запрещённый англоязычный ключ.
    """
    if not text:
        return False

    text_lower = text.lower()

    return any(blacklist_item in text_lower for blacklist_item in ENGLISH_BLACKLIST)


def detect_language_from_posts(post_texts: list[str]) -> tuple[str, float]:
    """
    Определить язык по набору постов канала.

    Args:
        post_texts: Список текстов постов (последние 10-20 постов).

    Returns:
        Кортеж (language_code, russian_score):
        - language_code: "ru", "en", "mixed"
        - russian_score: оценка от 0.0 до 1.0
    """
    if not post_texts:
        return "unknown", 0.5

    # Проверяем каждый пост
    russian_count = 0
    english_count = 0
    total_russian_score = 0.0

    for post_text in post_texts:
        if not post_text or len(post_text.strip()) < 10:
            continue

        # Быстрая проверка по чёрному списку
        if is_in_english_blacklist(post_text):
            english_count += 1
            continue

        # Проверяем язык поста
        detector = RussianLanguageDetector()
        if detector.is_russian(post_text):
            russian_count += 1
            total_russian_score += detector.get_language_score(post_text)[0]
        else:
            english_count += 1

    # Если постов мало, возвращаем unknown
    total_analyzed = russian_count + english_count
    if total_analyzed < 3:
        return "unknown", 0.5

    # Вычисляем соотношение
    russian_ratio = russian_count / total_analyzed
    avg_russian_score = total_russian_score / max(russian_count, 1)

    if russian_ratio >= 0.7:
        return "ru", avg_russian_score
    elif russian_ratio <= 0.3:
        return "en", 1.0 - avg_russian_score
    else:
        return "mixed", 0.5


class RussianLanguageDetector:
    """
    Детектор русского языка для текста.

    Usage:
        detector = RussianLanguageDetector()
        if detector.is_russian(text):
            # Текст на русском
    """

    def __init__(self, russian_threshold: float = 0.3, english_threshold: float = 0.5):
        """
        Инициализация детектора.

        Args:
            russian_threshold: Порог русских слов (0.3 = 30% слов должны быть русскими)
            english_threshold: Порог английских слов для исключения (0.5 = 50%)
        """
        self.russian_threshold = russian_threshold
        self.english_threshold = english_threshold

    def extract_words(self, text: str) -> list[str]:
        """
        Извлечь слова из текста.

        Args:
            text: Текст для анализа.

        Returns:
            Список слов в нижнем регистре.
        """
        if not text:
            return []

        # Приводим к нижнему регистру и разбиваем на слова
        text = text.lower()
        words = re.findall(r"\b\w+\b", text)
        return words

    def is_russian(self, text: str) -> bool:
        """
        Проверить, является ли текст русским.

        Args:
            text: Текст для проверки.

        Returns:
            True если текст на русском языке.
        """
        if not text:
            return False

        words = self.extract_words(text)

        if len(words) < MIN_WORDS_FOR_ANALYSIS:
            # Слишком короткий текст - проверяем по кириллице
            return bool(CYRILLIC_PATTERN.search(text))

        russian_count = sum(1 for word in words if word in RUSSIAN_MARKERS)
        english_count = sum(1 for word in words if word in ENGLISH_MARKERS)

        russian_ratio = russian_count / len(words)
        english_ratio = english_count / len(words)

        # Если больше 50% английских слов - точно не русский
        if english_ratio > self.english_threshold:
            return False

        # Если больше 30% русских слов - это русский текст
        return russian_ratio >= self.russian_threshold

    def get_language_score(self, text: str) -> tuple[float, float]:
        """
        Получить оценку языка (русский, английский).

        Args:
            text: Текст для анализа.

        Returns:
            Кортеж (russian_score, english_score) от 0 до 1.
        """
        if not text:
            return 0.0, 0.0

        words = self.extract_words(text)

        if not words:
            return 0.0, 0.0

        russian_count = sum(1 for word in words if word in RUSSIAN_MARKERS)
        english_count = sum(1 for word in words if word in ENGLISH_MARKERS)

        return russian_count / len(words), english_count / len(words)


# Синглтон
russian_detector = RussianLanguageDetector(
    russian_threshold=0.25,  # 25% русских слов достаточно
    english_threshold=0.4,  # 40% английских слов - уже не русский
)


def is_russian_text(text: str) -> bool:
    """
    Быстрая проверка текста на русский язык.

    Args:
        text: Текст для проверки.

    Returns:
        True если текст на русском.
    """
    return russian_detector.is_russian(text)


def get_russian_score(text: str) -> float:
    """
    Получить оценку русского языка (0-1).

    Args:
        text: Текст для проверки.

    Returns:
        Оценка от 0 до 1.
    """
    russian_score, _ = russian_detector.get_language_score(text)
    return russian_score


def is_english_blacklisted(text: str) -> bool:
    """
    Проверить текст по чёрному списку англоязычных ключей.

    Args:
        text: Текст для проверки.

    Returns:
        True если текст в чёрном списке.
    """
    return is_in_english_blacklist(text)
