"""
Admin monitoring handlers — callback buttons for GlitchTip alerts.
Callbacks: gt:traceback:{id}, gt:ack:{id}, gt:ignore:{id}
"""

from __future__ import annotations

import json
import logging
import pathlib

from aiogram import Router
from aiogram.types import CallbackQuery, Message

logger = logging.getLogger(__name__)

router = Router(name="admin_monitoring")

GT_CACHE = pathlib.Path("/tmp/gt_cache")  # nosec B108


def _get_callback_data(callback: CallbackQuery) -> str | None:
    """Safely extract callback data."""
    if callback.data:
        return callback.data
    return None


@router.callback_query(lambda c: c.data and c.data.startswith("gt:traceback:"))
async def show_traceback(callback: CallbackQuery) -> None:
    """Show full traceback for a GlitchTip alert."""
    if callback.message is None:
        await callback.answer("Сообщение недоступно", show_alert=True)
        return

    data = _get_callback_data(callback)
    if data is None:
        await callback.answer("Нет данных", show_alert=True)
        return

    issue_id = data.split(":")[2]
    cache_path = GT_CACHE / f"{issue_id}.json"

    if cache_path.exists():
        try:
            cache_data = json.loads(cache_path.read_text())
            tb = cache_data.get("traceback", "Трейсбек не найден")[:3500]
            await callback.message.answer(
                f"<pre>{tb}</pre>",
                parse_mode="HTML",
            )
        except Exception:  # noqa: BLE001
            logger.exception("Failed to read traceback cache for %s", issue_id)
            await callback.answer("Ошибка чтения кэша", show_alert=True)
            return
    else:
        await callback.answer("Трейсбек недоступен", show_alert=True)
        return

    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("gt:ack:"))
async def ack_issue(callback: CallbackQuery) -> None:
    """Acknowledge a GlitchTip alert — remove buttons, confirm."""
    if not isinstance(callback.message, Message):
        await callback.answer("Сообщение недоступно", show_alert=True)
        return

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("✅ Принято к сведению")
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("gt:ignore:"))
async def ignore_issue(callback: CallbackQuery) -> None:
    """Ignore a GlitchTip alert — remove buttons."""
    if callback.message is None:
        await callback.answer("Сообщение недоступно", show_alert=True)
        return

    if not isinstance(callback.message, Message):
        await callback.answer("Сообщение недоступно", show_alert=True)
        return

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer("🚫 Проигнорировано", show_alert=False)
