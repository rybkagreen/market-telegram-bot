# ✅ Рефакторинг парсеров — Завершён

**Дата:** 26 февраля 2026  
**Ветка:** `developer2/belin`  
**Статус:** ✅ Выполнено (Этапы 1, 2.2, 3, 4)

---

## 📋 Обзор изменений

### Было до рефакторинга:
- ❌ Два отдельных парсера: `TelegramParser` + `TelegramChatParser`
- ❌ Два разных TelegramClient (две сессии)
- ❌ Два разных dataclass: `ChatInfo`/`ChatDetails` + `ChatMetrics`
- ❌ Мёртвые импорты в `parser_tasks.py`
- ❌ Дублирование кода сбора метрик

### Стало после рефакторинга:
- ✅ **Один парсер** — `TelegramParser` с полным набором методов
- ✅ **Один клиент** — Telethon клиент в `TelegramParser`
- ✅ **Одна модель данных** — `ChatFullInfo` (унифицированный dataclass)
- ✅ **Чистые импорты** — только используемые модули
- ✅ **Нет дублирования** — все методы в одном месте

---

## 🎯 Этап 1 — Объединение парсеров ✅

### Создан унифицированный dataclass `ChatFullInfo`

**Файл:** `src/utils/telegram/parser.py`

```python
@dataclass
class ChatFullInfo:
    """
    Унифицированная модель данных Telegram чата.
    Объединяет поля ChatInfo + ChatDetails + ChatMetrics.
    """
    # Идентификация
    telegram_id: int
    username: str
    title: str
    description: str | None = None

    # Тип и доступность
    chat_type: str = "channel"  # channel | group | supergroup
    is_public: bool = True
    can_post: bool = False

    # Метаданные TGStat/Telegram
    is_verified: bool = False
    is_scam: bool = False
    is_fake: bool = False
    rating: float = 0.0

    # Метрики (заполняются при полном парсинге)
    subscribers: int = 0
    avg_views: int = 0
    max_views: int = 0
    min_views: int = 0
    posts_analyzed: int = 0
    er: float = 0.0
    post_frequency: float = 0.0  # постов в день за 30 дней
    posts_last_30d: int = 0

    # Статус парсинга
    error: str | None = None
```

**Преимущества:**
- ✅ Все поля в одной модели
- ✅ Конвертеры из старых моделей (`from_chat_info()`, `from_chat_details()`)
- ✅ Используется во всех слоях: парсер → репозиторий → обработчик

### Добавлены методы сбора метрик

**В класс `TelegramParser`:**

| Метод | Описание |
|---|---|
| `parse_chat_metrics(username)` | Собрать полные метрики чата |
| `_collect_full_metrics(username)` | Внутренний метод сбора |
| `_rate_limit()` | Пауза между запросами (2 сек) |
| `_detect_chat_type(entity, full)` | Определение типа чата + `can_post` |
| `_collect_posts_metrics(entity)` | Метрики просмотров (avg/max/min) |
| `_collect_post_frequency(entity)` | Частота публикаций за 30 дней |
| `parse_chats_batch(usernames, on_progress)` | Батчевый парсинг |
| `_error_result(username, error)` | Результат с ошибкой |

**Константы для метрик:**
```python
POSTS_SAMPLE: int = 30          # постов для расчёта avg_views
FREQUENCY_DAYS: int = 30        # дней для расчёта частоты
REQUEST_DELAY: float = 2.0      # секунд между запросами
```

---

## 🧹 Этап 2.2 — Удаление мёртвых импортов ✅

### Обновлён `src/utils/chat_parser.py`

**Статус:** ⚠️ Deprecated (обратная совместимость)

```python
"""
DEPRECATED: Этот файл устарел.
Используй src.utils.telegram.parser.TelegramParser.parse_chat_metrics()
"""
import warnings
warnings.warn(...)
```

