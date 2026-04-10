"""
Celery tasks for monitoring / GlitchTip alert processing.
Queue: worker_critical (high-priority error analysis)
"""

from __future__ import annotations

import asyncio
import json
import logging
import pathlib
from typing import Any

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from src.config.settings import settings
from src.core.services.qwen_service import QwenAnalysisResult, analyze_error
from src.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

SEVERITY_EMOJI: dict[str, str] = {
    "critical": "🔴",
    "high": "🟠",
    "medium": "🟡",
    "low": "🟢",
    "unknown": "⚪",
}

# Cache directory for traceback payloads (used by bot callback handlers)
GT_CACHE = pathlib.Path("/tmp/gt_cache")  # nosec B108


def _extract_traceback(payload: dict) -> str:
    """Extract human-readable traceback from GlitchTip payload."""
    exception = payload.get("issue", {}).get("exception", {})
    if not exception:
        return payload.get("issue", {}).get("culprit", "No traceback available")

    values = exception.get("values", [{}])
    if not values:
        return payload.get("issue", {}).get("culprit", "No traceback available")

    frames = values[0].get("stacktrace", {}).get("frames", [])
    if not frames:
        return payload.get("issue", {}).get("culprit", "No traceback available")

    # Last 10 frames for readability
    lines: list[str] = []
    for frame in frames[-10:]:
        filename = frame.get("filename", "?")
        lineno = frame.get("lineno", "?")
        func = frame.get("function", "?")
        context = frame.get("context_line", "")
        lines.append(f'  File "{filename}", line {lineno}, in {func}\n    {context}')

    return "\n".join(lines) if lines else payload.get("issue", {}).get("culprit", "No traceback")


def _cache_traceback(issue_id: str, title: str, traceback: str) -> pathlib.Path:
    """Persist traceback to disk so bot callback can read it."""
    GT_CACHE.mkdir(exist_ok=True)
    cache_path = GT_CACHE / f"{issue_id}.json"
    cache_path.write_text(json.dumps({"traceback": traceback, "title": title}))
    return cache_path


def _build_keyboard(issue_id: str) -> InlineKeyboardMarkup:
    """Inline keyboard: traceback / ack / ignore."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔍 Трейсбек",
                    callback_data=f"gt:traceback:{issue_id}",
                ),
                InlineKeyboardButton(
                    text="✅ Принято",
                    callback_data=f"gt:ack:{issue_id}",
                ),
                InlineKeyboardButton(
                    text="🚫 Игнор",
                    callback_data=f"gt:ignore:{issue_id}",
                ),
            ]
        ]
    )


def _format_message(
    project: str,
    title: str,
    result: QwenAnalysisResult,
) -> str:
    """Format the Telegram notification message."""
    sev = SEVERITY_EMOJI.get(result.severity, "⚪")
    files_str = "\n".join(f"  • {f}" for f in result.affected_files) or "  неизвестно"

    return (
        f"{sev} <b>GlitchTip Alert</b>\n\n"
        f"<b>Проект:</b> {project}\n"
        f"<b>Ошибка:</b> {title}\n"
        f"<b>Severity:</b> {result.severity}\n\n"
        f"<b>Причина:</b>\n{result.root_cause}\n\n"
        f"<b>Файлы:</b>\n{files_str}\n\n"
        f"<b>Фикс:</b>\n{result.suggested_fix}"
    )


async def _analyze_and_notify(payload: dict) -> None:
    """Analyze error via Qwen and notify admin via Telegram."""
    issue = payload.get("issue", {})
    issue_id = str(issue.get("id", "unknown"))
    title = issue.get("title", "Unknown error")
    culprit = issue.get("culprit", "")
    project = payload.get("project", {}).get("name", "rekharbor")

    traceback_text = _extract_traceback(payload)

    # Run Qwen analysis
    result = await analyze_error(
        title=title,
        culprit=culprit,
        traceback=traceback_text,
        project=project,
    )

    # Cache traceback for callback
    _cache_traceback(issue_id, title, traceback_text)

    text = _format_message(project, title, result)
    keyboard = _build_keyboard(issue_id)

    # Create a temporary Bot instance (API process has no shared bot)
    bot = Bot(token=settings.bot_token)
    try:
        await bot.send_message(
            chat_id=settings.admin_telegram_id,
            text=text,
            parse_mode="HTML",
            reply_markup=keyboard,
        )
        logger.info("GlitchTip alert sent to admin for issue %s", issue_id)
    except Exception:  # noqa: BLE001 — log and move on, don't retry notification
        logger.exception("Failed to send GlitchTip alert to admin for issue %s", issue_id)
    finally:
        await bot.session.close()


@celery_app.task(
    name="monitoring:analyze_glitchtip_error",
    queue="worker_critical",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
)
def analyze_glitchtip_error(self: Any, payload: dict) -> None:
    """Celery task: analyze GlitchTip error via Qwen and notify admin."""
    asyncio.run(_analyze_and_notify(payload))
