"""
Расширенные подкатегории каналов.

Базовые топики (поле TelegramChat.topic) — 6 значений из seed:
  бизнес, маркетинг, it, финансы, крипто, образование

Подкатегории добавляются поверх через поле subcategory в TelegramChat.
Используются в:
  - Парсере (автоклассификация по ключевым словам)
  - API /api/channels/stats
  - Скрипте бэкфилла

Спринт 3: Данные хранятся в БД (topic_categories), этот файл — FALLBACK.
"""


# Подкатегории сгруппированы по базовому топику
# Ключи верхнего уровня = реальные значения TelegramChat.topic
# Это FALLBACK на случай недоступности БД
SUBCATEGORIES: dict[str, dict[str, str]] = {
    "business": {
        "startup": "Стартапы и инновации",
        "small_business": "Малый бизнес и ИП",
        "franchise": "Франчайзинг",
        "personal_finance": "Личные финансы",
        "real_estate": "Недвижимость",
    },
    "marketing": {
        "digital": "Digital-маркетинг",
        "smm": "SMM и соцсети",
        "target_ads": "Таргетированная реклама",
        "sales": "Воронки продаж и CRM",
        "seo": "SEO и контент",
    },
    "it": {
        "programming": "Программирование",
        "web_dev": "Веб-разработка",
        "mobile_dev": "Мобильная разработка",
        "ai_ml": "ИИ и машинное обучение",
        "data": "Data Science и аналитика",
        "devops": "DevOps и облака",
        "security": "Кибербезопасность",
        "gamedev": "Разработка игр",
    },
    "finance": {
        "investments": "Инвестиции и трейдинг",
        "stock_market": "Фондовый рынок",
        "banking": "Банки и вклады",
        "insurance": "Страхование",
    },
    "crypto": {
        "defi": "DeFi и протоколы",
        "nft": "NFT",
        "trading": "Крипто-трейдинг",
        "bitcoin": "Bitcoin и Ethereum",
    },
    "education": {
        "online_courses": "Онлайн-курсы",
        "languages": "Изучение языков",
        "professional": "Профессии и переквалификация",
        "kids": "Детское образование",
        "university": "Высшее образование",
    },
    "health": {
        "fitness": "Фитнес и спорт",
        "nutrition": "Питание и диеты",
        "mental_health": "Психическое здоровье",
        "medicine": "Медицина и здоровье",
    },
    "news": {
        "politics": "Политика",
        "world": "Мировые новости",
        "tech_news": "Технологические новости",
        "economy": "Экономика",
    },
    "other": {
        "humor": "Юмор",
        "lifestyle": "Образ жизни",
        "hobbies": "Хобби",
    },
}

# Плоский маппинг: код подкатегории → название
ALL_SUBCATEGORIES: dict[str, str] = {
    subcat: name for subcats in SUBCATEGORIES.values() for subcat, name in subcats.items()
}

# Маппинг: подкатегория → родительский топик
SUBCATEGORY_TO_TOPIC: dict[str, str] = {
    subcat: parent for parent, subcats in SUBCATEGORIES.items() for subcat in subcats
}

# Ключевые слова для автоклассификации
# Используются в classify_subcategory()
SUBCATEGORY_KEYWORDS: dict[str, list[str]] = {
    # бизнес
    "startup": ["стартап", "startup", "инновации", "mvp", "фаундер", "раунд", "инвестор"],
    "small_business": ["малый бизнес", "ИП", "предприниматель", "открыть бизнес", "самозанятый"],
    "franchise": ["франшиза", "франчайзинг", "франчайзи"],
    "personal_finance": ["личный бюджет", "экономия", "копить", "финансовая грамотность"],
    "real_estate": ["недвижимость", "квартира", "ипотека", "аренда", "жильё"],
    # маркетинг
    "digital": ["digital", "диджитал", "интернет-маркетинг", "пиар", "pr"],
    "smm": ["smm", "instagram", "тикток", "reels", "контент-маркетинг", "инстаграм"],
    "target_ads": ["таргет", "таргетинг", "facebook ads", "vk реклама", "кабинет рекламы"],
    "sales": ["воронка", "crm", "продажи", "лиды", "конверсия"],
    "seo": ["seo", "сео", "продвижение сайта", "семантика", "позиции"],
    # it
    "programming": ["python", "javascript", "golang", "rust", "leetcode", "алгоритмы"],
    "web_dev": ["react", "vue", "angular", "фронтенд", "backend", "fullstack"],
    "mobile_dev": ["ios", "android", "flutter", "swift", "kotlin", "мобильная разработка"],
    "ai_ml": ["chatgpt", "llm", "нейросети", "machine learning", "openai", "claude", "ии"],
    "data": ["data science", "pandas", "sql", "аналитик данных", "bi", "дашборд"],
    "devops": ["docker", "kubernetes", "k8s", "ci/cd", "devops", "aws", "gcp", "azure"],
    "security": ["кибербезопасность", "пентест", "уязвимости", "hacking", "osint"],
    "gamedev": ["unity", "unreal", "gamedev", "разработка игр", "геймдев", "godot"],
    # финансы
    "investments": ["инвестиции", "портфель", "дивиденды", "etf", "пиф", "доходность"],
    "stock_market": ["акции", "биржа", "ipo", "фондовый", "мосбиржа", "tinkoff"],
    "banking": ["банк", "вклад", "кредит", "ставка", "сбербанк", "депозит"],
    "insurance": ["страхование", "страховка", "полис", "росгосстрах", "ингосстрах"],
    # крипто
    "defi": ["defi", "yield farming", "ликвидность", "протокол", "uniswap"],
    "nft": ["nft", "нфт", "метавселенная", "opensea"],
    "trading": ["трейдинг", "скальпинг", "технический анализ", "ta", "торговля"],
    "bitcoin": ["bitcoin", "биткоин", "ethereum", "эфириум", "btc", "eth"],
    # образование
    "online_courses": ["курс", "обучение онлайн", "урок", "воркшоп", "вебинар"],
    "languages": ["английский", "немецкий", "china", "язык", "learn english"],
    "professional": ["профессия", "переквалификация", "смена профессии", "карьера"],
    "kids": ["детское", "дети", "школьники", "подготовка к школе", "репетитор"],
    "university": ["университет", "вуз", "абитуриент", "егэ", "бакалавр", "магистр"],
    # здоровье
    "fitness": ["фитнес", "спорт", "тренировки", "зал", "качалка", "воркаут"],
    "nutrition": ["питание", "диета", "пп", "еда", "здоровое питание"],
    "mental_health": ["психология", "психотерапия", "ментальное здоровье", "стресс"],
    "medicine": ["медицина", "здоровье", "врач", "болезни", "лечение"],
}


