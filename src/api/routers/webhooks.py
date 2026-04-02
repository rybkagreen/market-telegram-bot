"""
FastAPI router для webhook-уведомлений GlitchTip.
S10: получает alert, сохраняет payload в очередь на хосте, сразу возвращает 200.
analyze_error.sh запускается хостовым cron-демоном из /opt/market-telegram-bot/reports/monitoring/payloads/
"""

from __future__ import annotations

import json
import logging
import secrets
import tempfile
from pathlib import Path

from fastapi import APIRouter, Header, HTTPException, Request

from src.config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

# Директория очереди — примонтирована из хоста через docker-compose volume
QUEUE_DIR = Path("/tmp/glitchtip_queue")


@router.post("/glitchtip-alert")
async def glitchtip_alert(
    request: Request,
    x_webhook_token: str | None = Header(default=None, alias="X-Webhook-Token"),
) -> dict[str, bool]:
    """
    Принять alert от GlitchTip, сохранить payload в очередь.

    analyze_error.sh запускается хостовым cron каждую минуту.
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

    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = tempfile.NamedTemporaryFile(  # noqa: SIM115
        mode="w",
        suffix=".json",
        delete=False,
        dir=str(QUEUE_DIR),
        prefix="glitchtip_",
    )
    json.dump(payload, tmp)
    tmp.close()

    logger.info("GlitchTip alert queued: %s", tmp.name)
    return {"ok": True}
