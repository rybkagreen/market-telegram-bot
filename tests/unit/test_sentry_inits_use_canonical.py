"""Both Sentry initializations consume canonical PII keys list.

Если этот test падает — кто-то re-introduced локальный literal в одном
из двух init модулей, restoring drift surface. Fix = restore import from
src.utils.pii_keys.

Behavioral check: pass a payload with every canonical key into each
``_scrub_pii`` and confirm all keys get masked. Any divergence (a key
in canonical but missing from a module's scrub set) breaks the test.
"""
from __future__ import annotations

from src.api.main import _scrub_pii as fastapi_scrub
from src.tasks.sentry_init import _scrub_pii as celery_scrub
from src.utils.pii_keys import SENTRY_PII_KEYS


def _payload_with_all_canonical_keys() -> dict[str, str]:
    return dict.fromkeys(SENTRY_PII_KEYS, "secret")


def test_fastapi_scrub_masks_all_canonical_keys() -> None:
    """FastAPI _scrub_pii cleans event['request']; every canonical key → ***."""
    event = {"request": _payload_with_all_canonical_keys()}
    result = fastapi_scrub(event, {})
    for key in SENTRY_PII_KEYS:
        assert result["request"][key] == "***", f"FastAPI did not scrub {key}"


def test_celery_scrub_masks_all_canonical_keys_in_extra() -> None:
    event = {"extra": _payload_with_all_canonical_keys()}
    result = celery_scrub(event, {})
    for key in SENTRY_PII_KEYS:
        assert result["extra"][key] == "***", f"Celery extra did not scrub {key}"


def test_celery_scrub_masks_all_canonical_keys_in_breadcrumbs() -> None:
    event = {"breadcrumbs": _payload_with_all_canonical_keys()}
    result = celery_scrub(event, {})
    for key in SENTRY_PII_KEYS:
        assert result["breadcrumbs"][key] == "***", (
            f"Celery breadcrumbs did not scrub {key}"
        )
