"""
FastAPI router для webhook-уведомлений GlitchTip.
S10: принимает alert, ставит Celery-задачу анализа, возвращает 200 немедленно.
Celery-задача: Qwen-анализ → уведомление админу в Telegram.
"""

from __future__ import annotations

import logging
import secrets
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Request

from src.config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/glitchtip-alert")
async def glitchtip_alert(
    request: Request,
    x_webhook_token: Annotated[str | None, Header(alias="X-Webhook-Token")] = None,
) -> dict[str, str]:
    """
    Принять alert от GlitchTip, отправить на анализ через Celery.

    Celery-задача: analyze_glitchtip_error.delay(payload)
    → Qwen анализ ошибки → отправка уведомления админу в Telegram
    → inline-кнопки: трейсбек / принять / игнорировать

    Возвращает 200 немедленно.
    """
    if not settings.glitchtip_webhook_secret:
        raise HTTPException(status_code=503, detail="Webhook not configured")

    if not x_webhook_token or not secrets.compare_digest(
        x_webhook_token, settings.glitchtip_webhook_secret
    ):
        raise HTTPException(status_code=403, detail="Invalid token")

    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON") from exc

    # Enqueue Celery task for analysis and notification
    from src.tasks.monitoring_tasks import analyze_glitchtip_error

    analyze_glitchtip_error.delay(payload)
    logger.info("GlitchTip alert enqueued for analysis")
    return {"status": "queued"}
