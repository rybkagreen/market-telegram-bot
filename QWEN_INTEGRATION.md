# Qwen AI Интеграция — Руководство

## 📋 Обзор

Интеграция Qwen моделей от Alibaba через OpenRouter API для задач:
- **Модерация контента** — проверка на запрещённые темы
- **Классификация каналов** — определение тематики Telegram каналов
- **Генерация текста** — создание рекламных объявлений

---

## 🔧 Настройки

### Переменные окружения (.env)

```bash
# Основная бесплатная модель (для модерации — без rate limit)
MODEL_FREE=stepfun/step-3.5-flash:free

# Fallback модель (если основная недоступна)
MODEL_FREE_FALLBACK=qwen/qwen3-coder:free

# Платная модель для PRO/BUSINESS тарифов
MODEL_PAID=qwen/qwen-plus

# Дополнительные Qwen модели
MODEL_QWEN_CODER_FREE=qwen/qwen3-coder:free    # Для классификации
MODEL_QWEN_TURBO=qwen/qwen-turbo               # Дешёвая ($0.002/1K tokens)
MODEL_QWEN_PLUS=qwen/qwen-plus                 # Качественная ($0.04/1K tokens)
```

---

## 📦 Компоненты

### 1. QwenAIService (`src/core/services/qwen_ai_service.py`)

Основной сервис для работы с Qwen моделями.

**Использование:**

```python
from src.core.services.qwen_ai_service import QwenAIService

service = QwenAIService(redis=redis_client)  # redis опционально

# Модерация контента (асинхронно)
result = await service.moderate_content(
    text="Проверь этот текст на запрещённый контент",
    use_paid=False
)

if not result.passed:
    print(f"Заблокировано: {result.categories}")

# Классификация канала (асинхронно)
result = await service.classify_channel(
    title="Бизнес Новости",
    username="biznes_news",
    description="Новости бизнеса и экономики",
    member_count=10000,
    posts=["пост 1", "пост 2"],
)

print(f"Тематика: {result.topic}")
print(f"Рейтинг: {result.rating}/10")
```

**Методы:**

| Метод | Описание | Возвращает |
|---|---|---|
| `moderate_content(text)` | Проверка контента | `QwenModerationResult` |
| `moderate_content_sync(text)` | Синхронная модерация (для Celery) | `QwenModerationResult` |
| `classify_channel(title, ...)` | Классификация канала | `QwenClassificationResult` |
| `classify_channel_sync(title, ...)` | Синхронная классификация | `QwenClassificationResult` |

---

### 2. TokenUsageLogger (`src/core/services/token_logger.py`)

Логирование использования токенов в Redis.

**Использование:**

```python
from src.core.services.token_logger import token_logger

# Записать использование
await token_logger.log_usage(
    model="qwen/qwen-plus",
    prompt_tokens=100,
    completion_tokens=50,
    total_tokens=150,
    task_type="classification",
    cost_usd=0.006
)

# Получить статистику
stats = await token_logger.get_stats()
print(stats)
# {'qwen/qwen-plus': {'total_requests': '100', 'total_tokens': '15000', ...}}

# Последние использования
recent = await token_logger.get_recent_usage(limit=10)
```

**Redis ключи:**
- `qwen:token_usage` — список последних 1000 записей
- `qwen:stats:{model}` — агрегированная статистика по модели (TTL 30 дней)

---

## 🎯 Модели

### Бесплатные

| Модель | Назначение | Rate Limit | Качество |
|---|---|---|---|
| `stepfun/step-3.5-flash:free` | Модерация | Нет | Хорошее |
| `qwen/qwen3-coder:free` | Классификация | ~8 req/min | Отличное |

### Платные

| Модель | Цена | Назначение | Качество |
|---|---|---|---|
| `qwen/qwen-turbo` | $0.002/1K tokens | Быстрая модерация | Хорошее |
| `qwen/qwen-plus` | $0.04/1K tokens | Точная классификация | Отличное |

---

## 📊 Интеграция в проект

### Content Filter

Автоматически использует Qwen для LLM-уровня:

```python
# src/utils/content_filter/filter.py
from src.core.services.qwen_ai_service import qwen_ai_service

result = qwen_ai_service.moderate_content_sync(text, timeout=30)
```

### LLM Classifier

Автоматически использует Qwen для классификации:

```python
# src/utils/telegram/llm_classifier.py
from src.core.services.qwen_ai_service import qwen_ai_service

result = await qwen_ai_service.classify_channel(...)
```

---

## 🔍 Мониторинг

### Проверка использования токенов

```bash
# На сервере
docker compose exec worker python -c "
from src.core.services.token_logger import token_logger
import asyncio

async def check():
    stats = await token_logger.get_stats()
    for model, data in stats.items():
        print(f'{model}:')
        print(f'  Requests: {data.get(\"total_requests\", 0)}')
        print(f'  Tokens: {data.get(\"total_tokens\", 0)}')
        print(f'  Cost: ${data.get(\"total_cost_usd\", 0):.4f}')

asyncio.run(check())
"
```

### Логи Qwen

```bash
# Поиск ошибок Qwen в логах
docker compose logs worker | grep -i 'Qwen.*error'

# Поиск успешных классификаций
docker compose logs worker | grep -i 'classification.*OK'
```

---

## ⚠️ Решение проблем

### Ошибка 429 (Rate Limit)

**Симптомы:**
```
Error code: 429 - Rate limit exceeded
```

**Решение:**
1. Использовать `stepfun/step-3.5-flash:free` для модерации (нет rate limit)
2. Добавить задержки между запросами
3. Использовать платную модель

### Ошибка 404 (Модель не найдена)

**Симптомы:**
```
Error code: 404 - No endpoints found for model
```

**Решение:**
1. Проверить название модели на https://openrouter.ai/models
2. Обновить `MODEL_FREE` в .env

### Ошибка JSON парсинга

**Симптомы:**
```
Expecting ',' delimiter: line 2 column 19
```

**Решение:**
1. Модель возвращает некорректный JSON
2. Использовать fallback модель
3. Упростить промпт

---

## 💰 Стоимость

### Пример расчёта

**Задача:** Классификация 1000 каналов

| Модель | Токенов/запрос | Всего токенов | Стоимость |
|---|---|---|---|
| `qwen/qwen3-coder:free` | ~500 | 500,000 | $0 (бесплатно) |
| `qwen/qwen-turbo` | ~500 | 500,000 | $1.00 |
| `qwen/qwen-plus` | ~500 | 500,000 | $20.00 |

**Рекомендация:**
- Использовать бесплатные модели для массовых задач
- Платные — только для PRO/BUSINESS тарифов

---

## 📝 Changelog

### v1.0 (2026-03-06)
- ✨ Добавлена интеграция Qwen через OpenRouter
- ✨ Создан `QwenAIService` для модерации и классификации
- ✨ Добавлен `TokenUsageLogger` для мониторинга
- 🔧 Обновлены настройки моделей в `settings.py`
- 🐛 Исправлены проблемы с rate limit

---

## 📚 Ссылки

- [OpenRouter API](https://openrouter.ai/docs)
- [Qwen Models](https://openrouter.ai/models?q=qwen)
- [Alibaba Qwen](https://qwenlm.github.io/)
