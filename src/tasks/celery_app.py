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
        },
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
    app.autodiscover_tasks(packages=["src.tasks"], force=True)

    return app


def get_beat_schedule() -> dict[str, Any]:
    """
    Получить расписание периодических задач Celery Beat.

    Returns:
        Словарь с расписанием задач.
    """
    return {
        # Обновление базы чатов — каждые 24 часа в 3:00 UTC
        "refresh-chat-database": {
            "task": "parser:refresh_chat_database",
            "schedule": crontab(hour=3, minute=0),
            "options": {"queue": "parser"},
        },
        # Ежедневный сбор аналитики в 02:00 UTC
        "collect-all-chats-stats-daily": {
            "task": "parser:collect_all_chats_stats",
            "schedule": crontab(hour=2, minute=0),
            "options": {"queue": "parser"},
        },
        # Проверка запланированных кампаний — каждые 5 минут
        "check-scheduled-campaigns": {
            "task": "mailing:check_scheduled_campaigns",
            "schedule": crontab(minute="*/5"),
            "options": {"queue": "mailing"},
        },
        # Удаление старых логов — каждое воскресенье в 3:00 UTC
        "delete-old-logs": {
            "task": "cleanup:delete_old_logs",
            "schedule": crontab(hour=3, minute=0, day_of_week=0),
            "options": {"queue": "cleanup"},
        },
        # Проверка низкого баланса — каждый час
        "check-low-balance": {
            "task": "mailing:check_low_balance",
            "schedule": crontab(minute=0),
            "options": {"queue": "mailing"},
        },
    }


# Создаем глобальное приложение
celery_app = create_celery_app()


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
                "args": args,
                "kwargs": kwargs,
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
                "args": args,
                "kwargs": kwargs,
            },
        )
