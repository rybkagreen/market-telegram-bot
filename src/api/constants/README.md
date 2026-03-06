# Константы приложения Market Bot

Централизованное хранилище всех констант проекта в модуле `src.api.constants`.

## Структура модулей

### `__init__.py`
Главный файл экспорта. Импортируйте константы отсюда:

```python
from src.api.constants import (
    TARIFF_CREDIT_COST,
    CREDIT_PACKAGES,
    LEVEL1_THRESHOLD,
    CELERY_BEAT_SCHEDULE,
)
```

### `tariffs.py`
Константы тарифных планов:
- `TARIFF_CREDIT_COST` — стоимость тарифов в кредитах
- `TARIFF_SUBSCRIBER_LIMITS` — ограничения по подписчикам
- `TARIFF_MIN_RATING` — минимальный рейтинг канала
- `TARIFF_TOPICS` — доступные топики
- `PREMIUM_SUBSCRIBER_THRESHOLD` — порог premium каналов (1M)

### `payments.py`
Константы платёжной системы:
- `CREDIT_PACKAGES` — пакеты кредитов для покупки
- `CREDIT_PACKAGE_STANDARD` — бонус стандартного пакета (100 кр)
- `CREDIT_PACKAGE_BUSINESS` — бонус бизнес пакета (500 кр)
- `CURRENCIES` / `CRYPTO_CURRENCIES` — список криптовалют
- `PAYMENT_METHODS` — методы оплаты (cryptobot, stars)

### `parser.py`
Константы парсера Telegram:
- `SEARCH_QUERIES` — 333 поисковых запроса по категориям
- `SEARCH_QUERIES_BY_CATEGORY` — запросы, сгруппированные по категориям (7 категорий)
- `TOPIC_SEARCH_QUERIES` — 63 запроса по 8 темам (дополнительно)
- `PARSER_POSTS_SAMPLE` — количество постов для анализа (50)
- `PARSER_RATE_LIMIT_DELAY` — задержка rate limiting (0.5 сек)
- `POPULAR_TOPICS` — популярные тематики (45 тем)

### `content_filter.py`
Константы контент-фильтра:
- `LEVEL1_THRESHOLD` — порог regex проверки (0.2)
- `LEVEL2_THRESHOLD` — порог pymorphy3 проверки (0.5)
- `LEVEL3_THRESHOLD` — порог LLM проверки (0.7)
- `BLOCKED_CATEGORIES` — 8 заблокированных категорий

### `celery.py`
Константы Celery задач:
- `CELERY_BEAT_SCHEDULE` — расписание периодических задач
- `CELERY_TASK_ROUTES` — маршрутизация по очередям
- `CELERY_TASK_TIME_LIMITS` — таймауты задач
- `CELERY_RETRY_POLICY` — политика retry
- `MAILING_QUEUE`, `PARSER_QUEUE`, `CLEANUP_QUEUE`, `AI_QUEUE` — имена очередей

### `limits.py`
Ограничения по тарифам:
- `FREE_AI_GENERATIONS` — 0
- `STARTER_AI_GENERATIONS` — 0
- `PRO_AI_GENERATIONS` — 5
- `BUSINESS_AI_GENERATIONS` — 20

- `FREE_CAMPAIGN_LIMIT` — 0
- `STARTER_CAMPAIGN_LIMIT` — 5
- `PRO_CAMPAIGN_LIMIT` — 20
- `BUSINESS_CAMPAIGN_LIMIT` — 100

- `FREE_CHAT_LIMIT` — 0
- `STARTER_CHAT_LIMIT` — 50
- `PRO_CHAT_LIMIT` — 200
- `BUSINESS_CHAT_LIMIT` — 1000

- `AI_COST_PER_GENERATION` — 10 кр
- `REFERRAL_BONUS` — 50 кр
- `LOW_BALANCE_THRESHOLD` — 50 кр

## Примеры использования

### Тарифы
```python
from src.api.constants import TARIFF_CREDIT_COST

plan_cost = TARIFF_CREDIT_COST["pro"]  # 999
```

### Платежи
```python
from src.api.constants import CREDIT_PACKAGES

for label, credits, bonus, value in CREDIT_PACKAGES:
    print(f"{label}: {credits} кр (+{bonus} бонус)")
```

### Парсер
```python
from src.api.constants import SEARCH_QUERIES, PARSER_POSTS_SAMPLE

for query in SEARCH_QUERIES[:10]:  # Первые 10 запросов
    chats = await parser.search_public_chats(query, limit=PARSER_POSTS_SAMPLE)
```

### Контент-фильтр
```python
from src.api.constants import LEVEL3_THRESHOLD, BLOCKED_CATEGORIES

if score >= LEVEL3_THRESHOLD:
    result.passed = False
    result.categories.extend(BLOCKED_CATEGORIES)
```

### Celery
```python
from src.api.constants import CELERY_BEAT_SCHEDULE, MAILING_QUEUE

# Расписание доступно в celery_config.py
schedule = CELERY_BEAT_SCHEDULE["check-scheduled-campaigns"]
```

### Лимиты
```python
from src.api.constants import PRO_AI_GENERATIONS, PRO_CAMPAIGN_LIMIT

if user.ai_generations_used >= PRO_AI_GENERATIONS:
    raise LimitExceeded("Превышен лимит ИИ-генераций")
```

## Обновление констант

Для изменения констант:
1. Откройте соответствующий модуль в `src/api/constants/`
2. Измените значение
3. Закоммитьте изменения
4. Перезапустите бота и воркеры

**Важно:** Не изменяйте константы в production без тестирования на develop!

## Миграция старого кода

Если вы нашли константы в других файлах, перенесите их в соответствующий модуль:

```python
# БЫЛО (в billing.py):
CREDIT_PACKAGES = [("300 кр", 300, 0, "300"), ...]

# СТАЛО (импорт из constants):
from src.api.constants import CREDIT_PACKAGES
```
