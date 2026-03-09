# 📋 ПЛАН ИСПРАВЛЕНИЙ — КАТЕГОРИИ И ПОДКАТЕГОРИИ КАНАЛОВ

**Проект:** Market Telegram Bot  
**Дата:** 2026-03-10  
**На основе аудита:** `docs/audit/CATEGORY_STATS_AUDIT.md`  
**Всего задач:** 8 (3 P0 + 3 P1 + 2 P2)  
**Оценка времени:** ~16 часов

---

## 🔴 ПРИОРИТЕТ P0 — КРИТИЧЕСКИЕ (НЕДЕЛЯ 1)

### P0.1 — Унифицировать названия тем (RU язык)

**Проблема:** Смешение русских и английских названий тем.

**Файлы для изменения:**
1. `src/db/models/telegram_chat.py` — модель канала
2. `src/utils/telegram/parser.py` — парсер (если есть классификация)
3. `src/api/constants/parser.py` — поисковые запросы
4. Миграция Alembic

**Шаги:**

#### Шаг 1: Создать маппинг тем

```python
# src/db/models/telegram_chat.py (добавить константу)

TOPIC_MAPPING: dict[str, str] = {
    "business": "бизнес",
    "education": "образование",
    "marketing": "маркетинг",
    "news": "новости",
    "health": "здоровье",
    "finance": "финансы",
    "crypto": "крипто",
    "it": "it",  # остаётся как есть
    "other": "другое",  # будет заменено на конкретные категории
}
```

#### Шаг 2: Создать миграцию Alembic

```bash
cd /opt/market-telegram-bot
alembic revision -m "normalize_channel_topics_to_russian"
```

**Содержимое миграции:**
```python
"""normalize_channel_topics_to_russian

Revision ID: abc123def456
Revises: 8885dc6d508e
Create Date: 2026-03-10

"""

from alembic import op
import sqlalchemy as sa

revision: str = "abc123def456"
down_revision: str | None = "8885dc6d508e"
branch_labels: str | list[str] | None = None
depends_on: str | list[str] | None = None


def upgrade() -> None:
    # Обновляем topic на русский язык
    op.execute("""
        UPDATE telegram_chats 
        SET topic = 'бизнес' 
        WHERE topic = 'business'
    """)
    
    op.execute("""
        UPDATE telegram_chats 
        SET topic = 'образование' 
        WHERE topic = 'education'
    """)
    
    op.execute("""
        UPDATE telegram_chats 
        SET topic = 'маркетинг' 
        WHERE topic = 'marketing'
    """)
    
    op.execute("""
        UPDATE telegram_chats 
        SET topic = 'новости' 
        WHERE topic = 'news'
    """)
    
    op.execute("""
        UPDATE telegram_chats 
        SET topic = 'здоровье' 
        WHERE topic = 'health'
    """)
    
    op.execute("""
        UPDATE telegram_chats 
        SET topic = 'финансы' 
        WHERE topic = 'finance'
    """)
    
    op.execute("""
        UPDATE telegram_chats 
        SET topic = 'крипто' 
        WHERE topic = 'crypto'
    """)
    
    op.execute("""
        UPDATE telegram_chats 
        SET topic = 'другое' 
        WHERE topic = 'other'
    """)


def downgrade() -> None:
    # Возвращаем английские названия
    op.execute("""
        UPDATE telegram_chats 
        SET topic = 'business' 
        WHERE topic = 'бизнес'
    """)
    
    op.execute("""
        UPDATE telegram_chats 
        SET topic = 'education' 
        WHERE topic = 'образование'
    """)
    
    op.execute("""
        UPDATE telegram_chats 
        SET topic = 'marketing' 
        WHERE topic = 'маркетинг'
    """)
    
    op.execute("""
        UPDATE telegram_chats 
        SET topic = 'news' 
        WHERE topic = 'новости'
    """)
    
    op.execute("""
        UPDATE telegram_chats 
        SET topic = 'health' 
        WHERE topic = 'здоровье'
    """)
    
    op.execute("""
        UPDATE telegram_chats 
        SET topic = 'finance' 
        WHERE topic = 'финансы'
    """)
    
    op.execute("""
        UPDATE telegram_chats 
        SET topic = 'crypto' 
        WHERE topic = 'крипто'
    """)
    
    op.execute("""
        UPDATE telegram_chats 
        SET topic = 'other' 
        WHERE topic = 'другое'
    """)
```