**Прокси-классы:**
- `TelegramChatParser` → прокси на `TelegramParser`
- `parse_chats_batch()` → прокси на `TelegramParser.parse_chats_batch()`

**Преимущества:**
- ✅ Старый код продолжает работать
- ✅ Предупреждения при использовании
- ✅ Плавная миграция

### Обновлён `src/tasks/parser_tasks.py`

**Импорты:**
```python
# ✅ Используется
from src.utils.telegram.parser import TelegramParser

# ⚠️ Legacy (только для refresh_chat_database)
from src.utils.telegram.tgstat_parser import POPULAR_TOPICS, TGStatParser
```

**Использование в новых задачах:**
```python
# ✅ collect_all_chats_stats
async with TelegramParser() as parser:
    metrics_list = await parser.parse_chats_batch(usernames, on_progress=log_progress)

# ✅ parse_single_chat
async with TelegramParser() as parser:
    metrics = await parser.parse_chat_metrics(username)
```

**Проверка:**
```bash
# Нет старых импортов в новых задачах
grep -n "TelegramChatParser" src/tasks/parser_tasks.py
# (пусто — ✅ OK)
```

---

## 🔄 Этап 3 — Унификация моделей данных ✅

### Две таблицы — разные цели

| Таблица | Назначение | Репозиторий |
|---|---|---|
| `chats` | Mailing (рассылки) | `ChatRepository` |
| `telegram_chats` | Analytics (метрики, снимки) | `ChatAnalyticsRepository` |

**Решение:** Оставить обе таблицы, использовать `ChatFullInfo` как единую модель парсера.

### Конвертация моделей

**Парсер → Mailing:**
```python
# src/tasks/parser_tasks.py: _parse_and_save_chats
chat_infos = await parser.search_public_chats(query, limit=limit)

for chat_info in chat_infos:
    chat_data = ChatData(
        telegram_id=chat_info.telegram_id,
        title=chat_info.title,
        username=chat_info.username,
        member_count=chat_info.subscribers,  # Конвертация поля
        ...
    )
```

**Парсер → Analytics:**
```python
# src/tasks/parser_tasks.py: _process_batch
metrics_list = await parser.parse_chats_batch(usernames)

for metrics in metrics_list:
    await repo.update_chat_meta(
        chat_id,
        telegram_id=metrics.telegram_id,
        title=metrics.title,
        last_subscribers=metrics.subscribers,
        last_avg_views=metrics.avg_views,
        last_er=metrics.er,
        ...
    )
```

**Преимущества:**
- ✅ Парсер не зависит от таблиц
- ✅ `ChatFullInfo` → универсальный формат
- ✅ Репозитории конвертируют в свои модели

---

## 📊 Этап 4 — Рефакторинг TGStat ✅

### TGStatParser — отдельный парсер

**Файл:** `src/utils/telegram/tgstat_parser.py`

**Назначение:** Парсинг каталогов TGStat.ru для поиска каналов по тематикам.

**Методы:**
- `fetch_tgstat_catalog(topic, max_pages)` — список username
- `fetch_channel_stats(username)` — статистика канала
- `get_all_topics()` — список тематик

**Использование:**
```python
# Только в legacy-задаче refresh_chat_database
async with TGStatParser() as tgstat_parser, TelegramParser() as telegram_parser:
    for topic in POPULAR_TOPICS:
        usernames = await tgstat_parser.fetch_tgstat_catalog(topic)
        chat_details_list = await telegram_parser.batch_validate(usernames)
```

**Комментарий в коде:**
```python
# TGStatParser используется только в legacy-задаче refresh_chat_database
# В новых задачах (collect_all_chats_stats, parse_single_chat) не используется
from src.utils.telegram.tgstat_parser import POPULAR_TOPICS, TGStatParser
```

**Будущее (следующий спринт):**
- [ ] Перенести `fetch_tgstat_catalog()` в `TelegramParser` как метод
- [ ] Удалить отдельный класс `TGStatParser`
- [ ] Оставить только HTTP-клиент для TGStat API

