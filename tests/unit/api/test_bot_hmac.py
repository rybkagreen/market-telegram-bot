"""Unit tests for ``src.api.auth_bot_hmac`` — sign/verify round-trip,
tampering, replay window. (BL-055; HMAC secret split from BOT_TOKEN in BL-066.)"""

from __future__ import annotations

import time

import pytest

from src.api.auth_bot_hmac import sign_bot_request, verify_bot_request_signature

HMAC_SECRET = "test-hmac-secret-do-not-use-in-production"
TOLERANCE = 60


def test_signed_request_verifies() -> None:
    body = b'{"telegram_id": 42, "redirect_path": "/own/payouts/request"}'
    ts, sig = sign_bot_request(body_bytes=body, hmac_secret=HMAC_SECRET)
    assert verify_bot_request_signature(
        timestamp_header=ts,
        body_bytes=body,
        signature_header=sig,
        hmac_secret=HMAC_SECRET,
        tolerance_sec=TOLERANCE,
    )


def test_tampered_body_rejected() -> None:
    body = b'{"telegram_id": 42, "redirect_path": "/own/payouts/request"}'
    ts, sig = sign_bot_request(body_bytes=body, hmac_secret=HMAC_SECRET)
    tampered = b'{"telegram_id": 999, "redirect_path": "/own/payouts/request"}'
    assert not verify_bot_request_signature(
        timestamp_header=ts,
        body_bytes=tampered,
        signature_header=sig,
        hmac_secret=HMAC_SECRET,
        tolerance_sec=TOLERANCE,
    )


def test_wrong_secret_rejected() -> None:
    body = b'{"x":1}'
    ts, sig = sign_bot_request(body_bytes=body, hmac_secret=HMAC_SECRET)
    assert not verify_bot_request_signature(
        timestamp_header=ts,
        body_bytes=body,
        signature_header=sig,
        hmac_secret="some-other-secret",
        tolerance_sec=TOLERANCE,
    )


def test_expired_timestamp_rejected() -> None:
    body = b'{"x":1}'
    long_ago = int(time.time() * 1000) - (TOLERANCE * 1000) - 5_000
    ts, sig = sign_bot_request(body_bytes=body, hmac_secret=HMAC_SECRET, timestamp_ms=long_ago)
    assert not verify_bot_request_signature(
        timestamp_header=ts,
        body_bytes=body,
        signature_header=sig,
        hmac_secret=HMAC_SECRET,
        tolerance_sec=TOLERANCE,
    )


def test_future_timestamp_outside_window_rejected() -> None:
    body = b'{"x":1}'
    far_future = int(time.time() * 1000) + (TOLERANCE * 1000) + 5_000
    ts, sig = sign_bot_request(body_bytes=body, hmac_secret=HMAC_SECRET, timestamp_ms=far_future)
    assert not verify_bot_request_signature(
        timestamp_header=ts,
        body_bytes=body,
        signature_header=sig,
        hmac_secret=HMAC_SECRET,
        tolerance_sec=TOLERANCE,
    )


def test_inside_window_at_boundary_accepted() -> None:
    body = b'{"x":1}'
    now_ms = 1_700_000_000_000  # fixed clock for determinism
    ts, sig = sign_bot_request(body_bytes=body, hmac_secret=HMAC_SECRET, timestamp_ms=now_ms)
    # exactly +tolerance — accepted
    assert verify_bot_request_signature(
        timestamp_header=ts,
        body_bytes=body,
        signature_header=sig,
        hmac_secret=HMAC_SECRET,
        tolerance_sec=TOLERANCE,
        now_ms=now_ms + TOLERANCE * 1000,
    )
    # +tolerance + 1 ms — rejected
    assert not verify_bot_request_signature(
        timestamp_header=ts,
        body_bytes=body,
        signature_header=sig,
        hmac_secret=HMAC_SECRET,
        tolerance_sec=TOLERANCE,
        now_ms=now_ms + TOLERANCE * 1000 + 1,
    )


def test_missing_headers_rejected() -> None:
    body = b'{"x":1}'
    assert not verify_bot_request_signature(
        timestamp_header=None,
        body_bytes=body,
        signature_header="abcd",
        hmac_secret=HMAC_SECRET,
        tolerance_sec=TOLERANCE,
    )
    assert not verify_bot_request_signature(
        timestamp_header="1234",
        body_bytes=body,
        signature_header=None,
        hmac_secret=HMAC_SECRET,
        tolerance_sec=TOLERANCE,
    )


@pytest.mark.parametrize("garbage", ["", "not-a-number", "1.5e10", "  "])
def test_malformed_timestamp_rejected(garbage: str) -> None:
    body = b'{"x":1}'
    _ts, sig = sign_bot_request(body_bytes=body, hmac_secret=HMAC_SECRET)
    assert not verify_bot_request_signature(
        timestamp_header=garbage,
        body_bytes=body,
        signature_header=sig,
        hmac_secret=HMAC_SECRET,
        tolerance_sec=TOLERANCE,
    )


def test_signature_case_insensitive() -> None:
    body = b'{"x":1}'
    ts, sig = sign_bot_request(body_bytes=body, hmac_secret=HMAC_SECRET)
    # caller forwards uppercase hex — still valid
    assert verify_bot_request_signature(
        timestamp_header=ts,
        body_bytes=body,
        signature_header=sig.upper(),
        hmac_secret=HMAC_SECRET,
        tolerance_sec=TOLERANCE,
    )