#### Шаг 3: Применить миграцию

```bash
cd /opt/market-telegram-bot
docker compose exec bot poetry run alembic upgrade head
```

#### Шаг 4: Проверить результат

```sql
SELECT topic, COUNT(*) FROM telegram_chats GROUP BY topic ORDER BY topic;
```

**Время:** 2 часа  
**Исполнитель:** belin

---

### P0.2 — Добавить тему "новости" в справочник

**Проблема:** В `topic_categories` отсутствует тема "новости".

**Файлы для изменения:**
1. `src/db/models/category.py` — модель (не требует изменений)
2. Миграция Alembic для добавления записей

**Шаги:**

#### Шаг 1: Создать миграцию

```bash
alembic revision -m "add_news_topic_categories"
```

**Содержимое миграции:**
```python
"""add_news_topic_categories

Revision ID: def789ghi012
Revises: abc123def456
Create Date: 2026-03-10

"""

from alembic import op
import sqlalchemy as sa
from datetime import datetime

revision: str = "def789ghi012"
down_revision: str | None = "abc123def456"
branch_labels: str | list[str] | None = None
depends_on: str | list[str] | None = None


def upgrade() -> None:
    # Добавляем подкатегории для темы "новости"
    op.bulk_insert(
        sa.table(
            "topic_categories",
            sa.column("id", sa.Integer),
            sa.column("topic", sa.String),
            sa.column("subcategory", sa.String),
            sa.column("display_name_ru", sa.String),
            sa.column("is_active", sa.Boolean),
            sa.column("sort_order", sa.Integer),
            sa.column("created_at", sa.DateTime),
            sa.column("updated_at", sa.DateTime),
        ),
        [
            {
                "topic": "новости",
                "subcategory": "media",
                "display_name_ru": "СМИ и журналистика",
                "is_active": True,
                "sort_order": 1,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            },
            {
                "topic": "новости",
                "subcategory": "politics",
                "display_name_ru": "Политика",
                "is_active": True,
                "sort_order": 2,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            },
            {
                "topic": "новости",
                "subcategory": "economy",
                "display_name_ru": "Экономика",
                "is_active": True,
                "sort_order": 3,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            },
            {
                "topic": "новости",
                "subcategory": "society",
                "display_name_ru": "Общество",
                "is_active": True,
                "sort_order": 4,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            },
            {
                "topic": "новости",
                "subcategory": "world",
                "display_name_ru": "Мировые новости",
                "is_active": True,
                "sort_order": 5,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            },
        ],
    )


def downgrade() -> None:
    op.execute("""
        DELETE FROM topic_categories 
        WHERE topic = 'новости'
    """)
```

#### Шаг 2: Применить миграцию

```bash
alembic upgrade head
```

#### Шаг 3: Проверить

```sql
SELECT topic, subcategory, display_name_ru 
FROM topic_categories 
WHERE topic = 'новости' 
ORDER BY sort_order;
```

**Время:** 1 час  
**Исполнитель:** belin

---

### P0.3 — Заполнить подкатегории для каналов (авто-классификация)

**Проблема:** 25 каналов (74%) без подкатегории.

**Файлы для изменения:**
1. `src/tasks/parser_tasks.py` — задача классификации
2. `src/core/services/ai_service.py` — AI сервис для классификации
3. Миграция данных (SQL script)

**Шаги:**

#### Шаг 1: Создать AI сервис для классификации

