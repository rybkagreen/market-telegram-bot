"""Unit tests for YandexOrdProvider — driven by httpx.MockTransport + JSON
fixtures under tests/fixtures/yandex_ord/. No network hit."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import pytest

from src.core.services.yandex_ord_provider import (
    OrdRegistrationError,
    YandexOrdProvider,
)

pytestmark = pytest.mark.asyncio

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "yandex_ord"
# BASE_URL intentionally points at the host root — paths like "/api/v7/*"
# are then resolved against that root. Using a base_url ending in "/v7"
# causes httpx to join as "/v7/api/v7/..." (double prefix).
BASE_URL = "https://api.ord.yandex.net"
FAKE_BEARER = "fake-bearer-for-tests"  # noqa: S105 — not a real credential
REKHARBOR_ORG_ID = "rekharbor-main"
REKHARBOR_INN = "7707123456"


def _load(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


class _RouteRecorder:
    """Helper to record requests intercepted by MockTransport."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []

    def record(self, req: httpx.Request) -> httpx.Request:
        self.requests.append(req)
        return req


def _build_provider(handler) -> YandexOrdProvider:
    """Instantiate YandexOrdProvider with httpx.MockTransport injected."""
    provider = YandexOrdProvider(
        api_key=FAKE_BEARER,
        base_url=BASE_URL,
        rekharbor_org_id=REKHARBOR_ORG_ID,
        rekharbor_inn=REKHARBOR_INN,
    )
    # Swap out the client for one using MockTransport, preserving headers.
    provider._client = httpx.AsyncClient(
        base_url=BASE_URL,
        headers={"Authorization": f"Bearer {FAKE_BEARER}"},
        transport=httpx.MockTransport(handler),
    )
    return provider


# ────────────────────────────────────────────
# ORG_TYPE_MAP mapping
# ────────────────────────────────────────────


# Pure static-map tests live in `tests/unit/test_yandex_ord_org_type_map.py`
# to keep them outside this module's `pytestmark = pytest.mark.asyncio`.


# ────────────────────────────────────────────
# register_advertiser
# ────────────────────────────────────────────


async def test_register_advertiser_sends_correct_payload() -> None:
    recorder = _RouteRecorder()

    def handler(req: httpx.Request) -> httpx.Response:
        recorder.record(req)
        assert req.method == "POST"
        assert req.url.path == "/api/v7/organization"
        assert req.headers["authorization"] == f"Bearer {FAKE_BEARER}"
        body = json.loads(req.content)
        assert body["id"] == "org-42"
        assert body["inn"] == "7707083893"
        assert body["isOrs"] is False
        assert body["isRr"] is False
        assert body["name"] == "ООО «Тест»"
        return httpx.Response(200, json=_load("register_organization_success.json"))

    provider = _build_provider(handler)
    org_id = await provider.register_advertiser(42, "ООО «Тест»", "7707083893")
    assert org_id == "org-42"
    assert len(recorder.requests) == 1


async def test_register_advertiser_handles_missing_inn() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        body = json.loads(req.content)
        assert body["inn"] == ""  # provider defaults to empty string
        return httpx.Response(200, json={"id": "org-42"})

    provider = _build_provider(handler)
    await provider.register_advertiser(42, "Test", None)


# ────────────────────────────────────────────
# register_platform
# ────────────────────────────────────────────


async def test_register_platform_sends_deterministic_id() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        assert req.url.path == "/api/v7/platforms"
        body = json.loads(req.content)
        assert body["organizationId"] == REKHARBOR_ORG_ID
        assert body["platforms"][0]["platformId"] == "platform-101"
        assert body["platforms"][0]["type"] == "site"
        assert body["platforms"][0]["url"] == "https://t.me/test_channel"
        assert body["platforms"][0]["isOwned"] is False
        return httpx.Response(200, json=_load("register_platform_success.json"))

    provider = _build_provider(handler)
    platform_id = await provider.register_platform(
        101, "https://t.me/test_channel", "Test Channel"
    )
    assert platform_id == "platform-101"


# ────────────────────────────────────────────
# register_contract
# ────────────────────────────────────────────


async def test_register_contract_sends_deterministic_id() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        assert req.url.path == "/api/v7/contract"
        body = json.loads(req.content)
        assert body["id"] == "contract-500"
        assert body["contractorId"] == REKHARBOR_ORG_ID
        assert body["clientId"] == "org-42"
        assert body["isRegReport"] is True
        assert body["subjectType"] == "distribution"
        assert body["amount"] == "1000.00"
        return httpx.Response(200, json=_load("register_contract_success.json"))

    provider = _build_provider(handler)
    contract_id = await provider.register_contract(500, "org-42", "1000.00", "2026-04-21")
    assert contract_id == "contract-500"


