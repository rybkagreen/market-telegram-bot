"""Unit tests for BL-080 8c retry helper (src/core/services/ord_retry.py)."""

from __future__ import annotations

import random

from src.core.services.ord_retry import compute_backoff


def test_first_attempt_uses_base_delay() -> None:
    """retry_count=0 → delay ≥ base_seconds (jitter is additive only)."""
    delay = compute_backoff(0, base_seconds=5.0, max_seconds=300.0, jitter_ratio=0.0)
    assert delay == 5


def test_exponential_growth() -> None:
    """Without jitter, delay должна doubles на каждый retry."""
    delays = [
        compute_backoff(n, base_seconds=1.0, max_seconds=1000.0, jitter_ratio=0.0) for n in range(5)
    ]
    assert delays == [1, 2, 4, 8, 16]


def test_max_cap_enforced() -> None:
    """delay clamped к max_seconds even at high retry counts."""
    delay = compute_backoff(20, base_seconds=1.0, max_seconds=60.0, jitter_ratio=0.0)
    assert delay == 60


def test_jitter_inside_expected_range() -> None:
    """jitter_ratio=0.3 → delay ∈ [base, 1.3 * base]."""
    random.seed(42)
    samples = [
        compute_backoff(0, base_seconds=10.0, max_seconds=100.0, jitter_ratio=0.3)
        for _ in range(100)
    ]
    assert all(10 <= s <= 13 for s in samples), samples


def test_negative_retry_count_treated_as_zero() -> None:
    """Defensive: negative retry_count clamps к 0 (no negative exponents)."""
    assert compute_backoff(-1, base_seconds=5.0, max_seconds=300.0, jitter_ratio=0.0) == 5


def test_minimum_one_second_returned() -> None:
    """Even с base=0, the floor is 1 second so Celery countdown is meaningful."""
    delay = compute_backoff(0, base_seconds=0.0, max_seconds=100.0, jitter_ratio=0.0)
    assert delay >= 1