```python
# src/core/services/category_classifier.py (новый файл)

"""
Сервис для автоматической классификации каналов по категориям.
Использует LLM для анализа описания канала.
"""

import logging
from typing import TypedDict

from src.core.services.ai_service import ai_service

logger = logging.getLogger(__name__)


class CategoryResult(TypedDict):
    topic: str
    subcategory: str
    confidence: float


CATEGORY_PROMPT = """
Проанализируй описание Telegram канала и определи категорию и подкатегорию.

Доступные категории и подкатегории:
- бизнес: startup, small_business, personal_finance, real_estate, franchise
- ит: programming, web_dev, mobile_dev, gamedev, devops, ai_ml, data, security
- маркетинг: smm, digital, seo, content, target_ads, sales
- новости: media, politics, economy, society, world
- образование: university, online_courses, languages, professional, kids
- финансы: investments, stock_market, banking, insurance
- крипто: trading, defi, nft, bitcoin
- здоровье: medicine, fitness, nutrition, psychology
- другое: entertainment, hobbies, lifestyle

Описание канала: {description}

Название канала: {title}

Верни ответ в формате JSON:
{{
    "topic": "категория",
    "subcategory": "подкатегория",
    "confidence": 0.95
}}
"""


async def classify_channel(title: str, description: str) -> CategoryResult:
    """
    Классифицировать канал по названию и описанию.
    
    Args:
        title: Название канала.
        description: Описание канала.
    
    Returns:
        Результат классификации.
    """
    prompt = CATEGORY_PROMPT.format(title=title, description=description)
    
    response = await ai_service.generate(
        prompt=prompt,
        model="qwen/qwen-turbo",  # Дешёвая модель для классификации
        temperature=0.1,  # Минимальная случайность
        max_tokens=200,
    )
    
    # Парсим JSON ответ
    import json
    try:
        result = json.loads(response)
        return CategoryResult(
            topic=result.get("topic", "другое"),
            subcategory=result.get("subcategory", ""),
            confidence=float(result.get("confidence", 0.5)),
        )
    except (json.JSONDecodeError, KeyError):
        logger.warning(f"Failed to parse classification response: {response}")
        return CategoryResult(topic="другое", subcategory="", confidence=0.0)
```

#### Шаг 2: Создать Celery задачу

```python
# src/tasks/parser_tasks.py (добавить задачу)

@celery_app.task(name="parser:autoclassify_channels", queue="parser")
def autoclassify_channels(limit: int = 50) -> dict:
    """
    Автоматически классифицировать каналы без подкатегории.
    
    Args:
        limit: Максимальное количество каналов для обработки.
    
    Returns:
        Статистика классификации.
    """
    import asyncio
    
    async def _classify_async() -> dict:
        from sqlalchemy import select
        
        from src.db.models.telegram_chat import TelegramChat
        from src.db.session import async_session_factory
        from src.core.services.category_classifier import classify_channel
        
        stats = {"classified": 0, "errors": 0, "low_confidence": 0}
        
        async with async_session_factory() as session:
            # Выбираем каналы без подкатегории
            query = (
                select(TelegramChat)
                .where(
                    TelegramChat.is_active == True,
                    TelegramChat.subcategory.is_(None),
                )
                .limit(limit)
            )
            result = await session.execute(query)
            channels = result.scalars().all()
            
            for channel in channels:
                try:
                    result = await classify_channel(
                        title=channel.title or "",
                        description=channel.description or "",
                    )
                    
                    if result["confidence"] >= 0.7:
                        channel.topic = result["topic"]
                        channel.subcategory = result["subcategory"]
                        stats["classified"] += 1
                    else:
                        stats["low_confidence"] += 1
                    
                except Exception as e:
                    logger.error(f"Error classifying channel {channel.id}: {e}")
                    stats["errors"] += 1
            
            await session.commit()
        
        return stats
    
    # Запускаем в event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_classify_async())
    finally:
        loop.close()
```

#### Шаг 3: Запустить классификацию

```bash
# Вручную через Flower или CLI
docker compose exec worker_critical poetry run celery -A src.tasks.celery_app call parser:autoclassify_channels --kwargs='{"limit": 50}'
```

#### Шаг 4: Проверить результат

```sql
SELECT topic, subcategory, COUNT(*) 
FROM telegram_chats 
WHERE is_active = true 
GROUP BY topic, subcategory 
ORDER BY topic, subcategory;
```

**Время:** 4 часа  
**Исполнитель:** belin

---

## 🟠 ПРИОРИТЕТ P1 — ВАЖНЫЕ (НЕДЕЛЯ 2)

### P1.1 — Исправить invalid subcategory

**Проблема:** 2 канала с подкатегориями которых нет в справочнике.

**Каналы:**
- `Smm room` — marketing + digital (нет в справочнике)
- `Моя Поликлиника` — health + medicine (нет в справочнике)

**Шаги:**

#### Шаг 1: Добавить missing подкатегории в справочник