# ────────────────────────────────────────────
# register_creative
# ────────────────────────────────────────────


@pytest.mark.parametrize(
    ("media_type", "expected_form"),
    [
        ("video", "text_video_block"),
        ("photo", "text_graphic_block"),
        ("image", "text_graphic_block"),
        ("none", "text_block"),
        ("text", "text_block"),
    ],
)
async def test_register_creative_form_depends_on_media(
    media_type: str, expected_form: str
) -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        assert req.url.path == "/api/v7/creative"
        body = json.loads(req.content)
        assert body["form"] == expected_form
        return httpx.Response(200, json=_load("register_creative_success.json"))

    provider = _build_provider(handler)
    token = await provider.register_creative(500, "Ad text", media_type, "org-42")
    assert token == "kra23abc-erid-token-xyz789"


async def test_register_creative_includes_deterministic_contract_id() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        body = json.loads(req.content)
        assert body["id"] == "creative-500"
        assert body["contractIds"] == ["contract-500"]
        assert body["kktuCodes"] == ["30.10.1"]
        assert body["textData"] == ["Ad text"]
        return httpx.Response(200, json=_load("register_creative_success.json"))

    provider = _build_provider(handler)
    await provider.register_creative(500, "Ad text", "none", "org-42")


async def test_register_creative_raises_when_token_missing() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_load("register_creative_missing_token.json"))

    provider = _build_provider(handler)
    with pytest.raises(OrdRegistrationError, match="missing 'token'"):
        await provider.register_creative(500, "Ad", "none", "org-42")


# ────────────────────────────────────────────
# report_publication
# ────────────────────────────────────────────


async def test_report_publication_payload_shape() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        assert req.url.path == "/api/v7/statistics"
        body = json.loads(req.content)
        stat = body["statistics"][0]
        assert stat["creativeId"] == "creative-500"
        assert stat["impsFact"] == 1
        assert stat["type"] == "other"
        assert stat["amount"]["vatRate"] == "100"
        return httpx.Response(200, json=_load("report_publication_success.json"))

    provider = _build_provider(handler)
    ok = await provider.report_publication(
        erid="kra23abc-erid-token-xyz789",
        published_at=datetime(2026, 4, 21, 11, 0, 0, tzinfo=UTC),
        placement_request_id=500,
    )
    assert ok is True


# ────────────────────────────────────────────
# get_status / check_erir_status
# ────────────────────────────────────────────


async def test_get_status_returns_status_string() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        assert req.url.path == "/api/v7/status"
        assert req.url.params["reqid"] == "req-abc-123-xyz"
        return httpx.Response(200, json=_load("status_erir_confirmed.json"))

    provider = _build_provider(handler)
    status = await provider.get_status("req-abc-123-xyz")
    assert status == "ERIR sync success"


async def test_check_erir_status_returns_full_payload() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_load("status_erir_failed.json"))

    provider = _build_provider(handler)
    result = await provider.check_erir_status("req-abc-123-xyz")
    assert result["status"] == "ERIR async error"
    assert result["errorCode"] == "EINVAL"


# ────────────────────────────────────────────
# Error handling
# ────────────────────────────────────────────


async def test_401_raises_ord_registration_error() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json=_load("error_401_invalid_token.json"))

    provider = _build_provider(handler)
    with pytest.raises(OrdRegistrationError, match="401"):
        await provider.register_advertiser(42, "Test", "7707083893")


async def test_422_validation_error() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(422, json=_load("error_422_validation.json"))

    provider = _build_provider(handler)
    with pytest.raises(OrdRegistrationError, match="validation error"):
        await provider.register_advertiser(42, "T", "123")


async def test_429_rate_limit_raises_client_error() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json=_load("error_429_rate_limit.json"))

    provider = _build_provider(handler)
    with pytest.raises(OrdRegistrationError, match="429"):
        await provider.register_advertiser(42, "T", "7707083893")


async def test_500_server_error_raises_with_retry_hint() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json=_load("error_500_server.json"))

    provider = _build_provider(handler)
    with pytest.raises(OrdRegistrationError, match="server error 500"):
        await provider.register_advertiser(42, "T", "7707083893")


async def test_connection_error_raises_ord_registration_error() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("cannot connect")

    provider = _build_provider(handler)
    with pytest.raises(OrdRegistrationError, match="Connection timeout|Request error"):
        await provider.register_advertiser(42, "T", "7707083893")
