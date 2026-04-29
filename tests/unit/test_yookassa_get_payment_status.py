"""Unit tests for YooKassaService.get_payment_status (Промт-15.13.1).

Covers return-type honesty: SDK без type stubs возвращает Any →
get_payment_status declared str | None. Tests verify None handling
when SDK doesn't return a status field.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from src.core.services.yookassa_service import YooKassaService

pytestmark = pytest.mark.asyncio


async def test_get_payment_status_returns_string_when_sdk_returns_status():
    service = YooKassaService()
    fake_payment = SimpleNamespace(status="succeeded")

    with patch(
        "src.core.services.yookassa_service.Payment.find_one",
        return_value=fake_payment,
    ):
        result = await service.get_payment_status("yk-test-001")

    assert result == "succeeded"


async def test_get_payment_status_returns_none_when_status_missing():
    service = YooKassaService()
    fake_payment = SimpleNamespace()

    with patch(
        "src.core.services.yookassa_service.Payment.find_one",
        return_value=fake_payment,
    ):
        result = await service.get_payment_status("yk-test-001")

    assert result is None


async def test_get_payment_status_returns_none_when_status_is_none():
    service = YooKassaService()
    fake_payment = SimpleNamespace(status=None)

    with patch(
        "src.core.services.yookassa_service.Payment.find_one",
        return_value=fake_payment,
    ):
        result = await service.get_payment_status("yk-test-001")

    assert result is None


async def test_get_payment_status_returns_none_when_status_not_string():
    service = YooKassaService()
    fake_payment = SimpleNamespace(status=42)

    with patch(
        "src.core.services.yookassa_service.Payment.find_one",
        return_value=fake_payment,
    ):
        result = await service.get_payment_status("yk-test-001")

    assert result is None