```python
# alembic revision -m "add_missing_subcategories"

def upgrade() -> None:
    op.bulk_insert(
        sa.table(
            "topic_categories",
            sa.column("id", sa.Integer),
            sa.column("topic", sa.String),
            sa.column("subcategory", sa.String),
            sa.column("display_name_ru", sa.String),
            sa.column("is_active", sa.Boolean),
            sa.column("sort_order", sa.Integer),
            sa.column("created_at", sa.DateTime),
            sa.column("updated_at", sa.DateTime),
        ),
        [
            {
                "topic": "маркетинг",
                "subcategory": "digital",
                "display_name_ru": "Digital-маркетинг",
                "is_active": True,
                "sort_order": 6,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            },
            {
                "topic": "здоровье",
                "subcategory": "medicine",
                "display_name_ru": "Медицина и здоровье",
                "is_active": True,
                "sort_order": 6,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            },
        ],
    )
```

#### Шаг 2: Обновить каналы с правильным topic

```sql
UPDATE telegram_chats 
SET topic = 'маркетинг' 
WHERE username = 'smm_ru';

UPDATE telegram_chats 
SET topic = 'здоровье' 
WHERE username = 'zdorovie_ru';
```

**Время:** 1 час  
**Исполнитель:** belin

---

### P1.2 — Разобрать категорию "другое"

**Проблема:** 10 каналов в категории "другое" без конкретной тематики.

**Каналы:**
- Movies
- Popcorn Today 🍿
- Blum: All Crypto
- rndm.club
- WOOFS ДВИЖ Party+After
- Марат Хуснуллин
- Айбелив Айкенфлаев
- Free Crypto
- Blum Memepad
- Gazgolder club

**Шаги:**

#### Шаг 1: Запустить AI классификацию для "другое"

```bash
# Используем задачу из P0.3
docker compose exec worker_critical poetry run celery -A src.tasks.celery_app call parser:autoclassify_channels --kwargs='{"limit": 10}'
```

#### Шаг 2: Ручная проверка (админ-панель)

Создать SQL script для ручной проверки:

```sql
-- Показать каналы для ручной классификации
SELECT id, title, username, topic, subcategory, member_count
FROM telegram_chats
WHERE topic = 'другое'
ORDER BY member_count DESC;
```

#### Шаг 3: Обновить категории

```sql
-- Пример (после ручной проверки)
UPDATE telegram_chats 
SET topic = 'крипто', subcategory = 'trading'
WHERE username IN ('blumcrypto', 'freecryptosfaucets', 'blumcrypto_memepad');

UPDATE telegram_chats 
SET topic = 'развлечения', subcategory = 'movies'
WHERE username IN ('movies', 'popcorn_today');

UPDATE telegram_chats 
SET topic = 'политика', subcategory = 'government'
WHERE username = 'mkhusnullin';
```

**Время:** 3 часа  
**Исполнитель:** belin + tsaguria (ручная проверка)

---

### P1.3 — Добавить валидацию при создании/обновлении канала

**Проблема:** Нет проверки existence topic+subcategory в справочнике.

**Файлы для изменения:**
1. `src/db/models/telegram_chat.py` — добавить constraint
2. `src/db/repositories/chat_repo.py` — валидация в repository
3. `src/utils/telegram/parser.py` — валидация при парсинге

**Шаги:**

#### Шаг 1: Добавить ForeignKey constraint

```python
# alembic revision -m "add_category_foreign_key"

def upgrade() -> None:
    # Добавляем FK на topic_categories
    op.create_foreign_key(
        "fk_telegram_chats_topic_category",
        "telegram_chats",
        "topic_categories",
        ["topic", "subcategory"],
        ["topic", "subcategory"],
    )
```

**Примечание:** Требуется изменить модель чтобы использовать composite FK.

#### Шаг 2: Добавить валидацию в repository

