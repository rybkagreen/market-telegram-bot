# QWEN CODE — СПРИНТ 3: СРЕДНИЙ ПРИОРИТЕТ (P2)

## ⚠️ ПРАВИЛА ВЫПОЛНЕНИЯ — ЧИТАЙ ПЕРЕД СТАРТОМ

1. **Спринты 1 и 2 должны быть завершены** перед началом
2. **Задачи 1–3 независимы** — можно выполнять параллельно
3. **Задача 4 (N+1)** — только после прочтения EXPLAIN ANALYZE запросов, не оптимизировать вслепую
4. **Задача 5 (JSON-документация)** — только документация, никакого изменения схемы БД
5. **Создавай миграцию** для любого изменения схемы БД — не трогать таблицы напрямую

---

## ЗАДАЧА 1 — Вынести подкатегории каналов в БД

### Файл: `src/utils/categories.py`

### Контекст
Подкатегории хардкожены в Python-файле (~94 строки). При добавлении новой категории нужно менять код и деплоить. Нужно перенести в БД.

### Что читать перед правкой
```
1. src/utils/categories.py — текущая структура данных
2. src/db/models/analytics.py — модель TelegramChat, поле topic/subcategory
3. src/db/base.py — Base для моделей
4. src/db/migrations/ — шаблон для новой миграции
```

### Что реализовать

**Шаг 1.1 — Создать модель:**
```python
# src/db/models/category.py
class TopicCategory(Base):
    __tablename__ = "topic_categories"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    topic: Mapped[str] = mapped_column(String(100), nullable=False)
    subcategory: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name_ru: Mapped[str] = mapped_column(String(200), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    
    __table_args__ = (
        UniqueConstraint("topic", "subcategory", name="uq_topic_subcategory"),
    )
```

**Шаг 1.2 — Создать миграцию:**
```bash
# Создать файл в src/db/migrations/versions/
# Имя: YYYYMMDD_HHMMSS_add_topic_categories_table.py
# Миграция должна:
# 1. Создать таблицу topic_categories
# 2. Заполнить данными из categories.py (в upgrade())
# 3. В downgrade() — удалить таблицу
```

**Шаг 1.3 — Создать репозиторий:**
```python
# src/db/repositories/category_repo.py
class CategoryRepository(BaseRepository[TopicCategory]):
    async def get_subcategories(self, topic: str) -> list[TopicCategory]
    async def get_all_topics(self) -> list[str]
    async def get_display_name(self, topic: str, subcategory: str) -> str | None
```

**Шаг 1.4 — Обновить `categories.py`:**
```python
# Оставить как FALLBACK (на случай недоступности БД):
CATEGORIES_FALLBACK = { ... }  # старые данные

async def get_subcategories(topic: str, session: AsyncSession) -> list[str]:
    """Берёт из БД, при ошибке — из FALLBACK."""
```

**Шаг 1.5 — Обновить места использования:**
```bash
# Найти все места где используется categories.py:
grep -rn "from src.utils.categories\|from utils.categories" src/
# Обновить каждый вызов
```

### Критерии готовности
- [ ] Таблица `topic_categories` создана и заполнена
- [ ] `categories.py` использует БД как источник истины
- [ ] Есть fallback на статические данные
- [ ] Все места использования обновлены
- [ ] Миграция применяется без ошибок

---

## ЗАДАЧА 2 — Реализовать расчёт ROI кампании

### Файл: `src/core/services/analytics_service.py`

### Контекст
Метод `calculate_roi()` возвращает `revenue=0`. Это делает ROI метрику бесполезной. ROI считается как: `(revenue - cost) / cost * 100%`. Revenue — ценность кликов/просмотров для рекламодателя.

### Что читать перед правкой
```
1. src/core/services/analytics_service.py — найти calculate_roi()
2. src/db/models/campaign.py — поля: clicks_count, total_cost, tracking_short_code
3. src/db/models/mailing_log.py — поля статистики
4. src/api/constants/tariffs.py — есть ли стоимость клика/просмотра
```

### Что реализовать

**Модель расчёта ROI:**
```python
# Упрощённая модель (нет прямой выручки — используем estimated value):
# CPM рынок Telegram RU ≈ 80-150 руб за 1000 просмотров
# CPC рынок Telegram RU ≈ 15-40 руб за клик

ESTIMATED_CPM_RUB = 100  # константа в settings.py или tariffs.py
ESTIMATED_CPC_RUB = 25

estimated_revenue = (
    (total_views / 1000) * ESTIMATED_CPM_RUB +
    total_clicks * ESTIMATED_CPC_RUB
)
roi_percent = ((estimated_revenue - actual_cost) / actual_cost * 100) if actual_cost > 0 else 0
```

