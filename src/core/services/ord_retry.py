"""Exponential backoff + jitter helper для ORD Celery retries (BL-080 8c, Q3=(b)).

Replaces the previous linear 5-min retry pattern that risked thundering herds
during Yandex outages. The helper computes a per-attempt delay; callers feed
it to `self.retry(countdown=...)` in Celery task handlers.

Tenacity не installed (pyproject.toml audit 2026-05-12); hand-rolled rather
than adding a dependency for a 20-line helper.
"""

from __future__ import annotations

import random


def compute_backoff(
    retry_count: int,
    *,
    base_seconds: float = 5.0,
    max_seconds: float = 300.0,
    jitter_ratio: float = 0.3,
) -> int:
    """Return the next retry countdown in whole seconds.

    Formula: ``delay = min(base * 2 ** retry_count, max)`` plus random
    ``[0, jitter_ratio * delay]`` to spread thundering herds. Returns
    a non-negative int suitable for Celery `countdown=`.

    Args:
        retry_count: zero-based retry index (``self.request.retries`` in Celery).
        base_seconds: first attempt's base delay (default 5s).
        max_seconds: hard ceiling, even after exponential growth (default 5 min).
        jitter_ratio: max additional fraction of delay (default 30%).
    """
    if retry_count < 0:
        retry_count = 0
    delay = min(base_seconds * (2**retry_count), max_seconds)
    jitter = random.uniform(0.0, jitter_ratio) * delay
    return max(1, int(delay + jitter))
