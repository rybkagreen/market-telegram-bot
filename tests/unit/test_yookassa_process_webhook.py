"""Unit tests for YooKassaService.process_webhook (Промт-15.13 / 14b).

Pure unit tests: no DB, no network, no FastAPI. Cover:
- IP whitelist authorisation (positive + negative + missing IP)
- JSON parse failure
- Structural validation (missing event / object / object.id)
- Successful event construction (event_type, payment_id, payload)
"""

from __future__ import annotations

import json

import pytest

from src.core.services.yookassa_service import (
    InvalidPayloadError,
    InvalidSignatureError,
    WebhookEvent,
    YooKassaService,
)

pytestmark = pytest.mark.asyncio


def _valid_body() -> bytes:
    return json.dumps({
        "event": "payment.succeeded",
        "object": {
            "id": "yk-test-001",
            "status": "succeeded",
            "amount": {"value": "510.00", "currency": "RUB"},
            "payment_method": {"type": "bank_card"},
            "receipt": {"id": "rcpt-001"},
            "metadata": {
                "user_id": "42",
                "desired_balance": "500.00",
            },
        },
    }).encode()


# ───── Authorization ─────────────────────────────────────────────


async def test_process_webhook_accepts_whitelisted_ip():
    service = YooKassaService()
    event = await service.process_webhook(_valid_body(), "185.71.76.5")

    assert isinstance(event, WebhookEvent)
    assert event.event_type == "payment.succeeded"
    assert event.payment_id == "yk-test-001"
    assert event.payload["payment_method"]["type"] == "bank_card"
    assert event.payload["receipt"]["id"] == "rcpt-001"


async def test_process_webhook_rejects_off_whitelist_ip():
    service = YooKassaService()
    with pytest.raises(InvalidSignatureError):
        await service.process_webhook(_valid_body(), "8.8.8.8")


async def test_process_webhook_rejects_missing_ip():
    service = YooKassaService()
    with pytest.raises(InvalidSignatureError):
        await service.process_webhook(_valid_body(), None)


async def test_process_webhook_rejects_malformed_ip():
    service = YooKassaService()
    with pytest.raises(InvalidSignatureError):
        await service.process_webhook(_valid_body(), "not-an-ip")


async def test_process_webhook_accepts_ipv6_whitelisted():
    service = YooKassaService()
    event = await service.process_webhook(_valid_body(), "2a02:5180::1")

    assert event.payment_id == "yk-test-001"


# ───── Payload parsing ───────────────────────────────────────────


async def test_process_webhook_rejects_invalid_json():
    service = YooKassaService()
    with pytest.raises(InvalidPayloadError):
        await service.process_webhook(b"not-json{", "185.71.76.5")


async def test_process_webhook_rejects_non_object_body():
    service = YooKassaService()
    with pytest.raises(InvalidPayloadError):
        await service.process_webhook(b"[1, 2, 3]", "185.71.76.5")


async def test_process_webhook_rejects_missing_event_field():
    service = YooKassaService()
    body = json.dumps({"object": {"id": "yk-1"}}).encode()
    with pytest.raises(InvalidPayloadError):
        await service.process_webhook(body, "185.71.76.5")


async def test_process_webhook_rejects_missing_object_field():
    service = YooKassaService()
    body = json.dumps({"event": "payment.succeeded"}).encode()
    with pytest.raises(InvalidPayloadError):
        await service.process_webhook(body, "185.71.76.5")


async def test_process_webhook_rejects_missing_payment_id():
    service = YooKassaService()
    body = json.dumps({
        "event": "payment.succeeded",
        "object": {"status": "succeeded"},
    }).encode()
    with pytest.raises(InvalidPayloadError):
        await service.process_webhook(body, "185.71.76.5")


async def test_process_webhook_passes_through_other_event_types():
    """Other event types (refund, cancellation) parse OK — dispatch is router's job."""
    service = YooKassaService()
    body = json.dumps({
        "event": "payment.canceled",
        "object": {"id": "yk-cancel-7", "status": "canceled"},
    }).encode()

    event = await service.process_webhook(body, "185.71.77.10")

    assert event.event_type == "payment.canceled"
    assert event.payment_id == "yk-cancel-7"


# ───── DTO immutability ──────────────────────────────────────────


async def test_webhook_event_is_frozen():
    """WebhookEvent is a frozen dataclass — caller cannot mutate it."""
    service = YooKassaService()
    event = await service.process_webhook(_valid_body(), "185.71.76.5")

    with pytest.raises((AttributeError, TypeError)):
        event.event_type = "spoofed"  # type: ignore[misc]
