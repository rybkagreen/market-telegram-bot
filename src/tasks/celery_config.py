"""
Celery конфигурация и дополнительные настройки.
Вынесено в отдельный модуль для удобства импорта.
"""

from typing import Any

from celery.schedules import crontab

# =============================================================================
# QUEUE NAME CONSTANTS
# =============================================================================

QUEUE_MAILING = "mailing"
QUEUE_PARSER = "parser"
QUEUE_CLEANUP = "cleanup"
QUEUE_RATING = "rating"
QUEUE_GAMIFICATION = "gamification"
QUEUE_WORKER_CRITICAL = "worker_critical"

TASK_REFRESH_CHAT_DB = "src.tasks.parser_tasks.refresh_chat_database"

# =============================================================================
# CELERY BEAT SCHEDULE
# =============================================================================

BEAT_SCHEDULE = {
    # Обновление базы данных чатов — каждые 24 часа в 03:00 UTC
    "refresh-chat-database": {
        "task": TASK_REFRESH_CHAT_DB,
        "schedule": crontab(hour=3, minute=0),
        "options": {"queue": QUEUE_PARSER},
    },
    # Проверка запланированных кампаний — каждые 5 минут
    "check-scheduled-campaigns": {
        "task": "src.tasks.mailing_tasks.check_scheduled_campaigns",
        "schedule": crontab(minute="*/5"),
        "options": {"queue": QUEUE_MAILING},
    },
    # Удаление старых логов — каждое воскресенье в 03:00 UTC
    "delete-old-logs": {
        "task": "src.tasks.cleanup_tasks.delete_old_logs",
        "schedule": crontab(hour=3, minute=0, day_of_week=0),
        "options": {"queue": QUEUE_CLEANUP},
    },
    # Проверка низкого баланса пользователей — каждый час
    "check-low-balance": {
        "task": "src.tasks.notification_tasks.check_low_balance",
        "schedule": crontab(minute=0),
        "options": {"queue": QUEUE_MAILING, "priority": 8, "expires": 60},
    },
    # Обновление статистики чатов — каждые 6 часов
    "update-chat-statistics": {
        "task": "src.tasks.parser_tasks.update_chat_statistics",
        "schedule": crontab(hour="*/6"),
        "options": {"queue": QUEUE_PARSER},
    },
    # Архивация старых кампаний — 1-го числа каждого месяца в 04:00 UTC
    "archive-old-campaigns": {
        "task": "src.tasks.cleanup_tasks.archive_old_campaigns",
        "schedule": crontab(hour=4, minute=0, day_of_month=1),
        "options": {"queue": QUEUE_CLEANUP},
    },
    # Пересчёт рейтингов каналов — ежедневно в 04:00 UTC
    "recalculate-ratings-daily": {
        "task": "src.tasks.rating_tasks.recalculate_ratings_daily",
        "schedule": crontab(hour=4, minute=0),
        "options": {"queue": QUEUE_RATING},
    },
    # Обновление еженедельных топов — каждый понедельник в 05:00 UTC
    "update-weekly-toplists": {
        "task": "src.tasks.rating_tasks.update_weekly_toplists",
        "schedule": crontab(hour=5, minute=0, day_of_week=1),
        "options": {"queue": QUEUE_RATING},
    },
    # Обновление стриков активности — ежедневно в 00:00 UTC
    "update-streaks-daily": {
        "task": "src.tasks.gamification_tasks.update_streaks_daily",
        "schedule": crontab(hour=0, minute=0),
        "options": {"queue": QUEUE_GAMIFICATION},
    },
    # Еженедельный дайджест — каждый понедельник в 10:00 UTC
    "send-weekly-digest": {
        "task": "src.tasks.gamification_tasks.send_weekly_digest",
        "schedule": crontab(hour=10, minute=0, day_of_week=1),
        "options": {"queue": QUEUE_GAMIFICATION},
    },
    # Проверка сезонных событий — ежедневно в 08:00 UTC
    "check-seasonal-events": {
        "task": "src.tasks.gamification_tasks.check_seasonal_events",
        "schedule": crontab(hour=8, minute=0),
        "options": {"queue": QUEUE_GAMIFICATION},
    },
    # TASK 6: Автоодобрение заявок — каждый час в 00 минут
    "auto-approve-placements": {
        "task": "src.tasks.notification_tasks.auto_approve_placements",
        "schedule": crontab(minute=0),
        "options": {"queue": QUEUE_MAILING, "priority": 7, "expires": 60},
    },
    # TASK 6: Напоминания о заявках — каждые 2 часа
    "placement-reminders": {
        "task": "src.tasks.notification_tasks.notify_pending_placement_reminders",
        "schedule": crontab(minute=0, hour="*/2"),
        "options": {"queue": QUEUE_MAILING, "priority": 6, "expires": 120},
    },
    # TASK 8: Уведомления об истечении тарифа — ежедневно в 10:00 UTC
    "notify-expiring-plans": {
        "task": "src.tasks.notification_tasks.notify_expiring_plans",
        "schedule": crontab(hour=10, minute=0),
        "options": {"queue": QUEUE_MAILING, "priority": 8, "expires": 300},
    },
    # TASK 8: Уведомления об истёкшем тарифе — ежедневно в 10:05 UTC
    "notify-expired-plans": {
        "task": "src.tasks.notification_tasks.notify_expired_plans",
        "schedule": crontab(hour=10, minute=5),
        "options": {"queue": QUEUE_MAILING, "priority": 8, "expires": 300},
    },
    # TASK 8.3: Ежедневная проверка достижений — ежедневно в 00:00 UTC
    "daily-badge-check": {
        "task": "src.tasks.badge_tasks.daily_badge_check",
        "schedule": crontab(hour=0, minute=0),
        "options": {"queue": QUEUE_GAMIFICATION},
    },
    # TASK 8.6: Топ рекламодателей месяца — 1-го числа каждого месяца в 00:00 UTC
    "monthly-top-advertisers": {
        "task": "src.tasks.badge_tasks.monthly_top_advertisers",
        "schedule": crontab(hour=0, minute=0, day_of_month=1),
        "options": {"queue": QUEUE_GAMIFICATION},
    },
    # S9: Проверка целостности данных — каждые 6 часов
    "data-integrity-check": {
        "task": "integrity:check_data_integrity",
        "schedule": crontab(hour="*/6", minute=0),
        "options": {"queue": QUEUE_CLEANUP},
    },
    # S9: Мониторинг здоровья опубликованных постов — каждые 6 часов
    "check-published-posts-health": {
        "task": "placement:check_published_posts_health",
        "schedule": crontab(hour="*/6", minute=30),
        "options": {"queue": QUEUE_WORKER_CRITICAL, "expires": 300},
    },
    # Scheduled deletions check — каждые 5 минут (consolidated from publication_tasks)
    "placement-check-scheduled-deletions": {
        "task": "placement:check_scheduled_deletions",
        "schedule": crontab(minute="*/5"),
        "options": {"queue": QUEUE_WORKER_CRITICAL, "expires": 60},
    },
    # Tax calendar reminder — ежедневно в 09:00 MSK (06:00 UTC)
    "tax-calendar-reminder": {
        "task": "tax:calendar_reminder",
        "schedule": crontab(hour=6, minute=0),  # 09:00 MSK = 06:00 UTC
        "options": {"queue": "billing"},
    },
    # PLACEMENT SLA CHECKS (каждые 5 минут)
    "placement-check-owner-sla": {
        "task": "placement:check_owner_response_sla",
        "schedule": crontab(minute="*/5"),
        "options": {"queue": QUEUE_WORKER_CRITICAL, "expires": 60},
    },
    "placement-check-payment-sla": {
        "task": "placement:check_payment_sla",
        "schedule": crontab(minute="*/5"),
        "options": {"queue": QUEUE_WORKER_CRITICAL, "expires": 60},
    },
    "placement-check-counter-sla": {
        "task": "placement:check_counter_offer_sla",
        "schedule": crontab(minute="*/5"),
        "options": {"queue": QUEUE_WORKER_CRITICAL, "expires": 60},
    },
    # ESCROW SLA CHECK — detect stalled placements (Fix 2)
    "placement-check-escrow-sla": {
        "task": "placement:check_escrow_sla",
        "schedule": crontab(minute="*/5"),
        "options": {"queue": QUEUE_WORKER_CRITICAL, "expires": 60},
    },
}

