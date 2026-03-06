"""
Celery конфигурация и дополнительные настройки.
Вынесено в отдельный модуль для удобства импорта.
"""

from typing import Any

from celery.schedules import crontab

# =============================================================================
# CELERY BEAT SCHEDULE
# =============================================================================

BEAT_SCHEDULE = {
    # Обновление базы данных чатов — каждые 24 часа в 03:00 UTC
    "refresh-chat-database": {
        "task": "src.tasks.parser_tasks.refresh_chat_database",
        "schedule": crontab(hour=3, minute=0),
        "options": {"queue": "parser"},
    },
    # Проверка запланированных кампаний — каждые 5 минут
    "check-scheduled-campaigns": {
        "task": "src.tasks.mailing_tasks.check_scheduled_campaigns",
        "schedule": crontab(minute="*/5"),
        "options": {"queue": "mailing"},
    },
    # Удаление старых логов — каждое воскресенье в 03:00 UTC
    "delete-old-logs": {
        "task": "src.tasks.cleanup_tasks.delete_old_logs",
        "schedule": crontab(hour=3, minute=0, day_of_week=0),
        "options": {"queue": "cleanup"},
    },
    # Проверка низкого баланса пользователей — каждый час
    "check-low-balance": {
        "task": "src.tasks.notification_tasks.check_low_balance",
        "schedule": crontab(minute=0),
        "options": {"queue": "mailing"},
    },
    # Обновление статистики чатов — каждые 6 часов
    "update-chat-statistics": {
        "task": "src.tasks.parser_tasks.update_chat_statistics",
        "schedule": crontab(hour="*/6"),
        "options": {"queue": "parser"},
    },
    # Архивация старых кампаний — 1-го числа каждого месяца в 04:00 UTC
    "archive-old-campaigns": {
        "task": "src.tasks.cleanup_tasks.archive_old_campaigns",
        "schedule": crontab(hour=4, minute=0, day_of_month=1),
        "options": {"queue": "cleanup"},
    },
    # Автоодобрение заявок — каждый час
    "auto-approve-pending-placements": {
        "task": "src.tasks.mailing_tasks.auto_approve_pending_placements",
        "schedule": crontab(minute=0),
        "options": {"queue": "mailing"},
    },
}

# =============================================================================
# TASK ROUTES
# =============================================================================

TASK_ROUTES = {
    # Очередь mailing — задачи рассылки
    "mailing.*": {"queue": "mailing"},
    "src.tasks.mailing_tasks.*": {"queue": "mailing"},
    "src.tasks.notification_tasks.*": {"queue": "mailing"},
    # Очередь parser — задачи парсера
    "parser.*": {"queue": "parser"},
    "src.tasks.parser_tasks.*": {"queue": "parser"},
    # Очередь cleanup — задачи очистки
    "cleanup.*": {"queue": "cleanup"},
    "src.tasks.cleanup_tasks.*": {"queue": "cleanup"},
    # Очередь ai — задачи ИИ
    "ai.*": {"queue": "ai"},
    "src.tasks.ai_tasks.*": {"queue": "ai"},
}

# =============================================================================
# TASK TIME LIMITS
# =============================================================================

TASK_TIME_LIMITS = {
    # Рассылки — длительный лимит
    "src.tasks.mailing_tasks.send_campaign": 600,  # 10 минут
    "src.tasks.mailing_tasks.check_scheduled_campaigns": 300,  # 5 минут
    # Парсер — средний лимит
    "src.tasks.parser_tasks.refresh_chat_database": 1800,  # 30 минут
    "src.tasks.parser_tasks.validate_username": 60,  # 1 минута
    # Очистка — длительный лимит
    "src.tasks.cleanup_tasks.delete_old_logs": 600,  # 10 минут
    "src.tasks.cleanup_tasks.archive_old_campaigns": 300,  # 5 минут
}

# =============================================================================
# TASK RETRY POLICY
# =============================================================================

TASK_RETRY_POLICY = {
    "max_retries": 3,
    "interval_start": 60,  # 1 минута
    "interval_step": 60,  # 1 минута
    "interval_max": 600,  # 10 минут
}

# Retry policy для конкретных задач
TASK_SPECIFIC_RETRY = {
    "src.tasks.mailing_tasks.send_campaign": {
        "max_retries": 5,
        "interval_start": 30,
        "interval_step": 60,
        "interval_max": 300,
    },
    "src.tasks.parser_tasks.refresh_chat_database": {
        "max_retries": 2,
        "interval_start": 300,
        "interval_step": 300,
        "interval_max": 600,
    },
}

# =============================================================================
# QUEUE CONFIGURATION
# =============================================================================

QUEUE_CONFIG = {
    "mailing": {
        "max_tasks_per_child": 100,
        "prefetch_multiplier": 1,
        "concurrency": 4,
    },
    "parser": {
        "max_tasks_per_child": 50,
        "prefetch_multiplier": 1,
        "concurrency": 2,
    },
    "cleanup": {
        "max_tasks_per_child": 100,
        "prefetch_multiplier": 1,
        "concurrency": 1,
    },
    "ai": {
        "max_tasks_per_child": 50,
        "prefetch_multiplier": 1,
        "concurrency": 2,
    },
}

# =============================================================================
# MONITORING
# =============================================================================

# Flower configuration
FLOWER_CONFIG = {
    "port": 5555,
    "basic_auth": None,  # Можно добавить username:password
    "persistent": True,
    "db": "flower_data",
}

# Prometheus metrics
METRICS_CONFIG = {
    "enabled": True,
    "prefix": "market_bot",
    "labels": ["task_name", "status", "queue"],
}

# =============================================================================
# RESULT BACKEND
# =============================================================================

RESULT_CONFIG = {
    "expires": 3600,  # 1 час
    "persistent": True,
    "extended": True,  # Хранить args, kwargs
}

# =============================================================================
# EVENT CONFIGURATION
# =============================================================================

EVENT_CONFIG = {
    "task_events": True,  # Отправлять события о задачах
    "worker_events": True,  # Отправлять события о воркерах
}

# =============================================================================
# SECURITY
# =============================================================================

SECURITY_CONFIG = {
    "task_signing": False,  # Можно включить для подписи задач
    "message_encryption": False,  # Можно включить для шифрования
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def get_task_schedule(task_name: str) -> dict[str, Any] | None:
    """
    Получить расписание для задачи.

    Args:
        task_name: Имя задачи.

    Returns:
        Расписание или None.
    """
    return BEAT_SCHEDULE.get(task_name)


def get_task_route(task_name: str) -> str:
    """
    Получить очередь для задачи.

    Args:
        task_name: Имя задачи.

    Returns:
        Название очереди.
    """
    for pattern, route in TASK_ROUTES.items():
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            if task_name.startswith(prefix):
                return route["queue"]
        elif task_name == pattern:
            return route["queue"]
    return "celery"  # Default queue


def get_task_time_limit(task_name: str) -> int:
    """
    Получить таймаут для задачи.

    Args:
        task_name: Имя задачи.

    Returns:
        Таймаут в секундах.
    """
    return TASK_TIME_LIMITS.get(task_name, 300)  # Default 5 минут


def get_retry_policy(task_name: str) -> dict[str, Any]:
    """
    Получить политику retry для задачи.

    Args:
        task_name: Имя задачи.

    Returns:
        Политика retry.
    """
    if task_name in TASK_SPECIFIC_RETRY:
        return TASK_SPECIFIC_RETRY[task_name]
    return TASK_RETRY_POLICY
