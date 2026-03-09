"""
Handlers для мониторинга сервера (диск, память, CPU) и Celery задач.
"""

import logging

import psutil
from aiogram import F, Router
from aiogram.types import CallbackQuery

from src.bot.filters.admin import AdminFilter
from src.bot.keyboards.admin import AdminCB
from src.bot.utils.safe_callback import safe_callback_edit
from src.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

router = Router()
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())


def get_server_metrics() -> dict:
    """
    Получить метрики сервера через psutil.
    
    Returns:
        dict с disk, memory, cpu метриками.
    """
    metrics = {
        "disk": {"total": 0, "used": 0, "free": 0, "percent": 0},
        "memory": {"total": 0, "used": 0, "free": 0, "percent": 0},
        "cpu": {"percent": 0},
        "uptime": "",
    }
    
    try:
        # Disk usage
        disk = psutil.disk_usage("/")
        metrics["disk"]["total"] = f"{disk.total / (1024**3):.1f}G"
        metrics["disk"]["used"] = f"{disk.used / (1024**3):.1f}G"
        metrics["disk"]["free"] = f"{disk.free / (1024**3):.1f}G"
        metrics["disk"]["percent"] = disk.percent
        
        # Memory usage
        memory = psutil.virtual_memory()
        metrics["memory"]["total"] = f"{memory.total / (1024**3):.1f}G"
        metrics["memory"]["used"] = f"{memory.used / (1024**3):.1f}G"
        metrics["memory"]["free"] = f"{memory.free / (1024**3):.1f}G"
        metrics["memory"]["percent"] = memory.percent
        
        # CPU usage
        metrics["cpu"]["percent"] = psutil.cpu_percent(interval=1)
        
        # Uptime
        boot_time = psutil.boot_time()
        import datetime
        uptime_seconds = datetime.datetime.now().timestamp() - boot_time
        uptime_days = int(uptime_seconds // 86400)
        uptime_hours = int((uptime_seconds % 86400) // 3600)
        uptime_minutes = int((uptime_seconds % 3600) // 60)
        
        if uptime_days > 0:
            metrics["uptime"] = f"{uptime_days}d {uptime_hours}h {uptime_minutes}m"
        elif uptime_hours > 0:
            metrics["uptime"] = f"{uptime_hours}h {uptime_minutes}m"
        else:
            metrics["uptime"] = f"{uptime_minutes}m"
        
    except Exception as e:
        logger.error(f"Error getting server metrics: {e}")
    
    return metrics


def get_celery_stats() -> dict:
    """
    Получить статистику Celery задач через inspect API.
    
    Returns:
        dict с active, scheduled, reserved задачами.
    """
    stats = {
        "active": 0,
        "scheduled": 0,
        "reserved": 0,
        "workers": [],
        "errors": [],
    }
    
    try:
        inspect = celery_app.control.inspect(timeout=5)
        
        # Active tasks
        active = inspect.active()
        if active:
            for worker, tasks in active.items():
                stats["workers"].append(worker)
                stats["active"] += len(tasks)
        
        # Scheduled tasks
        scheduled = inspect.scheduled()
        if scheduled:
            for tasks in scheduled.values():
                stats["scheduled"] += len(tasks)
        
        # Reserved tasks
        reserved = inspect.reserved()
        if reserved:
            for tasks in reserved.values():
                stats["reserved"] += len(tasks)
        
        # Registered tasks
        registered = inspect.registered()
        if registered:
            stats["registered_count"] = sum(len(tasks) for tasks in registered.values())
        
    except Exception as e:
        logger.error(f"Error getting Celery stats: {e}")
        stats["errors"].append(str(e))
    
    return stats


@router.callback_query(AdminCB.filter(F.action == "server_monitoring"))
async def show_server_monitoring(callback: CallbackQuery) -> None:
    """
    Показать мониторинг сервера.
    """
    try:
        metrics = get_server_metrics()
        
        text = (
            "🖥 <b>Мониторинг сервера</b>\n\n"
            f"⏱ <b>Uptime:</b> {metrics['uptime'] or 'N/A'}\n\n"
            f"💾 <b>Disk (/):</b>\n"
            f"  Total: {metrics['disk']['total']}\n"
            f"  Used: {metrics['disk']['used']} ({metrics['disk']['percent']}%)\n"
            f"  Free: {metrics['disk']['free']}\n\n"
            f"🧠 <b>Memory:</b>\n"
            f"  Total: {metrics['memory']['total']}\n"
            f"  Used: {metrics['memory']['used']}\n"
            f"  Free: {metrics['memory']['free']}\n\n"
            f"⚙️ <b>CPU:</b> {metrics['cpu']['percent']}% usage\n"
        )
        
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        
        builder = InlineKeyboardBuilder()
        builder.button(text="🔄 Обновить", callback_data=AdminCB(action="server_monitoring"))
        builder.button(text="🔙 Назад", callback_data=AdminCB(action="main"))
        builder.adjust(2)
        
        await safe_callback_edit(callback, text, reply_markup=builder.as_markup())
        
    except Exception as e:
        logger.error(f"Server monitoring error: {e}")
        await callback.answer("Ошибка получения данных", show_alert=True)


@router.callback_query(AdminCB.filter(F.action == "celery_tasks"))
async def show_celery_tasks(callback: CallbackQuery) -> None:
    """
    Показать задачи Celery.
    """
    try:
        stats = get_celery_stats()
        
        text = (
            "📋 <b>Задачи Celery</b>\n\n"
            f"👷 <b>Workers:</b> {len(stats['workers'])}\n"
        )
        
        if stats["workers"]:
            for worker in stats["workers"][:5]:
                text += f"  • {worker}\n"
        
        text += (
            f"\n🔥 <b>Active:</b> {stats['active']}\n"
            f"⏰ <b>Scheduled:</b> {stats['scheduled']}\n"
            f"📦 <b>Reserved:</b> {stats['reserved']}\n"
            f"📝 <b>Registered:</b> {stats.get('registered_count', 0)} tasks\n\n"
        )
        
        if stats["errors"]:
            text += f"❌ <b>Errors:</b>\n"
            for error in stats["errors"]:
                text += f"  • {error}\n"
        
        text += (
            "\n<b>Планировщик (Celery Beat):</b>\n"
            "• refresh-chat-database — каждые 24ч\n"
            "• check-scheduled-campaigns — каждые 5мин\n"
            "• delete-old-logs — каждое воскресенье\n"
            "• check-low-balance — каждый час\n"
            "• update-chat-statistics — каждые 6ч\n"
            "• archive-old-campaigns — 1-го числа месяца\n"
            "• check-plan-renewals — ежедневно в 03:00\n"
            "• check-pending-invoices — каждые 5мин\n"
            "• daily-badge-check — ежедневно в 00:00\n"
            "• monthly-top-advertisers — 1-го числа месяца\n"
            "• notify-expiring-plans — ежедневно в 10:00\n"
            "• notify-expired-plans — ежедневно в 10:05\n"
            "• auto-approve-placements — каждый час\n"
            "• placement-reminders — каждые 2 часа\n"
        )
        
        from src.bot.keyboards.admin import get_celery_tasks_kb
        
        keyboard = get_celery_tasks_kb()
        
        await safe_callback_edit(callback, text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Celery tasks error: {e}")
        await callback.answer("Ошибка получения данных", show_alert=True)


@router.callback_query(AdminCB.filter(F.action == "celery_worker_stats"))
async def show_celery_worker_stats(callback: CallbackQuery) -> None:
    """
    Показать детальную статистику по workers.
    """
    try:
        inspect = celery_app.control.inspect(timeout=5)
        
        # Stats per worker
        worker_stats = inspect.stats()
        
        text = "👷 <b>Celery Workers</b>\n\n"
        
        if worker_stats:
            for worker, stats in worker_stats.items():
                text += f"<b>{worker}</b>\n"
                
                # Broker
                broker = stats.get("broker", {})
                text += f"  Broker: {broker.get('hostname', 'N/A')}\n"
                
                # Pool
                pool = stats.get("pool", {})
                text += f"  Pool: {pool.get('max-concurrency', 'N/A')} concurrency\n"
                
                # Uptime
                uptime = stats.get("uptime", {})
                text += f"  Uptime: {uptime.get('humanized', 'N/A')}\n\n"
        else:
            text += "❌ No workers available\n"
        
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        
        builder = InlineKeyboardBuilder()
        builder.button(text="🔙 Назад", callback_data=AdminCB(action="celery_tasks"))
        builder.adjust(1)
        
        await safe_callback_edit(callback, text, reply_markup=builder.as_markup())
        
    except Exception as e:
        logger.error(f"Celery worker stats error: {e}")
        await callback.answer("Ошибка получения данных", show_alert=True)
