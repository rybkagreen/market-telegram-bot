"""
Celery приложение для асинхронных задач.
Настройка broker, backend, очередей и маршрутизации.
"""

import logging
from typing import Any

from celery import Celery, Task
from celery.schedules import crontab

from src.config.settings import settings

logger = logging.getLogger(__name__)


def create_celery_app() -> Celery:
    """
    Создать и настроить Celery приложение.

    Returns:
        Настроенное Celery приложение.
    """
    # Создаем приложение
    app = Celery(
        "market_bot",
        broker=settings.celery_broker_url,
        backend=settings.celery_result_backend,
        include=[
            "src.tasks.parser_tasks",
            "src.tasks.mailing_tasks",
            "src.tasks.cleanup_tasks",
            "src.tasks.notification_tasks",
            "src.tasks.billing_tasks",
            "src.tasks.placement_tasks",
        ],
    )

    # Конфигурация
    app.conf.update(
        # Сериализация
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        # Очереди
        task_routes={
            "mailing.*": {"queue": "mailing"},
            "parser.*": {"queue": "parser"},
            "cleanup.*": {"queue": "cleanup"},
            "publication.*": {"queue": "critical"},
        },
        # Приоритеты задач (Redis broker)
        broker_transport_options={
            "visibility_timeout": 604800,  # 7 дней
            "priority_steps": list(range(10)),  # 0-9
        },
        task_default_priority=5,  # Средний приоритет по умолчанию
        task_queue_max_priority=10,
        # Надёжность
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        task_track_started=True,
        # Таймауты
        task_soft_time_limit=300,  # 5 минут мягкий лимит
        task_time_limit=600,  # 10 минут жесткий лимит
        # Retry
        task_default_retry_delay=60,  # 1 минута между попытками
        task_max_retries=3,
        # Worker
        worker_prefetch_multiplier=1,  # Не брать задачи вперед
        worker_max_tasks_per_child=1000,  # Перезапуск worker после 1000 задач
        # Результат
        result_expires=3600,  # Истечение результата через 1 час
        result_persistent=True,
        # Логирование
        worker_hijack_root_logger=False,
        worker_log_level="INFO",
    )

    # Настройка Beat расписания
    app.conf.beat_schedule = get_beat_schedule()

    # Автообнаружение задач
    app.autodiscover_tasks(
        packages=[
            "src.tasks",
        ],
        force=True,
    )

    # Регистрация периодических задач для publication
    app.conf.beat_schedule["check-scheduled-deletions"] = {
        "task": "publication:check_scheduled_deletions",
        "schedule": crontab(minute="*/5"),
        "options": {"queue": "default"},
    }

    return app


