"""Sentry/GlitchTip initialization for Celery workers."""

import logging

import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

from src.config.settings import settings
from src.utils.pii_keys import SENTRY_PII_KEYS

logger = logging.getLogger(__name__)


def _scrub_pii(event: dict, hint: dict) -> dict:  # noqa: ARG001
    """Remove PII from Sentry events before sending (consistent with API)."""

    def _clean(obj: object) -> object:
        if isinstance(obj, dict):
            return {
                k: "***" if k.lower() in SENTRY_PII_KEYS else _clean(v)
                for k, v in obj.items()
            }
        if isinstance(obj, (list, tuple)):
            return type(obj)(_clean(i) for i in obj)
        return obj

    if "breadcrumbs" in event:
        event["breadcrumbs"] = _clean(event.get("breadcrumbs", {}))
    if "extra" in event:
        event["extra"] = _clean(event.get("extra", {}))

    return event


def init_worker_sentry() -> None:
    """Initialize Sentry for Celery workers. Only if SENTRY_DSN is set."""
    if not settings.sentry_dsn:
        logger.info("Sentry: SENTRY_DSN not set — error tracking disabled for workers")
        return

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.sentry_environment,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        integrations=[
            CeleryIntegration(),
            LoggingIntegration(event_level=logging.ERROR),
        ],
        before_send=_scrub_pii,  # type: ignore[arg-type]
        send_default_pii=False,
        shutdown_timeout=2,
        debug=False,
    )
    logger.info(
        "Sentry initialized for Celery worker (env=%s, traces=%.0f%%)",
        settings.sentry_environment,
        settings.sentry_traces_sample_rate * 100,
    )
