"""
Mock объекты для тестирования YooKassa SDK без реального API.
"""

from typing import Any


class MockConfirmation:
    """Mock объекта подтверждения платежа."""

    def __init__(self, url: str = "https://yookassa.ru/checkout/test") -> None:
        self.confirmation_url = url


class MockAmount:
    """Mock объекта суммы платежа."""

    def __init__(self, value: str = "100.00", currency: str = "RUB") -> None:
        self.value = value
        self.currency = currency


class MockYooKassaPayment:
    """
    Mock объекта платежа YooKassa.

    Имитирует ответ от YooKassa SDK для тестирования.
    """

    def __init__(
        self,
        payment_id: str = "test-payment-uuid-0001",
        status: str = "pending",
        paid: bool = False,
        confirmation_url: str = "https://yookassa.ru/checkout/test",
        amount_value: str = "100.00",
        amount_currency: str = "RUB",
        metadata: dict | None = None,
    ) -> None:
        self.id = payment_id
        self.status = status
        self.paid = paid
        self.confirmation = MockConfirmation(confirmation_url)
        self.amount = MockAmount(amount_value, amount_currency)
        self.metadata = metadata or {"user_id": "1", "amount_rub": "100"}


def mock_payment_create(
    payment_data: dict[str, Any], idempotency_key: str
) -> MockYooKassaPayment:
    """
    Mock функции Payment.create.

    Args:
        payment_data: Данные платежа.
        idempotency_key: Ключ идемпотентности.

    Returns:
        MockYooKassaPayment: Mock объект платежа.
    """
    metadata = payment_data.get("metadata", {})
    amount = payment_data.get("amount", {})

    return MockYooKassaPayment(
        payment_id="test-payment-uuid-0001",
        status="pending",
        paid=False,
        confirmation_url="https://yookassa.ru/checkout/test",
        amount_value=amount.get("value", "100.00"),
        amount_currency=amount.get("currency", "RUB"),
        metadata=metadata,
    )


def mock_payment_find_one(payment_id: str) -> MockYooKassaPayment:
    """
    Mock функции Payment.find_one.

    Args:
        payment_id: ID платежа.

    Returns:
        MockYooKassaPayment: Mock объект платежа со статусом 'succeeded'.
    """
    return MockYooKassaPayment(
        payment_id=payment_id,
        status="succeeded",
        paid=True,
        confirmation_url="https://yookassa.ru/checkout/test",
    )
