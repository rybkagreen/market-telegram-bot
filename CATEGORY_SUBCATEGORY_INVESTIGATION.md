# 🔍 ГЛУБОКОЕ ИССЛЕДОВАНИЕ ПРОБЛЕМЫ: КАТЕГОРИИ vs ПОДКАТЕГОРИИ

**Дата:** 2026-03-10  
**Приоритет:** P1 (критично для UX)  
**Статус:** ✅ ПРОБЛЕМА НАЙДЕНА

---

## 📊 СИМПТОМЫ ПРОБЛЕМЫ

**Пользователь сообщает:**
> В категории показывается, что есть каналы, а в подкатегориях эти же каналы отсутствуют.

**Наблюдаемое поведение:**
1. Пользователь заходит в категорию "IT" → видит 11 каналов ✅
2. Пользователь заходит в "Подкатегории" → видит 0 каналов ❌

---

## 🔬 АНАЛИЗ ДАННЫХ В БД

### 1. Распределение по категориям

```sql
SELECT topic, COUNT(*) as total, COUNT(subcategory) as with_subcat 
FROM telegram_chats 
WHERE is_active = true 
GROUP BY topic 
ORDER BY topic;
```

**Результат:**

| topic | total | with_subcat | % заполненных |
|-------|-------|-------------|---------------|
| business | 3 | 0 | 0% |
| education | 1 | 0 | 0% |
| health | 1 | 0 | 0% |
| **it** | **11** | **1** | **9%** |
| marketing | 1 | 0 | 0% |
| news | 4 | 0 | 0% |
| other | 10 | 0 | 0% |
| Другое | 1 | 1 | 100% |
| новости | 1 | 0 | 0% |
| финансы | 1 | 0 | 0% |

**Вывод:** Только 2 из 34 каналов (6%) имеют заполненный subcategory!

---

### 2. Детальный анализ IT категории

```sql
SELECT id, username, topic, subcategory 
FROM telegram_chats 
WHERE is_active = true AND topic = 'it';
```

**Результат:**

| id | username | topic | subcategory |
|----|----------|-------|-------------|
| 497 | python | it | **programming** ✅ |
| 496 | entertainment | it | NULL ❌ |
| 498 | golang | it | NULL ❌ |
| 502 | dailydvizh | it | NULL ❌ |
| 516 | golang_ru | it | NULL ❌ |
| 517 | javascript_ru | it | NULL ❌ |
| 518 | frontend_ru | it | NULL ❌ |
| 519 | devops_ru | it | NULL ❌ |
| 520 | docker_ru | it | NULL ❌ |
| 521 | kubernetes_ru | it | NULL ❌ |

**Вывод:** Только 1 канал из 11 имеет subcategory="programming". Остальные 10 — NULL.

---

## 🐛 КОРЕННАЯ ПРИЧИНА

### Проблема 1: Несогласованность ключей SUBCATEGORIES

**Файл:** `src/utils/categories.py`

```python
SUBCATEGORIES: dict[str, dict[str, str]] = {
    "бизнес": {  # ← Русский ключ
        "startup": "Стартапы и инновации",
        ...
    },
    "it": {  # ← Английский ключ
        "programming": "Программирование",
        ...
    },
    "финансы": {  # ← Русский ключ
        ...
    },
}
```

**Проблема:** Ключи смешаны — некоторые на русском, некоторые на английском!

---

### Проблема 2: Данные в БД на английском

```sql
SELECT DISTINCT topic FROM telegram_chats WHERE is_active = true;
```

**Результат:**
- `business` (англ)
- `education` (англ)
- `it` (англ)
- `финансы` (рус)
- `Другое` (рус)

**Проблема:** В БД topic хранится **на английском**, но SUBCATEGORIES использует **русские ключи**!

---

### Проблема 3: Логика handle_subcategories()

**Файл:** `src/bot/handlers/channels_db.py:323-365`

```python
@router.callback_query(ChannelsCB.filter(F.action == "subcategories"))
async def handle_subcategories(callback: CallbackQuery, callback_data: ChannelsCB) -> None:
    topic = callback_data.value  # ← "it" (английский)
    
    subcats = SUBCATEGORIES.get(topic, {})  # ← Ищет "it" в SUBCATEGORIES
    
    # ...
    
    result = await session.execute(
        select(
            TelegramChat.subcategory.label("subcat"),
            func.count(TelegramChat.id).label("total"),
        )
        .where(
            TelegramChat.is_active == true(),
            func.lower(TelegramChat.topic) == topic.lower(),  # ← topic = "it"
            TelegramChat.subcategory.in_(list(subcats.keys())),  # ← ["programming", "web_dev", ...]
        )
        .group_by(TelegramChat.subcategory)
    )
```

**Проблемы:**

1. **SUBCATEGORIES.get("it")** → работает (ключ "it" есть)
2. **Но для "business"** → `SUBCATEGORIES.get("business")` → `None` ❌ (ключ "бизнес" на русском!)
3. **Каналы без subcategory** → `subcategory.in_(...)` → не попадают в выборку ❌

---

