"""
FastAPI router для webhook-уведомлений GlitchTip.
S10: сохраняет alert в /tmp/glitchtip_queue/ → host-side скрипт (qwen) анализирует → Telegram.

Архитектура:
  GlitchTip → POST /webhooks/glitchtip-alert → FastAPI сохраняет JSON в /tmp/glitchtip_queue/
  → systemd timer / inotify на хосте → bash scripts/monitoring/analyze_error.sh <payload.json>
  → qwen --channel CI анализирует файлы проекта → отчёт → Telegram notification
"""

from __future__ import annotations

import json
import logging
import pathlib
import secrets
import uuid
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Request

from src.config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

QUEUE_DIR = pathlib.Path("/tmp/glitchtip_queue")


@router.post("/glitchtip-alert")
async def glitchtip_alert(
    request: Request,
    x_webhook_token: Annotated[str | None, Header(alias="X-Webhook-Token")] = None,
) -> dict[str, str]:
    """
    Принять alert от GlitchTip, сохранить в файловую очередь.

    Host-side скрипт (scripts/monitoring/analyze_error.sh) подхватит payload,
    запустит qwen --channel CI для анализа, и отправит отчёт админу в Telegram.

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

    # Save to file queue for host-side processing
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    issue_id = payload.get("issue", {}).get("id", "unknown")
    payload_file = QUEUE_DIR / f"{uuid.uuid4().hex}_{issue_id}.json"
    payload_file.write_text(json.dumps(payload, ensure_ascii=False))

    logger.info("GlitchTip alert saved to queue: %s", payload_file.name)
    return {"status": "queued", "file": payload_file.name}
