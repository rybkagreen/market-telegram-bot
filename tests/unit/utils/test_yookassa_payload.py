"""Unit tests for ``src.utils.yookassa_payload`` projection (16.5c / BL-051).

Coverage:
- FISCAL fields retained (top-level + receipt subtree)
- ROUNDTRIP (`metadata`) retained
- TRANSPORT (`test`) retained
- PII dropped (receipt.customer)
- TRANSPORT/PCI subtrees dropped (recipient, payment_method, confirmation)
- Edge cases: empty dict, None, non-dict input, receipt None / receipt {}
- Immutability: result mutation does not affect input sample
"""

from __future__ import annotations

from typing import Any

from src.utils.yookassa_payload import (
    FISCAL_TOP_LEVEL,
    RECEIPT_FISCAL_FIELDS,
    ROUNDTRIP_TOP_LEVEL,
    TRANSPORT_TOP_LEVEL,
    extract_persistable_metadata,
)


def _sample_payload() -> dict[str, Any]:
    """Realistic YooKassa ``payment.succeeded`` ``object`` payload.

    Mixes all four categories to exercise the full projection contract.
    """
    return {
        # FISCAL top-level
        "id": "yk-test-uuid-0001",
        "status": "succeeded",
        "paid": True,
        "amount": {"value": "517.50", "currency": "RUB"},
        "income_amount": {"value": "499.40", "currency": "RUB"},
        "captured_at": "2026-04-30T10:15:30.000Z",
        "created_at": "2026-04-30T10:15:00.000Z",
        "expires_at": "2026-04-30T11:00:00.000Z",
        "description": "Пополнение баланса RekHarborBot: 500.00 ₽",
        "refundable": True,
        "refunded_amount": {"value": "0.00", "currency": "RUB"},
        "receipt_registration": "succeeded",
        "cancellation_details": None,
        "authorization_details": {
            "rrn": "123456789012",
            "auth_code": "987654",
            "three_d_secure": {"applied": True},
        },
        "transfers": [],
        "deal": None,
        # ROUNDTRIP
        "metadata": {
            "user_id": "42",
            "desired_balance": "500.00",
            "fee_amount": "17.50",
            "gross_amount": "517.50",
        },
        # TRANSPORT (retained for diagnostic)
        "test": False,
        # PII / PCI / Transport — must be dropped
        "recipient": {
            "account_id": "shop-id-9999",
            "gateway_id": "gateway-id-1234",
        },
        "payment_method": {
            "type": "bank_card",
            "id": "pm-uuid-5678",
            "saved": False,
            "title": "Bank card *4242",
            "card": {
                "first6": "411111",
                "last4": "4242",
                "expiry_month": "12",
                "expiry_year": "2030",
                "card_type": "Visa",
                "issuer_country": "RU",
            },
        },
        "confirmation": {
            "type": "redirect",
            "confirmation_url": "https://yookassa.ru/checkout/abcdef",
        },
        "merchant_customer_id": "ext-customer-77",
        # receipt — mixed FISCAL + PII; allow-list applied to subtree
        "receipt": {
            "id": "rcpt-001",
            "type": "payment",
            "status": "succeeded",
            "tax_system_code": 2,
            "registered_at": "2026-04-30T10:15:35.000Z",
            "fiscal_provider_id": "ofd-yandex-001",
            "fiscal_document_number": "0000123456",
            "fiscal_storage_number": "9999987654321111",
            "fiscal_attribute": "0123456789",
            "items": [
                {
                    "description": "Пополнение баланса",
                    "quantity": "1.00",
                    "amount": {"value": "517.50", "currency": "RUB"},
                    "vat_code": 1,
                    "payment_subject": "service",
                    "payment_mode": "full_prepayment",
                }
            ],
            # PII subtree — must be dropped
            "customer": {
                "full_name": "Иванов Иван Иванович",
                "inn": "771234567890",
                "email": "user@example.com",
                "phone": "+79001234567",
            },
        },
    }


# ───── FISCAL retention (positive assertions) ───────────────────


def test_fiscal_top_level_retained():
    sample = _sample_payload()
    result = extract_persistable_metadata(sample)

    for key in FISCAL_TOP_LEVEL:
        assert key in result, f"FISCAL top-level field {key!r} dropped unexpectedly"
        assert result[key] == sample[key], f"FISCAL value mismatch for {key!r}"