```python
# src/db/repositories/chat_repo.py

async def upsert_batch(
    self,
    channels: list[TelegramChatData],
) -> int:
    """
    Обновить или создать каналы.
    
    Args:
        channels: Список каналов для обновления.
    
    Returns:
        Количество обновлённых каналов.
    """
    from sqlalchemy import select
    
    from src.db.models.category import TopicCategory
    
    updated = 0
    
    for channel_data in channels:
        # ✅ ВАЛИДАЦИЯ: Проверка существования категории
        if channel_data.topic:
            category_exists = await self.session.execute(
                select(TopicCategory).where(
                    TopicCategory.topic == channel_data.topic,
                    TopicCategory.subcategory == (channel_data.subcategory or ""),
                    TopicCategory.is_active == True,
                )
            )
            
            if not category_exists.scalar_one_or_none():
                logger.warning(
                    f"Category not found: {channel_data.topic}/{channel_data.subcategory}, "
                    f"using 'другое/'"
                )
                channel_data.topic = "другое"
                channel_data.subcategory = ""
        
        # ... остальная логика upsert
    
    return updated
```

**Время:** 3 часа  
**Исполнитель:** belin

---

## 🟡 ПРИОРИТЕТ P2 — СРЕДНИЕ (НЕДЕЛЯ 3)

### P2.1 — Создать админ-интерфейс для классификации

**Проблема:** Нет удобного интерфейса для ручной классификации.

**Файлы для создания:**
1. `src/bot/handlers/admin_categories.py` — новые handlers
2. `src/bot/keyboards/admin_categories.py` — клавиатуры

**Шаги:**

#### Шаг 1: Создать keyboard для выбора категории

```python
# src/bot/keyboards/admin_categories.py

from aiogram.types import InlineKeyboardBuilder
from src.db.models.category import TopicCategory


def get_category_selection_kb(categories: list[TopicCategory]) -> InlineKeyboardMarkup:
    """Клавиатура для выбора категории."""
    builder = InlineKeyboardBuilder()
    
    for category in categories:
        builder.button(
            text=f"{category.display_name_ru}",
            callback_data=f"admin_cat_select:{category.topic}:{category.subcategory}",
        )
    
    builder.adjust(2)  # 2 кнопки в ряд
    return builder.as_markup()
```

#### Шаг 2: Создать handler для админа

```python
# src/bot/handlers/admin_categories.py

@router.callback_query(AdminCB.filter(F.action == "classify_channel"))
async def classify_channel_handler(
    callback: CallbackQuery,
    callback_data: AdminCB,
) -> None:
    """Админ-панель для классификации канала."""
    channel_id = int(callback_data.value)
    
    # Показать канал и кнопки выбора категории
    text = f"Классификация канала #{channel_id}\n\nВыберите категорию:"
    keyboard = get_category_selection_kb(await get_all_categories())
    
    await callback.message.edit_text(text, reply_markup=keyboard)
```

**Время:** 2 часа  
**Исполнитель:** tsaguria

---

### P2.2 — Добавить мониторинг категорий

**Проблема:** Нет отслеживания каналов без категории.

**Файлы для изменения:**
1. `src/api/routers/analytics.py` — добавить endpoint
2. `mini_app/src/pages/Analytics.tsx` — добавить график

**Шаги:**

#### Шаг 1: Добавить endpoint

```python
# src/api/routers/analytics.py

@router.get("/analytics/categories")
async def get_category_stats(
    current_user: User = Depends(get_current_user),
) -> CategoryStatsResponse:
    """
    Получить статистику по категориям каналов.
    """
    async with async_session_factory() as session:
        chat_repo = ChatRepository(session)
        
        # Получить распределение по категориям
        stats = await chat_repo.get_category_distribution()
        
        # Найти каналы без категории
        unclassified = await chat_repo.get_unclassified_channels()
        
        return CategoryStatsResponse(
            total=stats["total"],
            by_category=stats["by_category"],
            unclassified_count=len(unclassified),
            unclassified_channels=unclassified[:10],  # Первые 10
        )
```

#### Шаг 2: Добавить график в Mini App

```tsx
// mini_app/src/pages/Analytics.tsx

import { PieChart, Pie, Cell } from 'recharts';

function CategoryDistribution({ stats }) {
  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8'];
  
  return (
    <div className="card">
      <h3>Распределение по категориям</h3>
      <PieChart width={400} height={400}>
        <Pie
          data={stats.by_category}
          cx={200}
          cy={200}
          outerRadius={150}
          fill="#8884d8"
          dataKey="count"
          label={({topic, percent}) => `${topic} ${(percent * 100).toFixed(0)}%`}
        >
          {stats.by_category.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
          ))}
        </Pie>
      </PieChart>
      
      {stats.unclassified_count > 0 && (
        <div className="alert warning">
          ⚠️ {stats.unclassified_count} каналов без категории
        </div>
      )}
    </div>
  );
}
```

