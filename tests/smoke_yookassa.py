#!/usr/bin/env python3
"""
Smoke тесты для YooKassa интеграции.
Запускаются внутри контейнера и проверяют все компоненты без реального API.
"""

import asyncio
import sys
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock, patch

# Тест T-01: Import check
def test_t01_import_yookassa_service() -> bool:
    """T-01: Import YooKassaService."""
    try:
        from src.core.services.yookassa_service import YooKassaService
        print("OK: T-01 - import YooKassaService")
        return True
    except Exception as e:
        print(f"FAIL: T-01 - {e}")
        return False


# Тест T-02: Service init без credentials
def test_t02_service_init_no_credentials() -> bool:
    """T-02: Service init без credentials."""
    try:
        from src.core.services.yookassa_service import YooKassaService
        svc = YooKassaService()
        # Сервис должен инициализироваться даже без credentials (с warning)
        print("OK: T-02 - graceful init without credentials")
        return True
    except Exception as e:
        print(f"FAIL: T-02 - {e}")
        return False


# Тест T-03: Import model YooKassaPayment
def test_t03_import_model() -> bool:
    """T-03: Import YooKassaPayment model."""
    try:
        from src.db.models.yookassa_payment import YooKassaPayment
        print("OK: T-03 - import YooKassaPayment model")
        return True
    except Exception as e:
        print(f"FAIL: T-03 - {e}")
        return False


# Тест T-04: Model columns check
def test_t04_model_columns() -> bool:
    """T-04: Model columns check."""
    try:
        from src.db.models.yookassa_payment import YooKassaPayment
        cols = [c.name for c in YooKassaPayment.__table__.columns]
        required = ['id', 'payment_id', 'user_id', 'amount_rub', 'credits', 'status', 'idempotency_key']
        missing = set(required) - set(cols)
        if missing:
            print(f"FAIL: T-04 - Missing columns: {missing}")
            return False
        print("OK: T-04 - all required columns present")
        return True
    except Exception as e:
        print(f"FAIL: T-04 - {e}")
        return False


# Тест T-05: Notification formatter
def test_t05_notification_formatter() -> bool:
    """T-05: Notification formatter."""
    try:
        from src.bot.handlers.shared.notifications import format_yookassa_payment_success
        result = format_yookassa_payment_success(Decimal("300"), 330, 1330)
        assert "<b>" in result, "HTML tags missing"
        assert "300" in result, "Amount missing"
        assert "330" in result, "Credits missing"
        assert "parse_mode" not in result, "parse_mode should not be in output"
        print("OK: T-05 - formatter returns HTML with correct values")
        return True
    except Exception as e:
        print(f"FAIL: T-05 - {e}")
        return False


# Тест T-06: HTML tags не экранированы
def test_t06_html_not_escaped() -> bool:
    """T-06: HTML tags are not escaped."""
    try:
        from src.bot.handlers.shared.notifications import format_yookassa_payment_success
        text = format_yookassa_payment_success(Decimal("100"), 100, 200)
        assert "&lt;" not in text and "&gt;" not in text, "HTML tags are escaped!"
        print("OK: T-06 - HTML tags are not escaped")
        return True
    except Exception as e:
        print(f"FAIL: T-06 - {e}")
        return False


# Тест T-07: Mock create_payment flow
async def test_t07_mock_create_payment() -> bool:
    """T-07: Mock create_payment flow."""
    try:
        from tests.mocks.yookassa_mock import mock_payment_create, MockYooKassaPayment
        from src.core.services.yookassa_service import YooKassaService
        from src.db.session import async_session_factory
        from sqlalchemy import select
        from src.db.models.yookassa_payment import YooKassaPayment

        # Патчим Payment.create
        with patch("src.core.services.yookassa_service.Payment.create", side_effect=mock_payment_create):
            svc = YooKassaService()
            # Создаём тестового пользователя если нет
            async with async_session_factory() as session:
                from src.db.models.user import User
                from src.db.repositories.user_repo import UserRepository

                user_repo = UserRepository(session)
                user = await user_repo.get_by_telegram_id(999999)
                if not user:
                    user = await user_repo.create(
                        telegram_id=999999,
                        first_name="Test",
                        username="testuser",
                    )

                user_id = user.id

            # Создаём платёж
            record = await svc.create_payment(
                amount_rub=Decimal("100"),
                credits=100,
                user_id=user_id,
            )

            assert record is not None, "Payment record is None"
            assert record.confirmation_url is not None, "confirmation_url is None"
            assert "test-payment-uuid" in record.payment_id, "Invalid payment_id"

            print("OK: T-07 - mock create_payment flow")
            return True

    except Exception as e:
        print(f"FAIL: T-07 - {e}")
        import traceback
        traceback.print_exc()
        return False