def test_receipt_fiscal_fields_retained():
    sample = _sample_payload()
    result = extract_persistable_metadata(sample)

    assert "receipt" in result, "receipt subtree dropped despite having FISCAL content"
    receipt_result = result["receipt"]
    receipt_sample = sample["receipt"]

    for key in RECEIPT_FISCAL_FIELDS:
        if key in receipt_sample:
            assert key in receipt_result, f"receipt.{key} dropped unexpectedly"
            assert receipt_result[key] == receipt_sample[key]


def test_roundtrip_metadata_retained():
    sample = _sample_payload()
    result = extract_persistable_metadata(sample)

    for key in ROUNDTRIP_TOP_LEVEL:
        assert key in result, f"ROUNDTRIP field {key!r} dropped"
        assert result[key] == sample[key]


def test_transport_test_flag_retained():
    sample = _sample_payload()
    result = extract_persistable_metadata(sample)

    for key in TRANSPORT_TOP_LEVEL:
        assert key in result, f"TRANSPORT field {key!r} dropped"
        assert result[key] == sample[key]


# ───── Drops (negative assertions) ──────────────────────────────


def test_recipient_subtree_dropped():
    sample = _sample_payload()
    result = extract_persistable_metadata(sample)

    assert "recipient" not in result


def test_payment_method_subtree_dropped():
    sample = _sample_payload()
    result = extract_persistable_metadata(sample)

    assert "payment_method" not in result


def test_confirmation_subtree_dropped():
    sample = _sample_payload()
    result = extract_persistable_metadata(sample)

    assert "confirmation" not in result


def test_merchant_customer_id_dropped():
    sample = _sample_payload()
    result = extract_persistable_metadata(sample)

    assert "merchant_customer_id" not in result


def test_receipt_customer_pii_dropped():
    sample = _sample_payload()
    result = extract_persistable_metadata(sample)

    assert "customer" not in result.get("receipt", {})


# ───── Edge cases ───────────────────────────────────────────────


def test_empty_dict_returns_empty_dict():
    assert extract_persistable_metadata({}) == {}


def test_none_returns_empty_dict():
    assert extract_persistable_metadata(None) == {}


def test_non_dict_returns_empty_dict():
    # Defensive: caller bug → empty dict, not crash. Cast through Any to
    # bypass static type narrowing of the param.
    payload: Any = [1, 2, 3]
    assert extract_persistable_metadata(payload) == {}


def test_receipt_none_does_not_raise():
    # `receipt` may be None when payment has no fiscal receipt registered.
    result = extract_persistable_metadata({"id": "yk-1", "receipt": None})
    assert "id" in result
    assert "receipt" not in result


def test_receipt_empty_dict_dropped_from_result():
    # Empty receipt projection (no FISCAL fields present) → key is absent.
    # Documents intentional choice: empty receipt dict is not surfaced.
    result = extract_persistable_metadata({"id": "yk-1", "receipt": {}})
    assert "id" in result
    assert "receipt" not in result


def test_receipt_only_pii_dropped_from_result():
    # Receipt with ONLY PII (no FISCAL) → entire subtree dropped from result.
    payload = {
        "id": "yk-1",
        "receipt": {
            "customer": {"email": "x@y.z", "phone": "+1"},
        },
    }
    result = extract_persistable_metadata(payload)
    assert "id" in result
    assert "receipt" not in result


# ───── Immutability ─────────────────────────────────────────────


def test_input_not_mutated():
    sample = _sample_payload()
    sample_snapshot = _sample_payload()  # independent reference

    result = extract_persistable_metadata(sample)
    result["amount"] = {"value": "0.00", "currency": "RUB"}
    result["receipt"]["items"] = []

    # Sample's top-level still intact
    assert sample["amount"] == sample_snapshot["amount"]
    # Sample's nested receipt.items still intact (we mutated result["receipt"]
    # which is the same dict object as the projection — so this asserts that
    # the projection does NOT share references for receipt subtree mutations
    # to leak back into sample. NOTE: the current implementation builds a
    # new receipt dict via comprehension, so reference-share is one level
    # deep. items list IS shared (no deep copy). This documents the
    # contract: top-level new dict, nested values shared.
    # → for items to remain unchanged we must verify against pre-mutation
    # snapshot.
    assert sample["receipt"]["items"] == sample_snapshot["receipt"]["items"]


def test_result_is_new_dict_object():
    sample = _sample_payload()
    result = extract_persistable_metadata(sample)
    assert result is not sample