def classify_subcategory(
    title: str,
    description: str,
    topic: str,
) -> str | None:
    """
    Определить подкатегорию канала по ключевым словам.

    Args:
        title:       TelegramChat.title
        description: TelegramChat.description
        topic:       TelegramChat.topic — базовая категория

    Returns:
        Код подкатегории (e.g. "smm", "devops") или None
    """
    if not topic:
        return None

    # Нормализуем topic к нижнему регистру для сравнения
    topic_lower = topic.lower()

    # Маппинг русских тем на английские ключи
    topic_mapping = {
        "бизнес": "business",
        "финансы": "finance",
        "крипто": "crypto",
        "образование": "education",
        "маркетинг": "marketing",
        "новости": "news",
        "другое": "other",
        "здоровье": "health",
    }
    
    # Используем маппинг если topic на русском
    topic_key = topic_mapping.get(topic_lower, topic_lower)

    if topic_key not in SUBCATEGORIES:
        return None

    text = f"{title or ''} {description or ''}".lower()
    valid_subcats = set(SUBCATEGORIES[topic_key].keys())

    scores: dict[str, int] = {}
    for subcat, keywords in SUBCATEGORY_KEYWORDS.items():
        if subcat not in valid_subcats:
            continue
        score = sum(1 for kw in keywords if kw in text)
        if score > 0:
            scores[subcat] = score

    if not scores:
        return None

    return max(scores, key=lambda k: scores[k])


# ═══════════════════════════════════════════════════════════════
# Sprint 3: Async функции для работы с БД
# ═══════════════════════════════════════════════════════════════

async def get_subcategories_from_db(topic: str) -> dict[str, str] | None:
    """
    Получить подкатегории для топика из БД.

    Args:
        topic: Название топика.

    Returns:
        dict {subcategory: display_name} или None.
    """
    try:
        from src.db.repositories.category_repo import CategoryRepository
        from src.db.session import async_session_factory

        async with async_session_factory() as session:
            repo = CategoryRepository(session)
            categories = await repo.get_subcategories(topic)

            if not categories:
                return None

            return {cat.subcategory: cat.display_name_ru for cat in categories}

    except Exception:
        # Fallback на статические данные
        return SUBCATEGORIES.get(topic)


async def get_all_topics_from_db() -> list[str]:
    """
    Получить все топики из БД.

    Returns:
        Список топиков.
    """
    try:
        from src.db.repositories.category_repo import CategoryRepository
        from src.db.session import async_session_factory

        async with async_session_factory() as session:
            repo = CategoryRepository(session)
            return await repo.get_all_topics()

    except Exception:
        # Fallback на статические данные
        return list(SUBCATEGORIES.keys())


async def get_categories_dict_from_db() -> dict[str, dict[str, str]]:
    """
    Получить все категории в виде вложенного dict из БД.

    Returns:
        dict {topic: {subcategory: display_name}}.
    """
    try:
        from src.db.repositories.category_repo import CategoryRepository
        from src.db.session import async_session_factory

        async with async_session_factory() as session:
            repo = CategoryRepository(session)
            return await repo.get_categories_dict()

    except Exception:
        # Fallback на статические данные
        return SUBCATEGORIES
