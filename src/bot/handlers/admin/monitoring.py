"""
Admin monitoring handlers — callback buttons for GlitchTip alerts.
Callbacks: gt:apply:{id}, gt:ignore:{id}
"""

import asyncio
import logging
import pathlib

from aiogram import Bot, Router
from aiogram.types import CallbackQuery

logger = logging.getLogger(__name__)

router = Router(name="admin_monitoring")

REPORTS_DIR = pathlib.Path("/opt/market-telegram-bot/reports/monitoring/error_reports")
APPLY_SCRIPT = "/opt/market-telegram-bot/scripts/monitoring/apply_fix.sh"


@router.callback_query(lambda c: c.data and c.data.startswith("gt:apply:"))
async def handle_apply(callback: CallbackQuery):
    """Admin clicked 'Apply fix' — run apply_fix.sh via qwen."""
    assert callback.data is not None  # guaranteed by callback router lambda
    issue_id = callback.data.split(":")[2]
    await callback.answer("⏳ Применяю исправление...", show_alert=False)

    # Find latest report for this issue
    report = _find_report(issue_id)
    if not report:
        if callback.message and hasattr(callback.message, "edit_text"):
            await callback.message.edit_text(
                f"❌ Отчёт для issue `{issue_id}` не найден.",
                parse_mode="Markdown",
            )
        return

    # Remove keyboard
    if callback.message and hasattr(callback.message, "edit_reply_markup"):
        await callback.message.edit_reply_markup(reply_markup=None)

    # Get bot instance from callback
    bot_instance: Bot = callback.bot

    # Send "working" message
    msg = callback.message
    if msg is None or not hasattr(msg, "chat"):
        return
    status_msg = await bot_instance.send_message(
        chat_id=msg.chat.id,
        text=f"⏳ Запускаю исправление для `{issue_id}`...\nЭто может занять до 4 минут.",
        parse_mode="Markdown",
    )

    # Run apply_fix.sh

    proc = await asyncio.create_subprocess_exec(
        "bash",
        APPLY_SCRIPT,
        str(report),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)

    if proc.returncode == 0:
        output = stdout.decode().strip()
        await status_msg.edit_text(
            f"✅ Исправление применено для `{issue_id}`\n\n```\n{output[-2000:]}\n```",
            parse_mode="Markdown",
        )
        logger.info("Fix applied for issue %s", issue_id)
    else:
        error = stderr.decode().strip()[:500]
        await status_msg.edit_text(
            f"❌ Ошибка при применении исправления `{issue_id}`\n\n```\n{error}\n```",
            parse_mode="Markdown",
        )
        logger.error("Fix apply failed for %s: %s", issue_id, error)


@router.callback_query(lambda c: c.data and c.data.startswith("gt:ignore:"))
async def handle_ignore(callback: CallbackQuery):
    """Admin clicked 'Ignore' — dismiss the alert."""
    assert callback.data is not None  # guaranteed by callback router lambda
    issue_id = callback.data.split(":")[2]
    await callback.answer("Отклонено", show_alert=False)

    msg = callback.message
    if msg and hasattr(msg, "edit_text"):
        await msg.edit_text(
            f"🚫 Алерт `{issue_id}` отклонён администратором.",
            parse_mode="Markdown",
            reply_markup=None,
        )
    logger.info("Alert ignored for issue %s", issue_id)


def _find_report(issue_id: str) -> pathlib.Path | None:
    """Find the latest report file for a given issue ID."""
    if not REPORTS_DIR.exists():
        return None
    matches = sorted(REPORTS_DIR.glob(f"error_*_{issue_id}.md"), reverse=True)
    return matches[0] if matches else None
