---
name: celery-task
description: "MUST BE USED for Celery tasks: critical/background/game queues, retry policies, Beat schedules, task signatures, exponential backoff. Use when working with src/tasks/, celery_config.py, async background jobs, mailing campaigns, parser updates, or periodic monitoring tasks. Enforces: bind=True for retries, acks_late, separate queues, run_async() helper."
license: MIT
version: 1.0.0
author: market-telegram-bot
---

# Celery Task Conventions

Создаёт фоновые задачи Celery 5 с правильной обработкой ошибок, retry-логикой
и маршрутизацией по очередям. Мониторинг через Flower на порту 5555.

## When to Use
- Написание фоновых задач в `src/tasks/`
- Настройка периодических задач в Celery Beat
- Обработка рассылок рекламных кампаний
- Парсинг и обновление списка чатов
- Генерация PDF-отчётов
- Обработка платёжных webhook'ов

## Rules
- `bind=True` для всех задач, которые могут делать `self.retry()`
- Роутинг: задачи рассылки → `queue="mailing"`, парсер → `queue="parser"`
- Max retries: 3, countdown: экспоненциальный (1с, 4с, 9с)
- `acks_late=True` на уровне приложения — задачи повторно ставятся в очередь при падении воркера
- Логировать старт/конец задачи через `logger.info()` с task ID

## Instructions

1. Импортируй `app` из `src/tasks/celery_app.py`
2. Декорируй через `@app.task(bind=True, max_retries=3, queue="...")`
3. В теле задачи: логируй старт, выполни работу, логируй завершение
4. Все async-вызовы оборачивай через `run_async()` хелпер
5. Оборачивай в `try/except` с конкретными типами исключений
6. Для периодических задач добавь в `CELERY_BEAT_SCHEDULE` в `celery_config.py`

## Examples

### Task с retry и экспоненциальным backoff
```python
from src.tasks.celery_app import app
from src.utils.async_helpers import run_async
from src.services.mailing import MailingService
from telethon.errors import FloodWaitError
import logging

logger = logging.getLogger(__name__)

@app.task(bind=True, max_retries=3, queue="mailing", acks_late=True)
def send_campaign(self, campaign_id: int) -> dict:
    logger.info("Task %s: starting campaign %d", self.request.id, campaign_id)
    try:
        result = run_async(MailingService().run_campaign(campaign_id))
        logger.info(
            "Task %s: campaign %d completed — sent=%d",
            self.request.id, campaign_id, result["sent"]
        )
        return result
    except FloodWaitError as exc:
        logger.warning("Task %s: FloodWait %ds", self.request.id, exc.value)
        raise self.retry(exc=exc, countdown=exc.value + 5)
    except Exception as exc:
        logger.error("Task %s: error — %s", self.request.id, exc)
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
```

### Celery Beat расписание
```python
# src/tasks/celery_config.py
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    "update-chat-stats": {
        "task": "src.tasks.parser.update_chat_stats",
        "schedule": crontab(hour="*/6"),   # каждые 6 часов
        "queue": "parser",
    },
    "cleanup-expired-campaigns": {
        "task": "src.tasks.cleanup.remove_expired",
        "schedule": crontab(hour=3, minute=0),  # ежедневно в 3:00
        "queue": "mailing",
    },
}
```

### Async helper
```python
# src/utils/async_helpers.py
import asyncio
from typing import TypeVar, Coroutine, Any

T = TypeVar("T")

def run_async(coro: Coroutine[Any, Any, T]) -> T:
    """Run async coroutine from sync Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()
```