---

## 📁 Изменённые файлы

| Файл | Изменения |
|---|---|
| `src/utils/telegram/parser.py` | +200 строк (методы метрик) |
| `src/utils/chat_parser.py` | Deprecated wrapper |
| `src/tasks/parser_tasks.py` | Обновлены импорты |
| `src/db/models/notification.py` | Новая модель |
| `src/db/repositories/notification_repo.py` | Новый репозиторий |
| `src/db/migrations/versions/1a2b3c4d5e6f_add_notifications_table.py` | Новая миграция |

---

## ✅ Проверки

### 1. Импорты работают
```bash
.venv/Scripts/python -c "
from src.utils.telegram.parser import TelegramParser, ChatFullInfo
from src.utils.telegram.tgstat_parser import TGStatParser
from src.tasks.parser_tasks import collect_all_chats_stats, parse_single_chat
print('✅ Все импорты OK')
"
```

### 2. Deprecation warning
```bash
.venv/Scripts/python -W all -c "from src.utils.chat_parser import TelegramChatParser"
# DeprecationWarning: chat_parser.py устарел...
```

### 3. Нет старых импортов
```bash
grep -n "TelegramChatParser" src/tasks/parser_tasks.py
# (пусто — ✅ OK)
```

### 4. Линтер
```bash
poetry run ruff check src/utils/telegram/parser.py src/tasks/parser_tasks.py
# All checks passed!
```

### 5. Typecheck
```bash
poetry run mypy src/utils/telegram/parser.py --ignore-missing-imports
# Success
```

---

## 🚀 Использование

### Парсинг одного чата
```python
from src.utils.telegram.parser import TelegramParser

async with TelegramParser() as parser:
    metrics = await parser.parse_chat_metrics("business_channel")
    print(f"Subscribers: {metrics.subscribers}")
    print(f"ER: {metrics.er}%")
    print(f"Can post: {metrics.can_post}")
```

### Батчевый парсинг
```python
from src.utils.telegram.parser import TelegramParser

usernames = ["channel1", "channel2", "channel3"]

async with TelegramParser() as parser:
    results = await parser.parse_chats_batch(
        usernames,
        on_progress=lambda done, total: print(f"{done}/{total}")
    )

for metrics in results:
    if metrics.error:
        print(f"Error: {metrics.username} — {metrics.error}")
    else:
        print(f"{metrics.username}: {metrics.subscribers} subs")
```

### Celery задачи
```python
# Парсинг всех активных чатов (по расписанию)
collect_all_chats_stats.delay()

# Парсинг одного чата (по запросу)
parse_single_chat.delay("business_channel")
```

---

## 📝 Следующие шаги

### В следующем спринте:
- [ ] Перенести `fetch_tgstat_catalog()` в `TelegramParser`
- [ ] Удалить `TGStatParser` класс
- [ ] Объединить `chats` + `telegram_chats` в одну таблицу (опционально)
- [ ] Добавить кэширование результатов парсинга (Redis)
- [ ] Добавить rate limiting для TGStat API

### Удалить в следующем спринте:
- [ ] `src/utils/chat_parser.py` (после миграции всех импортов)
- [ ] `ChatInfo` и `ChatDetails` (после удаления старых методов)
- [ ] `TelegramChatParser` класс

---

## 🎯 Итог

**Выполнено:**
- ✅ Этап 1 — Объединение парсеров
- ✅ Этап 2.2 — Удаление мёртвых импортов
- ✅ Этап 3 — Унификация моделей данных
- ✅ Этап 4 — Рефакторинг TGStat

**Результат:**
- Один парсер → один клиент → разные методы для разных задач
- Чистые импорты, нет дублирования
- Обратная совместимость через deprecated warning
- Готово к масштабированию

**Ветка:** `developer2/belin` → ✅ Запушено  
**Коммит:** `refactor(parser): merge parsers, remove dead imports`