### Проблема 4: Отсутствие автоклассификации

**Файл:** `src/utils/categories.py:68-103`

```python
def classify_subcategory(
    title: str,
    description: str,
    topic: str,
) -> str | None:
    """Определить подкатегорию канала по ключевым словам."""
    # ... логика классификации ...
```

**Проблема:** Функция существует, но **НЕ ВЫЗЫВАЕТСЯ** при парсинге каналов!

---

## 📈 ПОЛНАЯ КАРТИНА ПРОБЛЕМЫ

```
┌─────────────────────────────────────────────────────────────┐
│                    КАНАЛЫ В БД (34 шт)                       │
├─────────────────────────────────────────────────────────────┤
│ topic="it" (11 каналов)                                     │
│   ├─ subcategory="programming" (1 канал) ✅                 │
│   └─ subcategory=NULL (10 каналов) ❌                       │
│                                                              │
│ topic="business" (3 канала)                                 │
│   └─ subcategory=NULL (3 канала) ❌                         │
│                                                              │
│ topic="other" (10 каналов)                                  │
│   └─ subcategory=NULL (10 каналов) ❌                       │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    SUBCATEGORIES (fallback)                  │
├─────────────────────────────────────────────────────────────┤
│ "бизнес" → ["startup", "small_business", ...] ✅            │
│ "it" → ["programming", "web_dev", ...] ✅                   │
│ "финансы" → ["investments", "stock_market", ...] ✅         │
│                                                              │
│ "business" → НЕ СУЩЕСТВУЕТ ❌                               │
│ "marketing" → НЕ СУЩЕСТВУЕТ ❌                              │
│ "news" → НЕ СУЩЕСТВУЕТ ❌                                   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    ЛОГИКА handle_subcategories()             │
├─────────────────────────────────────────────────────────────┤
│ 1. topic = "it" (из callback_data)                          │
│ 2. subcats = SUBCATEGORIES.get("it") → {"programming": ...} │
│ 3. SQL: WHERE topic = "it" AND subcategory IN ("programming", ...) │
│ 4. Результат: 1 канал (где subcategory="programming")       │
│                                                              │
│ 1. topic = "business" (из callback_data)                    │
│ 2. subcats = SUBCATEGORIES.get("business") → None ❌        │
│ 3. Возврат: "Для категории business нет подкатегорий" ❌    │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔧 РЕШЕНИЯ

### Решение 1: Исправить ключи SUBCATEGORIES (срочно)

**Файл:** `src/utils/categories.py`

```python
SUBCATEGORIES: dict[str, dict[str, str]] = {
    # Было (русские ключи):
    # "бизнес": {...}
    # "финансы": {...}
    
    # Стало (английские ключи как в БД):
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
    "finance": {  # ← Вместо "финансы"
        "investments": "Инвестиции и трейдинг",
        "stock_market": "Фондовый рынок",
        "banking": "Банки и вклады",
        "insurance": "Страхование",
    },
    "crypto": {  # ← Вместо "крипто"
        "defi": "DeFi и протоколы",
        "nft": "NFT",
        "trading": "Крипто-трейдинг",
        "bitcoin": "Bitcoin и Ethereum",
    },
    "education": {  # ← Вместо "образование"
        "online_courses": "Онлайн-курсы",
        "languages": "Изучение языков",
        "professional": "Профессии и переквалификация",
        "kids": "Детское образование",
        "university": "Высшее образование",
    },
    "news": {  # ← НОВОЕ
        "politics": "Политика",
        "world": "Мировые новости",
        "tech_news": "Технологические новости",
        "economy": "Экономика",
    },
    "other": {  # ← НОВОЕ
        "humor": "Юмор",
        "lifestyle": "Образ жизни",
        "hobbies": "Хобби",
    },
}
```

---

### Решение 2: Автоклассификация существующих каналов (миграция)

**Файл:** `src/db/migrations/versions/20260310_000000_backfill_subcategories.py`

```python
"""Backfill subcategories for existing channels

Revision ID: 0014
Revises: 0013
Create Date: 2026-03-10 00:00:00.000000

"""
from alembic import op
from sqlalchemy import select, update

from src.db.models.analytics import TelegramChat
from src.utils.categories import classify_subcategory


def upgrade() -> None:
    # Используем SQL для обновления
    connection = op.get_bind()
    
    # Получаем все каналы без subcategory
    result = connection.execute(
        select(
            TelegramChat.id,
            TelegramChat.title,
            TelegramChat.description,
            TelegramChat.topic,
        ).where(
            TelegramChat.is_active == True,
            TelegramChat.subcategory == None,
        )
    )
    
    for row in result:
        subcategory = classify_subcategory(
            title=row.title or "",
            description=row.description or "",
            topic=row.topic or "",
        )
        
        if subcategory:
            connection.execute(
                update(TelegramChat)
                .where(TelegramChat.id == row.id)
                .values(subcategory=subcategory)
            )


def downgrade() -> None:
    # Не делаем downgrade — классификация полезна
    pass
