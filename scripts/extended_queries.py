# Расширенные поисковые запросы для парсинга Telegram
# Включает: обычные, специфичные, по описаниям, по постам

SEARCH_QUERIES_EXTENDED = [
    # ========== КРИПТОВАЛЮТЫ (30 запросов) ==========
    # Основные
    "crypto", "bitcoin", "ethereum", "trading",
    "crypto news", "bitcoin news", "crypto trading",
    "defi", "nft", "web3", "blockchain",
    
    # Сигналы и трейдинг
    "crypto signals", "bitcoin signals", "trading signals",
    "pump signals", "binance signals", "forex signals",
    "day trading", "scalping", "swing trading",
    
    # Специфичные русские фразы
    "крипта", "биткоин", "эфириум", "трейдинг",
    "сигналы крипто", "памп сигналы", "бинанс",
    "крипто новости", "блокчейн новости",
    
    # По описаниям каналов
    "cryptocurrency news and analysis",
    "bitcoin trading signals channel",
    "ethereum community russian",
    "defi yields and staking",
    
    # ========== БИЗНЕС И ФИНАНСЫ (25 запросов) ==========
    # Основные
    "business", "finance", "investing", "stocks",
    "business news", "financial news", "investment tips",
    
    # Специфичные
    "startup news", "venture capital", "angel investing",
    "stock market analysis", "forex trading", "options trading",
    
    # Русские фразы
    "бизнес новости", "финансы", "инвестиции",
    "фондовый рынок", "трейдинг обучение",
    "бизнес идеи", "стартап россия",
    
    # По описаниям
    "business and finance news",
    "investment strategies and tips",
    "russian business community",
    
    # ========== ТЕХНОЛОГИИ IT (30 запросов) ==========
    # Основные
    "tech", "technology", "programming", "coding",
    "tech news", "programming tips", "software development",
    
    # Языки программирования
    "python", "javascript", "golang", "rust",
    "java developer", "cpp", "typescript",
    
    # Технологии
    "ai", "machine learning", "data science",
    "devops", "docker", "kubernetes", "cloud",
    
    # Русские фразы
    "программирование", "разработка", "айти",
    "программисты", "код", "технологии новости",
    "искусственный интеллект", "дата сайенс",
    
    # По описаниям
    "software developers community",
    "programming tutorials and tips",
    "russian it community",
    
    # ========== МАРКЕТИНГ SMM (20 запросов) ==========
    # Основные
    "marketing", "smm", "digital marketing",
    "marketing tips", "social media marketing",
    
    # Специфичные
    "content marketing", "email marketing", "seo",
    "ppc advertising", "conversion optimization",
    
    # Русские фразы
    "маркетинг", "смм", "таргетинг",
    "контекстная реклама", "продвижение",
    "маркетинг советы", "бизнес маркетинг",
    
    # По описаниям
    "marketing strategies and tools",
    "smm tips for business",
    
    # ========== НОВОСТИ СМИ (20 запросов) ==========
    # Основные
    "news", "breaking news", "world news",
    "politics", "economy", "society",
    
    # Специфичные
    "independent media", "investigative journalism",
    "political analysis", "economic news",
    
    # Русские фразы
    "новости", "политика", "экономика",
    "общество", "происшествия",
    "независимые новости", "журналистика",
    
    # По описаниям
    "daily news and analysis",
    "independent journalism",
    
    # ========== ОБРАЗОВАНИЕ НАУКА (15 запросов) ==========
    "education", "science", "online courses",
    "learning", "tutorials", "lectures",
    "образование", "наука", "курсы",
    "лекции", "онлайн обучение",
    
    # ========== ЗДОРОВЬЕ СПОРТ (15 запросов) ==========
    "health", "fitness", "sport",
    "workout", "nutrition", "wellness",
    "здоровье", "фитнес", "спорт",
    "тренировки", "питание", "зож",
    
    # ========== ПУТЕШЕСТВИЯ (10 запросов) ==========
    "travel", "tourism", "adventure",
    "путешествия", "туризм", "отдых",
    "travel blog", "travel tips",
    
    # ========== ЕДА РЕЦЕПТЫ (10 запросов) ==========
    "food", "recipes", "cooking",
    "еда", "рецепты", "готовка",
    "food blog", "restaurant reviews",
    
    # ========== МОДА КРАСОТА (10 запросов) ==========
    "fashion", "beauty", "style",
    "мода", "красота", "стиль",
    "fashion blog", "beauty tips",
    
    # ========== РАЗВЛЕЧЕНИЯ (15 запросов) ==========
    "entertainment", "movies", "music",
    "развлечения", "кино", "музыка",
    "celebrity news", "movie reviews",
    
    # ========== ИГРЫ (10 запросов) ==========
    "gaming", "games", "esports",
    "игры", "гейминг", "киберспорт",
    "game reviews", "gaming news",
    
    # ========== СПЕЦИФИЧНЫЕ НЕОБЫЧНЫЕ (20 запросов) ==========
    # Сленг и аббревиатуры
    "имхо", "спс", "пож", "мб",
    "топ", "лучшее", "подборка",
    
    # Эмодзи в названиях
    "🔥", "💰", "📈", "🚀",
    "💎", "🎯", "⚡️",
    
    # Специфичные фразы
    "авторский канал", "личный блог",
    "без цензуры", "только правда",
    "инсайды", "эксклюзив",
    
    # По описаниям с ключевыми словами
    "подпишись на канал", "вступай в чат",
    "канал для своих", "закрытый клуб",
]

# Запросы для поиска по постам (ищем каналы где эти слова в постах)
POST_SEARCH_QUERIES = [
    # Крипто сленг
    "холд", "шорт", "лонг", "ликвидка",
    "газ", "комиссия", "стейкинг", "фарминг",
    
    # Бизнес сленг
    "дедлайн", "митинг", "стартап", "инвестор",
    "прибыль", "оборот", "маржа", "лиды",
    
    # IT сленг
    "деплой", "релиз", "баг", "фича",
    "рефакторинг", "код ревью", "спринт",
    
    # Маркетинг сленг
    "лидогенерация", "конверсия", "ctr", "cpa",
    "роминг", "креативы", "таргет",
    
    # Общие русские слова
    "друзья", "подписчики", "канал", "чат",
    "новость", "важно", "внимание", "срочно",
]

# Категории для группировки
QUERY_CATEGORIES = {
    "crypto": SEARCH_QUERIES_EXTENDED[:30],
    "business": SEARCH_QUERIES_EXTENDED[30:55],
    "it": SEARCH_QUERIES_EXTENDED[55:85],
    "marketing": SEARCH_QUERIES_EXTENDED[85:105],
    "news": SEARCH_QUERIES_EXTENDED[105:125],
    "education": SEARCH_QUERIES_EXTENDED[125:140],
    "health": SEARCH_QUERIES_EXTENDED[140:155],
    "travel": SEARCH_QUERIES_EXTENDED[155:165],
    "food": SEARCH_QUERIES_EXTENDED[165:175],
    "fashion": SEARCH_QUERIES_EXTENDED[175:185],
    "entertainment": SEARCH_QUERIES_EXTENDED[185:200],
    "gaming": SEARCH_QUERIES_EXTENDED[200:210],
    "specific": SEARCH_QUERIES_EXTENDED[210:],
}