def get_beat_schedule() -> dict[str, Any]:
    """
    Получить расписание периодических задач Celery Beat.

    Парсинг настроен на ночное время (02:30-06:00 UTC = 05:30-09:00 MSK).
    Разбит на 7 слотов по 30 минут для соблюдения лимитов Telegram.

    Telegram лимиты (User API):
    - Поиск каналов: ~10-20 запросов в минуту
    - Получение информации о канале: ~50-100 запросов в минуту
    - FloodWait: автоматически обрабатывается в парсере

    Каждый слот обрабатывает ~20-25 поисковых запросов.
    Общее время: 3.5 часа для ~150 запросов.

    Returns:
        Словарь с расписанием задач.
    """
    return {
        # ========== ПАРСИНГ (00:15-03:30 UTC = 03:15-06:30 MSK) ==========
        # Слот 1: 03:15 MSK (00:15 UTC) - Бизнес и финансы
        "parser-slot-1-business": {
            "task": "parser:refresh_chat_database_business",
            "schedule": crontab(hour=0, minute=15),
            "options": {"queue": "parser"},
            "kwargs": {"query_category": "business"},
        },
        # Слот 2: 03:45 MSK (00:45 UTC) - Маркетинг и продажи
        "parser-slot-2-marketing": {
            "task": "parser:refresh_chat_database_marketing",
            "schedule": crontab(hour=0, minute=45),
            "options": {"queue": "parser"},
            "kwargs": {"query_category": "marketing"},
        },
        # Слот 3: 04:15 MSK (01:15 UTC) - IT и технологии
        "parser-slot-3-it": {
            "task": "parser:refresh_chat_database_it",
            "schedule": crontab(hour=1, minute=15),
            "options": {"queue": "parser"},
            "kwargs": {"query_category": "it"},
        },
        # Слот 4: 04:45 MSK (01:45 UTC) - Недвижимость, Авто, Путешествия
        "parser-slot-4-lifestyle": {
            "task": "parser:refresh_chat_database_lifestyle",
            "schedule": crontab(hour=1, minute=45),
            "options": {"queue": "parser"},
            "kwargs": {"query_category": "lifestyle"},
        },
        # Слот 5: 05:15 MSK (02:15 UTC) - Еда, Мода, Здоровье
        "parser-slot-5-health": {
            "task": "parser:refresh_chat_database_health",
            "schedule": crontab(hour=2, minute=15),
            "options": {"queue": "parser"},
            "kwargs": {"query_category": "health"},
        },
        # Слот 6: 05:45 MSK (02:45 UTC) - Образование, Дом, Развлечения
        "parser-slot-6-education": {
            "task": "parser:refresh_chat_database_education",
            "schedule": crontab(hour=2, minute=45),
            "options": {"queue": "parser"},
            "kwargs": {"query_category": "education"},
        },
        # Слот 7: 06:15 MSK (03:15 UTC) - Новости, Работа, Психология
        "parser-slot-7-news": {
            "task": "parser:refresh_chat_database_news",
            "schedule": crontab(hour=3, minute=15),
            "options": {"queue": "parser"},
            "kwargs": {"query_category": "news"},
        },
        # ========== АНАЛИТИКА (06:30 MSK = 03:30 UTC) ==========
        # Сбор аналитики после завершения парсинга
        "collect-all-chats-stats-daily": {
            "task": "parser:collect_all_chats_stats",
            "schedule": crontab(hour=3, minute=30),
            "options": {"queue": "parser"},
        },
        # ========== MAILING (каждые 5 минут) ==========
        "check-scheduled-campaigns": {
            "task": "mailing:check_scheduled_campaigns",
            "schedule": crontab(minute="*/5"),
            "options": {"queue": "mailing"},
        },
        # ========== CLEANUP (воскресенье 03:00 UTC) ==========
        "delete-old-logs": {
            "task": "cleanup:delete_old_logs",
            "schedule": crontab(hour=3, minute=0, day_of_week=0),
            "options": {"queue": "cleanup"},
        },
        # ========== BILLING (каждый час) ==========
        "check-low-balance": {
            "task": "mailing:check_low_balance",
            "schedule": crontab(minute=0),
            "options": {"queue": "mailing"},
        },
        # ========== PLAN RENEWALS (ежедневно в 03:00 UTC) ==========
        "check-plan-renewals": {
            "task": "billing:check_plan_renewals",
            "schedule": crontab(hour=settings.plan_renewal_check_hour, minute=0),
            "options": {"queue": "billing", "priority": 9},
        },
        # ========== CHECK PENDING INVOICES (каждые 5 минут) ==========
        "check-pending-invoices": {
            "task": "billing:check_pending_invoices",
            "schedule": 300.0,  # 5 минут
            "options": {"queue": "billing", "priority": 9},
        },
    }


# Создаем глобальное приложение
celery_app = create_celery_app()

# Алиас для совместимости
app = celery_app


# Decorator для регистрации задач
def register_task(name: str | None = None, **kwargs: Any) -> Any:
    """
    Декоратор для регистрации Celery задач.

    Usage:
        @register_task("mailing:send_campaign")
        def send_campaign(campaign_id: int):
            ...
    """

    def decorator(func: Task) -> Task:
        task_name = name or func.__name__
        return celery_app.task(name=task_name, **kwargs)(func)

    return decorator


# Base Task class с логированием
class BaseTask(Task):
    """Базовый класс для задач с логированием."""

    abstract = True

    def on_failure(
        self,
        exc: Exception,
        task_id: str,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        einfo: Any,
    ) -> None:
        """Логирование ошибки задачи."""
        logger.error(
            f"Task {self.name} failed: {exc}",
            extra={
                "task_id": task_id,
                "task_args": args,  # Renamed to avoid conflict with logging internals
                "task_kwargs": kwargs,
                "traceback": einfo.traceback,
            },
        )

    def on_success(
        self, retval: Any, task_id: str, args: tuple[Any, ...], kwargs: dict[str, Any]
    ) -> None:
        """Логирование успеха задачи."""
        logger.info(f"Task {self.name} completed successfully", extra={"task_id": task_id})

    def on_retry(
        self,
        exc: Exception,
        task_id: str,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        einfo: Any,
    ) -> None:
        """Логирование повторной попытки."""
        logger.warning(
            f"Task {self.name} retrying: {exc}",
            extra={
                "task_id": task_id,
                "task_args": args,
                "task_kwargs": kwargs,
            },
        )