**Добавить в `settings.py`:**
```python
ANALYTICS_ESTIMATED_CPM_RUB: float = 100.0
ANALYTICS_ESTIMATED_CPC_RUB: float = 25.0
```

**Сигнатура результата:**
```python
@dataclass
class ROIResult:
    actual_cost: Decimal
    estimated_revenue: Decimal
    roi_percent: float
    total_views: int
    total_clicks: int
    ctr_percent: float
    note: str = "Доход оценочный на основе рыночных CPM/CPC"
```

### Критерии готовности
- [ ] `calculate_roi()` возвращает реальные данные (не `revenue=0`)
- [ ] Константы `ESTIMATED_CPM_RUB` и `ESTIMATED_CPC_RUB` вынесены в settings
- [ ] При `total_cost = 0` — не делить на ноль, вернуть `roi_percent=0`
- [ ] Добавлено поле `note` с пояснением об оценочности
- [ ] ROI отображается в аналитике бота (найти место вывода и убедиться)

---

## ЗАДАЧА 3 — Добавить `last_login_at` для стриков активности

### Контекст
`update_streaks_daily` не работает корректно — нет поля `last_login_at` в таблице users, поэтому стрики не считаются. Нужно добавить поле и логику обновления.

### Что читать перед правкой
```
1. src/db/models/user.py — текущие поля
2. src/tasks/gamification_tasks.py — update_streaks_daily()
3. src/bot/handlers/start.py — обработчик /start (место обновления last_login)
4. src/db/migrations/versions/ — шаблон миграции
```

### Что реализовать

**Шаг 3.1 — Добавить поля в модель `User`:**
```python
# src/db/models/user.py
last_login_at: Mapped[datetime | None] = mapped_column(
    DateTime(timezone=True), nullable=True
)
login_streak_days: Mapped[int] = mapped_column(Integer, default=0)
max_streak_days: Mapped[int] = mapped_column(Integer, default=0)
```

**Шаг 3.2 — Создать миграцию:**
```
Файл: YYYYMMDD_HHMMSS_add_last_login_streak_to_users.py
Добавить: last_login_at, login_streak_days, max_streak_days
```

**Шаг 3.3 — Обновлять при каждом запуске бота:**
```python
# src/bot/handlers/start.py — в обработчике любой команды/callback от пользователя
# Обновлять last_login_at = datetime.utcnow()
# Делать это через UserRepository, не напрямую
```

**Шаг 3.4 — Исправить `update_streaks_daily()`:**
```python
# src/tasks/gamification_tasks.py
async def update_streaks_daily():
    """
    Алгоритм:
    1. Взять всех пользователей с last_login_at >= вчера
    2. Для каждого: streak += 1 если логин вчера или сегодня
    3. Для остальных: streak = 0
    4. Обновить max_streak если streak > max_streak
    5. Начислить XP за стрик (7 дней = 50 XP, 30 дней = 200 XP)
    """
```

### Критерии готовности
- [ ] Поля `last_login_at`, `login_streak_days`, `max_streak_days` добавлены в модель
- [ ] Миграция создана и применяется без ошибок
- [ ] `last_login_at` обновляется при активности пользователя
- [ ] `update_streaks_daily()` использует реальные данные
- [ ] XP начисляется за стрики

---

## ЗАДАЧА 4 — Оптимизация N+1 запросов

### Контекст
Выявлены два места с потенциальными N+1:
1. `src/api/routers/channels.py` — цикл с запросом внутри
2. `src/bot/handlers/cabinet.py` — получение выплат для каждого канала отдельно

### ⚠️ Правило: перед оптимизацией — прочитать код, убедиться что N+1 реально есть

### Что читать перед правкой
```
1. src/api/routers/channels.py — строки 150-180
2. src/bot/handlers/cabinet.py — цикл по каналам
3. src/db/repositories/base.py — доступные методы
4. SQLAlchemy docs: selectinload, joinedload, contains_eager
```

### Что реализовать

