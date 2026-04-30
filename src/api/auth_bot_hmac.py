"""HMAC-SHA256 verification for server-to-server bot → API requests (BL-055).

The bot signs each request to ``/api/auth/exchange-bot-token-to-portal`` with
``HMAC_SHA256(BOT_TOKEN, <timestamp_ms>.<raw_body>)`` and forwards the proof
in two headers:

* ``X-Bot-Auth-Timestamp`` — milliseconds since epoch, kept inside a
  ±``bot_auth_timestamp_tolerance_sec`` window to bound replay risk.
* ``X-Bot-Auth-Signature`` — lowercase hex HMAC.

Module is pure: no settings import, no logging of secrets / timestamps,
no side effects. The handler in ``auth.py`` injects the live values.
"""

from __future__ import annotations

import hashlib
import hmac
import time


def verify_bot_request_signature(
    *,
    timestamp_header: str | None,
    body_bytes: bytes,
    signature_header: str | None,
    bot_token: str,
    tolerance_sec: int,
    now_ms: int | None = None,
) -> bool:
    """Return True iff the request is well-formed and authentic.

    Performs all three checks before returning:
        1. Both headers present and parseable.
        2. ``|now_ms - timestamp_ms| <= tolerance_sec * 1000``.
        3. ``hmac.compare_digest(expected_hex, signature_hex)`` is True.

    ``now_ms`` is injected for tests; production passes ``None`` and lets
    this helper read the wall clock.
    """
    if timestamp_header is None or signature_header is None:
        return False

    try:
        timestamp_ms = int(timestamp_header)
    except (TypeError, ValueError):
        return False

    current_ms = now_ms if now_ms is not None else int(time.time() * 1000)
    if abs(current_ms - timestamp_ms) > tolerance_sec * 1000:
        return False

    message = f"{timestamp_ms}.".encode() + body_bytes
    expected_hex = hmac.new(bot_token.encode(), message, hashlib.sha256).hexdigest()

    # Constant-time compare — rejects timing-side-channel attacks even if a
    # caller controls signature_header byte-by-byte.
    return hmac.compare_digest(expected_hex, signature_header.strip().lower())


def sign_bot_request(
    *,
    body_bytes: bytes,
    bot_token: str,
    timestamp_ms: int | None = None,
) -> tuple[str, str]:
    """Return ``(timestamp_header, signature_header)`` for the bot side.

    Mirror of ``verify_bot_request_signature``. Kept here so the bot helper
    and the verifier share one definition of the signed-message wire format.
    """
    ts_ms = timestamp_ms if timestamp_ms is not None else int(time.time() * 1000)
    message = f"{ts_ms}.".encode() + body_bytes
    signature = hmac.new(bot_token.encode(), message, hashlib.sha256).hexdigest()
    return str(ts_ms), signature