**Время:** 2 часа  
**Исполнитель:** tsaguria

---

## 📊 ГРАФИК ВЫПОЛНЕНИЯ

| Неделя | Задачи | Исполнитель | Часы |
|--------|--------|-------------|------|
| **Неделя 1 (P0)** | P0.1, P0.2, P0.3 | belin | 7 |
| **Неделя 2 (P1)** | P1.1, P1.2, P1.3 | belin | 7 |
| **Неделя 3 (P2)** | P2.1, P2.2 | tsaguria | 4 |
| **ИТОГО** | **8 задач** | | **18 часов** |

---

## ✅ КРИТЕРИИ ПРИЁМКИ

### Для каждой задачи:

1. **Код изменён** согласно спецификации
2. **Миграция создана** и протестирована
3. **Миграция применена** к production БД
4. **Ruff + MyPy** проверки проходят
5. **Git commit** с описанием
6. **PR создан** и approved

### Финальная проверка:

```bash
# Проверить распределение по категориям
docker compose exec postgres psql -U market_bot -d market_bot_db -c "
    SELECT topic, subcategory, COUNT(*) 
    FROM telegram_chats 
    WHERE is_active = true 
    GROUP BY topic, subcategory 
    ORDER BY topic, subcategory;
"

# Проверить каналы без категории
docker compose exec postgres psql -U market_bot -d market_bot_db -c "
    SELECT COUNT(*) as unclassified 
    FROM telegram_chats 
    WHERE is_active = true 
    AND (subcategory IS NULL OR subcategory = '');
"

# Проверить справочник
docker compose exec postgres psql -U market_bot -d market_bot_db -c "
    SELECT topic, COUNT(*) as subcategories 
    FROM topic_categories 
    WHERE is_active = true 
    GROUP BY topic 
    ORDER BY topic;
"

# Запустить тесты
make test

# Проверить линтеры
make lint
```

---

## 📋 ЧЕКЛИСТ ЗАДАЧ

- [ ] **P0.1** Унифицировать названия тем (RU язык)
- [ ] **P0.1** Создать миграцию Alembic
- [ ] **P0.1** Применить миграцию
- [ ] **P0.2** Добавить тему "новости" в справочник
- [ ] **P0.2** Создать 5 подкатегорий для новостей
- [ ] **P0.3** Создать AI сервис классификации
- [ ] **P0.3** Создать Celery задачу autoclassify_channels
- [ ] **P0.3** Запустить классификацию для 25 каналов
- [ ] **P1.1** Добавить missing подкатегории (digital, medicine)
- [ ] **P1.1** Обновить каналы с правильным topic
- [ ] **P1.2** Запустить AI классификацию для "другое"
- [ ] **P1.2** Ручная проверка 10 каналов
- [ ] **P1.3** Добавить FK constraint на topic_categories
- [ ] **P1.3** Добавить валидацию в chat_repo.upsert_batch()
- [ ] **P2.1** Создать admin-интерфейс для классификации
- [ ] **P2.2** Добавить endpoint /analytics/categories
- [ ] **P2.2** Добавить график в Mini App
- [ ] **Все** Применить все миграции
- [ ] **Все** Запустить тесты
- [ ] **Все** Запустить линтеры

---

## 📈 ОЖИДАЕМЫЙ РЕЗУЛЬТАТ

### До исправлений:
```
Всего каналов: 34
С подкатегорией: 9 (26%)
Без подкатегории: 25 (74%) ⚠️
Проблемные темы: 8 (business, education, marketing, etc.)
```

### После исправлений:
```
Всего каналов: 34
С подкатегорией: 32 (94%) ✅
Без подкатегории: 2 (6%) ✅
Все темы на русском языке ✅
Все подкатегории валидны ✅
```

---

**ПЛАН УТВЕРЖДЁН:** 2026-03-10  
**СЛЕДУЮЩИЙ АУДИТ:** После выполнения всех исправлений

---

**ИСПОЛНИТЕЛЬ:** Qwen Code  
**ФАЙЛ ПЛАНА:** `docs/audit/FIX_PLAN_CATEGORIES.md`
