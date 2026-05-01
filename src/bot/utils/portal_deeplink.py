"""Portal deeplink helper.

Bot cannot accept PII (per project rule + ФЗ-152). Setup flows that need
bank requisites or legal-profile data live exclusively in the web portal.

BL-055: the bot now mints its own portal-login URL by calling the API
endpoint ``POST /api/auth/exchange-bot-token-to-portal`` server-side
with HMAC auth. The returned ``ticket_url`` lands directly on an
``InlineKeyboardButton(url=…)`` — Telegram opens the user's external
browser, the portal exchanges the ticket for a session, and the user
arrives on the requested redirect path authenticated.

Note on TTL: the ticket the API mints is short-lived
(``settings.ticket_jwt_ttl_seconds``, default 300 s). A button minted
just before being shown to the user is fresh for 5 minutes; for delayed
taps beyond that window the portal returns 401 — the user's recourse is
to re-open the bot menu and tap again, which mints a new URL.
"""

from __future__ import annotations

import logging

import httpx

from src.api.auth_bot_hmac import sign_bot_request
from src.config.settings import settings

logger = logging.getLogger(__name__)

_EXCHANGE_PATH = "/api/auth/exchange-bot-token-to-portal"
_DEFAULT_TIMEOUT_S = 5.0


class PortalDeeplinkError(RuntimeError):
    """Raised when the bot cannot mint a portal URL.

    Callers should treat this as a soft failure (skip the button,
    surface a fallback message) — never bubble it up as a crash that
    breaks the entire menu render.
    """


async def build_portal_deeplink(
    telegram_id: int,
    redirect_path: str,
    *,
    http_client: httpx.AsyncClient | None = None,
) -> str:
    """Mint a portal-login URL for the given Telegram user.

    Returns the ticket URL on success. Raises :class:`PortalDeeplinkError`
    on any failure — network error, non-2xx response, malformed body.
    Callers should ``except PortalDeeplinkError`` and fall back to
    omitting the inline button.

    ``http_client`` is injected for tests; production passes ``None`` and
    a one-shot ``httpx.AsyncClient`` is created and closed inside.
    """
    body_bytes = _serialize_body(telegram_id=telegram_id, redirect_path=redirect_path)
    timestamp_header, signature_header = sign_bot_request(
        body_bytes=body_bytes,
        hmac_secret=settings.bot_api_hmac_secret,
    )
    headers = {
        "X-Bot-Auth-Timestamp": timestamp_header,
        "X-Bot-Auth-Signature": signature_header,
        "Content-Type": "application/json",
    }
    url = settings.internal_api_base_url.rstrip("/") + _EXCHANGE_PATH

    try:
        if http_client is None:
            async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT_S) as client:
                response = await client.post(url, content=body_bytes, headers=headers)
        else:
            response = await http_client.post(url, content=body_bytes, headers=headers)
    except httpx.HTTPError as exc:
        logger.warning(
            "portal_deeplink_http_error",
            extra={
                "event": "portal_deeplink_http_error",
                "telegram_id": telegram_id,
                "redirect_path": redirect_path,
                "error": str(exc),
            },
        )
        raise PortalDeeplinkError("HTTP transport failure") from exc

    if response.status_code != 200:
        logger.warning(
            "portal_deeplink_non_200",
            extra={
                "event": "portal_deeplink_non_200",
                "telegram_id": telegram_id,
                "redirect_path": redirect_path,
                "status_code": response.status_code,
            },
        )
        raise PortalDeeplinkError(f"API returned {response.status_code}")

    try:
        ticket_url = response.json()["ticket_url"]
    except (ValueError, KeyError, TypeError) as exc:
        logger.warning(
            "portal_deeplink_malformed_response",
            extra={
                "event": "portal_deeplink_malformed_response",
                "telegram_id": telegram_id,
                "redirect_path": redirect_path,
            },
        )
        raise PortalDeeplinkError("malformed API response") from exc

    if not isinstance(ticket_url, str) or not ticket_url:
        raise PortalDeeplinkError("API returned empty ticket_url")

    return ticket_url


def _serialize_body(*, telegram_id: int, redirect_path: str) -> bytes:
    """Build the canonical JSON body the API endpoint expects.

    Kept centralized so the signed bytes match the bytes that hit the
    wire — using ``json.dumps`` and shipping the same string we signed
    is the only way to keep HMAC stable across servers.
    """
    import json

    return json.dumps(
        {"telegram_id": telegram_id, "redirect_path": redirect_path},
        separators=(", ", ": "),
    ).encode()
