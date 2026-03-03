"""
Расширенные подкатегории каналов.

Базовые топики (поле TelegramChat.topic) — 6 значений из seed:
  бизнес, маркетинг, it, финансы, крипто, образование

Подкатегории добавляются поверх через поле subcategory в TelegramChat.
Используются в:
  - Парсере (автоклассификация по ключевым словам)
  - API /api/channels/stats
  - Скрипте бэкфилла
"""

# Подкатегории сгруппированы по базовому топику
# Ключи верхнего уровня = реальные значения TelegramChat.topic
SUBCATEGORIES: dict[str, dict[str, str]] = {
    "бизнес": {
        "startup":          "Стартапы и инновации",
        "small_business":   "Малый бизнес и ИП",
        "franchise":        "Франчайзинг",
        "personal_finance": "Личные финансы",
        "real_estate":      "Недвижимость",
    },
    "маркетинг": {
        "digital":    "Digital-маркетинг",
        "smm":        "SMM и соцсети",
        "target_ads": "Таргетированная реклама",
        "sales":      "Воронки продаж и CRM",
        "seo":        "SEO и контент",
    },
    "it": {
        "programming": "Программирование",
        "web_dev":     "Веб-разработка",
        "mobile_dev":  "Мобильная разработка",
        "ai_ml":       "ИИ и машинное обучение",
        "data":        "Data Science и аналитика",
        "devops":      "DevOps и облака",
        "security":    "Кибербезопасность",
        "gamedev":     "Разработка игр",
    },
    "финансы": {
        "investments":  "Инвестиции и трейдинг",
        "stock_market": "Фондовый рынок",
        "banking":      "Банки и вклады",
        "insurance":    "Страхование",
    },
    "крипто": {
        "defi":     "DeFi и протоколы",
        "nft":      "NFT",
        "trading":  "Крипто-трейдинг",
        "bitcoin":  "Bitcoin и Ethereum",
    },
    "образование": {
        "online_courses": "Онлайн-курсы",
        "languages":      "Изучение языков",
        "professional":   "Профессии и переквалификация",
        "kids":           "Детское образование",
        "university":     "Высшее образование",
    },
}

# Плоский маппинг: код подкатегории → название
ALL_SUBCATEGORIES: dict[str, str] = {
    subcat: name
    for subcats in SUBCATEGORIES.values()
    for subcat, name in subcats.items()
}

# Маппинг: подкатегория → родительский топик
SUBCATEGORY_TO_TOPIC: dict[str, str] = {
    subcat: parent
    for parent, subcats in SUBCATEGORIES.items()
    for subcat in subcats
}

# Ключевые слова для автоклассификации
# Используются в classify_subcategory()
SUBCATEGORY_KEYWORDS: dict[str, list[str]] = {
    # бизнес
    "startup":        ["стартап", "startup", "инновации", "mvp", "фаундер", "раунд", "инвестор"],
    "small_business": ["малый бизнес", "ИП", "предприниматель", "открыть бизнес", "самозанятый"],
    "franchise":      ["франшиза", "франчайзинг", "франчайзи"],
    "personal_finance": ["личный бюджет", "экономия", "копить", "финансовая грамотность"],
    "real_estate":    ["недвижимость", "квартира", "ипотека", "аренда", "жильё"],
    # маркетинг
    "digital":        ["digital", "диджитал", "интернет-маркетинг", "пиар", "pr"],
    "smm":            ["smm", "instagram", "тикток", "reels", "контент-маркетинг", "инстаграм"],
    "target_ads":     ["таргет", "таргетинг", "facebook ads", "vk реклама", "кабинет рекламы"],
    "sales":          ["воронка", "crm", "продажи", "лиды", "конверсия"],
    "seo":            ["seo", "сео", "продвижение сайта", "семантика", "позиции"],
    # it
    "programming":    ["python", "javascript", "golang", "rust", "leetcode", "алгоритмы"],
    "web_dev":        ["react", "vue", "angular", "фронтенд", "backend", "fullstack"],
    "mobile_dev":     ["ios", "android", "flutter", "swift", "kotlin", "мобильная разработка"],
    "ai_ml":          ["chatgpt", "llm", "нейросети", "machine learning", "openai", "claude", "ии"],
    "data":           ["data science", "pandas", "sql", "аналитик данных", "bi", "дашборд"],
    "devops":         ["docker", "kubernetes", "k8s", "ci/cd", "devops", "aws", "gcp", "azure"],
    "security":       ["кибербезопасность", "пентест", "уязвимости", "hacking", "osint"],
    "gamedev":        ["unity", "unreal", "gamedev", "разработка игр", "геймдев", "godot"],
    # финансы
    "investments":    ["инвестиции", "портфель", "дивиденды", "etf", "пиф", "доходность"],
    "stock_market":   ["акции", "биржа", "ipo", "фондовый", "мосбиржа", "tinkoff"],
    "banking":        ["банк", "вклад", "кредит", "ставка", "сбербанк", "депозит"],
    "insurance":      ["страхование", "страховка", "полис", "росгосстрах", "ингосстрах"],
    # крипто
    "defi":           ["defi", "yield farming", "ликвидность", "протокол", "uniswap"],
    "nft":            ["nft", "нфт", "метавселенная", "opensea"],
    "trading":        ["трейдинг", "скальпинг", "технический анализ", "ta", "торговля"],
    "bitcoin":        ["bitcoin", "биткоин", "ethereum", "эфириум", "btc", "eth"],
    # образование
    "online_courses": ["курс", "обучение онлайн", "урок", "воркшоп", "вебинар"],
    "languages":      ["английский", "немецкий", "china", "язык", "learn english"],
    "professional":   ["профессия", "переквалификация", "смена профессии", "карьера"],
    "kids":           ["детское", "дети", "школьники", "подготовка к школе", "репетитор"],
    "university":     ["университет", "вуз", "абитуриент", "егэ", "бакалавр", "магистр"],
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

    if topic_lower not in SUBCATEGORIES:
        return None

    text = f"{title or ''} {description or ''}".lower()
    valid_subcats = set(SUBCATEGORIES[topic_lower].keys())

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