**Место 1 — `channels.py`:**
```python
# Если есть:
for tariff in tariffs:
    count = await session.execute(count_query(tariff))

# Заменить на единый запрос:
counts = await session.execute(
    select(Channel.tariff, func.count(Channel.id))
    .group_by(Channel.tariff)
)
counts_dict = {row.tariff: row.count for row in counts}
```

**Место 2 — `cabinet.py`:**
```python
# Если есть:
for channel in channels:
    payout = await payout_repo.get_available_amount(channel.id)

# Заменить на bulk-запрос:
channel_ids = [c.id for c in channels]
payouts = await payout_repo.get_available_amounts_bulk(channel_ids)
# payouts = {channel_id: amount}
```

**Добавить метод в `payout_repo.py`:**
```python
async def get_available_amounts_bulk(
    self, channel_ids: list[int]
) -> dict[int, Decimal]:
    """
    Возвращает {channel_id: available_amount} для всех channel_ids.
    Один SQL запрос с GROUP BY.
    """
```

### Критерии готовности
- [ ] В `channels.py` вместо N запросов — один с GROUP BY
- [ ] В `cabinet.py` выплаты получаются bulk-запросом
- [ ] `get_available_amounts_bulk` добавлен в `payout_repo.py`
- [ ] Логика результата не изменилась — только количество запросов

---

## ЗАДАЧА 5 — Документировать JSON-поля моделей

### Контекст
Несколько моделей имеют JSON-поля без документации их структуры. Это делает разработку очень сложной.

### Файлы для документирования:
```
src/db/models/campaign.py — filters_json, meta_json
src/db/models/analytics.py — recent_posts (comment="Последние 5 постов...")
src/db/models/user.py — если есть JSON поля
```

### Что делать (ТОЛЬКО документация — не менять схему)

Для каждого JSON-поля добавить TypedDict и docstring:

```python
# src/db/models/campaign.py

class CampaignFiltersJSON(TypedDict, total=False):
    """
    Структура поля Campaign.filters_json
    
    Пример:
    {
        "topics": ["technology", "business"],
        "subcategories": ["startups"],
        "min_members": 1000,
        "max_members": 100000,
        "exclude_channels": [123456, 789012],
        "language": "ru",
        "has_bot_admin": True
    }
    """
    topics: list[str]
    subcategories: list[str]
    min_members: int
    max_members: int
    exclude_channels: list[int]
    language: str
    has_bot_admin: bool

class CampaignMetaJSON(TypedDict, total=False):
    """
    Структура поля Campaign.meta_json
    
    Пример:
    {
        "ai_generated": True,
        "ab_variant": "A",
        "source": "wizard",
        "tracking_enabled": True
    }
    """
    ai_generated: bool
    ab_variant: str
    source: str
    tracking_enabled: bool
```

**Для `recent_posts` в `TelegramChat`:**
```python
class RecentPostJSON(TypedDict):
    """
    Структура одного поста в TelegramChat.recent_posts
    
    Пример:
    {
        "message_id": 12345,
        "text": "Первые 200 символов...",
        "views": 1500,
        "date": "2026-03-07T10:00:00Z",
        "has_media": False
    }
    """
    message_id: int
    text: str
    views: int
    date: str
    has_media: bool

# recent_posts: list[RecentPostJSON] — последние 5 постов
```

### Критерии готовности
- [ ] Каждое JSON-поле имеет соответствующий TypedDict
- [ ] TypedDict расположен рядом с моделью в том же файле
- [ ] Добавлен пример структуры в docstring
- [ ] Схема БД не изменена (только Python-типы для документации)

---

## ФИНАЛЬНАЯ ПРОВЕРКА СПРИНТА 3

```bash
# 1. Проверить миграции
alembic check  # или: python -m alembic check

# 2. Проверить импорты новых модулей
python -c "from src.db.models.category import TopicCategory; print('OK')"
python -c "from src.db.repositories.category_repo import CategoryRepository; print('OK')"

# 3. Проверить запуск
python -c "from src.bot.main import main; print('Bot: OK')"
python -c "from src.api.main import app; print('API: OK')"

# 4. Проверить отсутствие новых TODO
grep -rn "TODO\|FIXME\|revenue=0\|placement_id=0" src/core/services/analytics_service.py
grep -rn "TODO\|FIXME" src/tasks/gamification_tasks.py

# 5. Линтер
ruff check src/db/models/ src/db/repositories/ src/core/services/analytics_service.py
```

**Спринт считается завершённым** когда все 5 задач выполнены и миграции применяются без ошибок.