# Тест T-08: Billing handler imports
def test_t08_billing_handlers() -> bool:
    """T-08: Billing handler imports."""
    try:
        import importlib
        m = importlib.import_module("src.bot.handlers.billing.billing")
        handlers = [name for name in dir(m) if "yookassa" in name.lower() or "yk_" in name.lower()]
        if not handlers:
            print(f"FAIL: T-08 - No YooKassa handlers found")
            return False
        print(f"OK: T-08 - YooKassa handlers found: {handlers}")
        return True
    except Exception as e:
        print(f"FAIL: T-08 - {e}")
        return False


# Тест T-09: Webhook endpoint registered
def test_t09_webhook_endpoint() -> bool:
    """T-09: Webhook endpoint registered."""
    try:
        from src.api.routers.billing import router
        routes = [r.path for r in router.routes]
        if "/webhooks/yookassa" not in routes:
            print(f"FAIL: T-09 - Route not found. Routes: {routes}")
            return False
        print("OK: T-09 - /webhooks/yookassa route registered")
        return True
    except Exception as e:
        print(f"FAIL: T-09 - {e}")
        return False


# Тест T-10: YooKassa packages constant
def test_t10_yookassa_packages() -> bool:
    """T-10: YooKassa packages constant."""
    try:
        from src.constants.payments import YOOKASSA_PACKAGES
        if not YOOKASSA_PACKAGES:
            print("FAIL: T-10 - YOOKASSA_PACKAGES is empty")
            return False
        if len(YOOKASSA_PACKAGES) != 5:
            print(f"FAIL: T-10 - Expected 5 packages, got {len(YOOKASSA_PACKAGES)}")
            return False
        for pkg in YOOKASSA_PACKAGES:
            assert "rub" in pkg, "Missing 'rub' key"
            assert "credits" in pkg, "Missing 'credits' key"
            assert "label" in pkg, "Missing 'label' key"
        print("OK: T-10 - YOOKASSA_PACKAGES has correct structure")
        return True
    except Exception as e:
        print(f"FAIL: T-10 - {e}")
        return False


def run_all_tests() -> dict[str, Any]:
    """Запустить все тесты."""
    tests = [
        ("T-01", test_t01_import_yookassa_service),
        ("T-02", test_t02_service_init_no_credentials),
        ("T-03", test_t03_import_model),
        ("T-04", test_t04_model_columns),
        ("T-05", test_t05_notification_formatter),
        ("T-06", test_t06_html_not_escaped),
        ("T-07", lambda: asyncio.run(test_t07_mock_create_payment())),
        ("T-08", test_t08_billing_handlers),
        ("T-09", test_t09_webhook_endpoint),
        ("T-10", test_t10_yookassa_packages),
    ]

    results = {"passed": 0, "failed": 0, "details": []}

    print("=" * 60)
    print("YooKassa Smoke Tests")
    print("=" * 60)

    for test_id, test_fn in tests:
        try:
            if test_fn():
                results["passed"] += 1
                results["details"].append(f"{test_id}: OK")
            else:
                results["failed"] += 1
                results["details"].append(f"{test_id}: FAIL")
        except Exception as e:
            results["failed"] += 1
            results["details"].append(f"{test_id}: EXCEPTION - {e}")

    print("=" * 60)
    print(f"Results: {results['passed']} passed, {results['failed']} failed")
    print("=" * 60)

    return results


if __name__ == "__main__":
    results = run_all_tests()
    sys.exit(0 if results["failed"] == 0 else 1)
