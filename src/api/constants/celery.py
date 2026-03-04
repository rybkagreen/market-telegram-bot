"""
Константы Celery задач Market Bot.
"""

# Очереди
MAILING_QUEUE: str = "mailing"
PARSER_QUEUE: str = "parser"
CLEANUP_QUEUE: str = "cleanup"
AI_QUEUE: str = "ai"
DEFAULT_QUEUE: str = "celery"

# Расписание задач (BEAT SCHEDULE)
CELERY_BEAT_SCHEDULE = {
    # Обновление базы данных чатов — каждые 24 часа в 03:00 UTC
    "refresh-chat-database": {
        "task": "src.tasks.parser_tasks.refresh_chat_database",
        "schedule": "crontab(hour=3, minute=0)",
        "queue": PARSER_QUEUE,
    },
    # Проверка запланированных кампаний — каждые 5 минут
    "check-scheduled-campaigns": {
        "task": "src.tasks.mailing_tasks.check_scheduled_campaigns",
        "schedule": "crontab(minute='*/5')",
        "queue": MAILING_QUEUE,
    },
    # Удаление старых логов — каждое воскресенье в 03:00 UTC
    "delete-old-logs": {
        "task": "src.tasks.cleanup_tasks.delete_old_logs",
        "schedule": "crontab(hour=3, minute=0, day_of_week=0)",
        "queue": CLEANUP_QUEUE,
    },
    # Проверка низкого баланса пользователей — каждый час
    "check-low-balance": {
        "task": "src.tasks.notification_tasks.check_low_balance",
        "schedule": "crontab(minute=0)",
        "queue": MAILING_QUEUE,
    },
    # Обновление статистики чатов — каждые 6 часов
    "update-chat-statistics": {
        "task": "src.tasks.parser_tasks.update_chat_statistics",
        "schedule": "crontab(hour='*/6')",
        "queue": PARSER_QUEUE,
    },
    # Архивация старых кампаний — 1-го числа каждого месяца в 04:00 UTC
    "archive-old-campaigns": {
        "task": "src.tasks.cleanup_tasks.archive_old_campaigns",
        "schedule": "crontab(hour=4, minute=0, day_of_month=1)",
        "queue": CLEANUP_QUEUE,
    },
    # Очистка бесполезных каналов — каждое воскресенье в 03:30 UTC
    "cleanup-useless-channels": {
        "task": "cleanup:cleanup_useless_channels",
        "schedule": "crontab(hour=3, minute=30, day_of_week=0)",
        "queue": CLEANUP_QUEUE,
    },
    # LLM-переклассификация каналов — каждое воскресенье в 02:00 UTC
    "llm-reclassify-channels": {
        "task": "parser:llm_reclassify_all",
        "schedule": "crontab(day_of_week='sunday', hour='2', minute='0')",
        "queue": PARSER_QUEUE,
        "kwargs": {"batch_size": 50},
    },
}

# Маршрутизация задач
CELERY_TASK_ROUTES = {
    # Очередь mailing — задачи рассылки
    "mailing.*": {"queue": MAILING_QUEUE},
    "src.tasks.mailing_tasks.*": {"queue": MAILING_QUEUE},
    "src.tasks.notification_tasks.*": {"queue": MAILING_QUEUE},
    # Очередь parser — задачи парсера
    "parser.*": {"queue": PARSER_QUEUE},
    "src.tasks.parser_tasks.*": {"queue": PARSER_QUEUE},
    # Очередь cleanup — задачи очистки
    "cleanup.*": {"queue": CLEANUP_QUEUE},
    "src.tasks.cleanup_tasks.*": {"queue": CLEANUP_QUEUE},
    # Очередь ai — задачи ИИ
    "ai.*": {"queue": AI_QUEUE},
    "src.tasks.ai_tasks.*": {"queue": AI_QUEUE},
}

# Таймауты задач (секунды)
CELERY_TASK_TIME_LIMITS = {
    "src.tasks.mailing_tasks.send_campaign": 600,  # 10 минут
    "src.tasks.mailing_tasks.check_scheduled_campaigns": 300,  # 5 минут
    "src.tasks.parser_tasks.refresh_chat_database": 1800,  # 30 минут
    "src.tasks.parser_tasks.validate_username": 60,  # 1 минута
    "src.tasks.cleanup_tasks.delete_old_logs": 600,  # 10 минут
    "src.tasks.cleanup_tasks.archive_old_campaigns": 300,  # 5 минут
}

# Политика retry
CELERY_RETRY_POLICY = {
    "max_retries": 3,
    "interval_start": 60,  # 1 минута
    "interval_step": 60,  # 1 минута
    "interval_max": 600,  # 10 минут
}