```

---

### Решение 3: Интеграция classify_subcategory() в парсер

**Файл:** `src/tasks/parser_tasks.py`

```python
# В функции parse_single_chat() или refresh_chat_database()

# После определения topic:
from src.utils.categories import classify_subcategory

subcategory = classify_subcategory(
    title=chat.title,
    description=chat.description,
    topic=topic,
)

# Сохраняем в БД
chat.topic = topic
chat.subcategory = subcategory  # ← Добавлено!
```

---

### Решение 4: Улучшенная логика handle_subcategories()

**Файл:** `src/bot/handlers/channels_db.py`

```python
@router.callback_query(ChannelsCB.filter(F.action == "subcategories"))
async def handle_subcategories(callback: CallbackQuery, callback_data: ChannelsCB) -> None:
    topic = callback_data.value
    
    # Получаем подкатегории из БД (с fallback)
    from src.utils.categories import get_subcategories_from_db
    subcats = await get_subcategories_from_db(topic)
    
    if not subcats:
        text = f"❌ Для категории <b>{topic}</b> нет подкатегорий"
        # ...
        return
    
    text = f"📊 <b>Подкатегории: {topic}</b>\n\n"
    
    async with async_session_factory() as session:
        from sqlalchemy import func, select, true
        from src.db.models.analytics import TelegramChat
        
        # Получаем каналы С subcategory
        result_with_subcat = await session.execute(
            select(
                TelegramChat.subcategory.label("subcat"),
                func.count(TelegramChat.id).label("total"),
            )
            .where(
                TelegramChat.is_active == true(),
                func.lower(TelegramChat.topic) == topic.lower(),
                TelegramChat.subcategory.in_(list(subcats.keys())),
            )
            .group_by(TelegramChat.subcategory)
            .order_by(func.count(TelegramChat.id).desc())
        )
        rows_with_subcat = result_with_subcat.tuples().all()
        
        # Получаем каналы БЕЗ subcategory
        result_without_subcat = await session.execute(
            select(func.count(TelegramChat.id).label("total"))
            .where(
                TelegramChat.is_active == true(),
                func.lower(TelegramChat.topic) == topic.lower(),
                TelegramChat.subcategory == None,
            )
        )
        total_without_subcat = result_without_subcat.scalar() or 0
    
    # Формируем список
    for row in rows_with_subcat:
        subcat = row[0]
        total = row[1]
        if subcat:
            name = subcats.get(subcat, subcat)
            text += f"• {name}: <b>{total:,}</b>\n"
    
    # Добавляем информацию о каналах без subcategory
    if total_without_subcat > 0:
        text += f"\n⚠️ <b>{total_without_subcat:,} каналов</b> без подкатегории\n"
        text += "Классификация будет добавлена в ближайшее время."
    
    if not rows_with_subcat and total_without_subcat == 0:
        text += "Пока нет данных по подкатегориям.\n"
    
    # ...
```

---

## 📋 ПЛАН ИСПРАВЛЕНИЯ

### Этап 1: Исправить ключи SUBCATEGORIES (30 мин)
- [ ] Обновить `src/utils/categories.py`
- [ ] Заменить русские ключи на английские
- [ ] Добавить missing категории (news, other)

### Этап 2: Создать миграцию backfill (1 час)
- [ ] Создать `20260310_000000_backfill_subcategories.py`
- [ ] Протестировать на staging
- [ ] Применить миграцию

### Этап 3: Интегрировать в парсер (1 час)
- [ ] Обновить `src/tasks/parser_tasks.py`
- [ ] Добавить вызов `classify_subcategory()`
- [ ] Протестировать на новых каналах

### Этап 4: Улучшить handle_subcategories() (1 час)
- [ ] Обновить `src/bot/handlers/channels_db.py`
- [ ] Добавить отображение каналов без subcategory
- [ ] Добавить informative message

---

## 🎯 ОЖИДАЕМЫЙ РЕЗУЛЬТАТ

**После исправления:**

| topic | total | with_subcat | % заполненных |
|-------|-------|-------------|---------------|
| business | 3 | 3 | 100% ✅ |
| it | 11 | 11 | 100% ✅ |
| marketing | 1 | 1 | 100% ✅ |
| news | 4 | 4 | 100% ✅ |

**Пользовательский опыт:**
1. Заходит в категорию "IT" → видит 11 каналов ✅
2. Заходит в "Подкатегории" → видит:
   - Programming: 5 каналов
   - Web Dev: 3 канала
   - DevOps: 2 канала
   - AI/ML: 1 канал
3. Все каналы распределены по подкатегориям ✅

---

## 📊 ТЕКУЩАЯ СТАТИСТИКА

- **Всего каналов:** 34
- **С подкатегорией:** 2 (6%)
- **Без подкатегории:** 32 (94%)
- **Категории с русскими ключами:** 3 ("бизнес", "финансы", "крипто", "образование")
- **Категории с английскими ключами:** 6 ("it", "business", "marketing", "news", "other", "education")

---

**РЕКОМЕНДАЦИЯ:** Начать с Этапа 1 (исправление ключей) — это займёт 30 минут и сразу улучшит ситуацию.
