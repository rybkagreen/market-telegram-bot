"""Unit tests for ``src.bot.utils.portal_deeplink.build_portal_deeplink`` (BL-055).

The helper signs a body with HMAC-SHA256(BOT_API_HMAC_SECRET, …), POSTs it
to the internal API, and returns the ``ticket_url`` from the response. Tests
verify the wire format (headers, body), success path, and that every
HTTP-layer failure mode collapses to ``PortalDeeplinkError`` (so callers
can blanket-catch and skip the button).

The HMAC key was split from BOT_TOKEN in BL-066 (defence-in-depth).
"""

from __future__ import annotations

import hmac
import json
from typing import Any

import httpx
import pytest

from src.bot.utils.portal_deeplink import (
    PortalDeeplinkError,
    build_portal_deeplink,
)
from src.config.settings import settings


def _make_handler(
    *,
    response_json: dict[str, Any] | None = None,
    status_code: int = 200,
    captured: dict[str, Any] | None = None,
):
    """Return an httpx MockTransport handler that captures + replies."""

    def _handler(request: httpx.Request) -> httpx.Response:
        if captured is not None:
            captured["url"] = str(request.url)
            captured["headers"] = dict(request.headers)
            captured["body"] = request.content
        if response_json is None:
            return httpx.Response(status_code=status_code)
        return httpx.Response(status_code=status_code, json=response_json)

    return _handler


@pytest.mark.asyncio
async def test_happy_path_returns_ticket_url() -> None:
    captured: dict[str, Any] = {}
    transport = httpx.MockTransport(
        _make_handler(
            response_json={"ticket_url": "https://portal.example/login/ticket?ticket=AAA"},
            captured=captured,
        )
    )
    async with httpx.AsyncClient(transport=transport) as client:
        url = await build_portal_deeplink(
            telegram_id=12345,
            redirect_path="/own/payouts/request",
            http_client=client,
        )
    assert url == "https://portal.example/login/ticket?ticket=AAA"

    # URL hits the internal base + endpoint path, never the public api URL.
    assert captured["url"].endswith("/api/auth/exchange-bot-token-to-portal")
    assert captured["url"].startswith(settings.internal_api_base_url.rstrip("/"))


@pytest.mark.asyncio
async def test_signature_matches_signed_body() -> None:
    captured: dict[str, Any] = {}
    transport = httpx.MockTransport(
        _make_handler(
            response_json={"ticket_url": "https://portal.example/login/ticket?ticket=Z"},
            captured=captured,
        )
    )
    async with httpx.AsyncClient(transport=transport) as client:
        await build_portal_deeplink(
            telegram_id=42,
            redirect_path="/own/payouts/request",
            http_client=client,
        )

    body = captured["body"]
    parsed = json.loads(body.decode())
    assert parsed == {"telegram_id": 42, "redirect_path": "/own/payouts/request"}

    ts_header = captured["headers"]["x-bot-auth-timestamp"]
    sig_header = captured["headers"]["x-bot-auth-signature"]

    # Recompute HMAC the way the API verifier does.
    import hashlib

    message = f"{int(ts_header)}.".encode() + body
    expected = hmac.new(settings.bot_api_hmac_secret.encode(), message, hashlib.sha256).hexdigest()
    assert hmac.compare_digest(expected, sig_header)


@pytest.mark.asyncio
async def test_non_200_raises_portal_deeplink_error() -> None:
    transport = httpx.MockTransport(_make_handler(status_code=401))
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(PortalDeeplinkError):
            await build_portal_deeplink(
                telegram_id=42,
                redirect_path="/own/payouts/request",
                http_client=client,
            )


@pytest.mark.asyncio
async def test_400_raises_portal_deeplink_error() -> None:
    transport = httpx.MockTransport(
        _make_handler(status_code=400, response_json={"detail": "redirect_path not allowed"})
    )
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(PortalDeeplinkError):
            await build_portal_deeplink(
                telegram_id=42,
                redirect_path="/admin/secret",
                http_client=client,
            )


@pytest.mark.asyncio
async def test_malformed_json_raises_portal_deeplink_error() -> None:
    def _handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=200, content=b"not-json")

    transport = httpx.MockTransport(_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(PortalDeeplinkError):
            await build_portal_deeplink(
                telegram_id=42,
                redirect_path="/own/payouts/request",
                http_client=client,
            )


@pytest.mark.asyncio
async def test_missing_ticket_url_field_raises_portal_deeplink_error() -> None:
    transport = httpx.MockTransport(
        _make_handler(response_json={"something_else": "x"}, status_code=200)
    )
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(PortalDeeplinkError):
            await build_portal_deeplink(
                telegram_id=42,
                redirect_path="/own/payouts/request",
                http_client=client,
            )


@pytest.mark.asyncio
async def test_empty_ticket_url_raises_portal_deeplink_error() -> None:
    transport = httpx.MockTransport(
        _make_handler(response_json={"ticket_url": ""}, status_code=200)
    )
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(PortalDeeplinkError):
            await build_portal_deeplink(
                telegram_id=42,
                redirect_path="/own/payouts/request",
                http_client=client,
            )


@pytest.mark.asyncio
async def test_network_error_raises_portal_deeplink_error() -> None:
    def _handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom")

    transport = httpx.MockTransport(_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(PortalDeeplinkError):
            await build_portal_deeplink(
                telegram_id=42,
                redirect_path="/own/payouts/request",
                http_client=client,
            )