# =============================================================================
# TASK ROUTES
# =============================================================================

TASK_ROUTES = {
    # Очередь mailing — задачи рассылки
    "mailing.*": {"queue": QUEUE_MAILING},
    "src.tasks.mailing_tasks.*": {"queue": QUEUE_MAILING},
    "src.tasks.notification_tasks.*": {"queue": QUEUE_MAILING},
    # Очередь notifications — уведомления пользователей
    "notifications.*": {"queue": "notifications"},
    # Очередь parser — задачи парсера
    "parser.*": {"queue": QUEUE_PARSER},
    "src.tasks.parser_tasks.*": {"queue": QUEUE_PARSER},
    # Очередь cleanup — задачи очистки
    "cleanup.*": {"queue": QUEUE_CLEANUP},
    "src.tasks.cleanup_tasks.*": {"queue": QUEUE_CLEANUP},
    # Очередь ai — задачи ИИ
    "ai.*": {"queue": "ai"},
    "src.tasks.ai_tasks.*": {"queue": "ai"},
    # Очередь rating — задачи рейтингов
    "rating.*": {"queue": QUEUE_RATING},
    "src.tasks.rating_tasks.*": {"queue": QUEUE_RATING},
    # Очередь gamification — задачи геймификации
    "gamification.*": {"queue": QUEUE_GAMIFICATION},
    "src.tasks.gamification_tasks.*": {"queue": QUEUE_GAMIFICATION},
    # Очередь badges — задачи достижений
    "badges.*": {"queue": QUEUE_GAMIFICATION},
    "src.tasks.badge_tasks.*": {"queue": QUEUE_GAMIFICATION},
    # Очередь billing — задачи биллинга
    "billing.*": {"queue": "billing"},
    "src.tasks.billing_tasks.*": {"queue": "billing"},
    # Очередь tax — налоговые задачи
    "tax.*": {"queue": "billing"},
    "src.tasks.tax_tasks.*": {"queue": "billing"},
    # Очередь placement — задачи размещения (критические)
    "placement.*": {"queue": QUEUE_WORKER_CRITICAL},
    "src.tasks.placement_tasks.*": {"queue": QUEUE_WORKER_CRITICAL},
}

# =============================================================================
# TASK TIME LIMITS
# =============================================================================

TASK_TIME_LIMITS = {
    # Рассылки — длительный лимит
    "src.tasks.mailing_tasks.send_campaign": 600,  # 10 минут
    "src.tasks.mailing_tasks.check_scheduled_campaigns": 300,  # 5 минут
    # Парсер — средний лимит
    TASK_REFRESH_CHAT_DB: 1800,  # 30 минут
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
    TASK_REFRESH_CHAT_DB: {
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
    QUEUE_MAILING: {
        "max_tasks_per_child": 100,
        "prefetch_multiplier": 1,
        "concurrency": 4,
    },
    QUEUE_PARSER: {
        "max_tasks_per_child": 50,
        "prefetch_multiplier": 1,
        "concurrency": 2,
    },
    QUEUE_CLEANUP: {
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
