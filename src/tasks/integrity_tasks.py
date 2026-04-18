"""
Celery задача проверки целостности данных.
S9: периодически проверяет инварианты БД и оповещает администратора о нарушениях.
"""

import asyncio
import logging
from typing import Any

from src.tasks.celery_app import BaseTask, celery_app

logger = logging.getLogger(__name__)

# SQL checks: (name, query, alert_message_template)
INTEGRITY_CHECKS: list[tuple[str, str, str]] = [
    (
        "signed_contracts_have_signatures",
        """
        SELECT COUNT(*) FROM contracts c
        LEFT JOIN contract_signatures s ON s.contract_id = c.id
        WHERE c.contract_status = 'signed' AND s.id IS NULL
        """,
        "⚠️ {count} подписанных договоров без записи в contract_signatures",
    ),
    (
        "transaction_balance_sanity",
        "SELECT COUNT(*) FROM users WHERE balance < 0",
        "🚨 {count} пользователей с отрицательным балансом",
    ),
    (
        "escrow_without_placement",
        """
        SELECT COUNT(*) FROM transactions t
        WHERE t.type = 'escrow'
          AND NOT EXISTS (
            SELECT 1 FROM placement_requests p
            WHERE p.id = t.placement_request_id
              AND p.status = 'escrow'
          )
        """,
        "⚠️ {count} эскроу-транзакций без соответствующей кампании в статусе escrow",
    ),
    (
        "completed_placements_have_publication_log",
        """
        SELECT COUNT(*) FROM placement_requests p
        WHERE p.status = 'completed'
          AND NOT EXISTS (
            SELECT 1 FROM publication_logs l
            WHERE l.placement_id = p.id
              AND l.event_type = 'published'
          )
        """,
        "⚠️ {count} завершённых кампаний без записи о публикации в publication_logs",
    ),
]


@celery_app.task(base=BaseTask, name="integrity:check_data_integrity", queue="cleanup")
def check_data_integrity() -> dict[str, Any]:
    """
    Проверить целостность данных.

    Запускается каждые 6 часов через Celery Beat.
    При нарушениях отправляет сообщение администратору.

    Returns:
        Результаты проверок.
    """
    logger.info("Starting data integrity check")

    try:
        result = asyncio.run(_check_data_integrity_async())
        logger.info(f"Data integrity check completed: {result}")
        return result
    except Exception as e:
        logger.error(f"Error in data integrity check: {e}")
        return {"error": str(e)}


async def _check_data_integrity_async() -> dict[str, Any]:
    """Асинхронная реализация проверки целостности данных."""
    from src.db.session import celery_async_session_factory as async_session_factory

    results: dict[str, Any] = {"checks": {}, "failures": [], "ok": True}

    async with async_session_factory() as session:
        from sqlalchemy import text

        for check_name, query, message_template in INTEGRITY_CHECKS:
            try:
                row = await session.execute(text(query.strip()))
                count: int = row.scalar() or 0
                results["checks"][check_name] = count

                if count > 0:
                    msg = message_template.format(count=count)
                    results["failures"].append(msg)
                    logger.warning(f"Integrity check FAILED: {check_name} — {msg}")
            except Exception as e:
                error_msg = f"❌ Ошибка при проверке {check_name}: {e}"
                results["failures"].append(error_msg)
                logger.error(f"Integrity check ERROR: {check_name} — {e}")

    if results["failures"]:
        results["ok"] = False
        await _notify_admin_failures(results["failures"])

    return results


async def _notify_admin_failures(failures: list[str]) -> None:
    """Отправить администратору сообщение о нарушениях целостности."""
    from src.config.settings import settings
    from src.tasks._bot_factory import get_bot

    admin_ids = settings.admin_ids
    if not admin_ids:
        logger.warning("ADMIN_IDS not set — cannot send integrity alert")
        return

    text = "🔍 <b>Проверка целостности данных — обнаружены нарушения:</b>\n\n"
    text += "\n".join(f"• {f}" for f in failures)

    bot = get_bot()
    for admin_id in admin_ids:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=text,
                parse_mode="HTML",
            )
        except Exception as e:
            logger.error(f"Failed to send integrity alert to admin {admin_id}: {e}")
    logger.info(f"Integrity alert sent to {len(admin_ids)} admin(s)")
