"""Canonical YooKassa webhook payload projection для at-rest persistence.

Single source of truth для filtering YooKassa webhook payloads перед
записью в ``YookassaPayment.yookassa_metadata`` (JSONB column).

Categorization (informational; allow-list applied per category):

* **FISCAL (16 top-level + 11 receipt fields):** must retain for
  accounting (УСН/КУДиР), reconciliation, dispute resolution. Includes
  amounts, timestamps, status flags, fiscal receipt details, banking
  authorization details. Persisted to ``yookassa_metadata`` JSONB.
* **PII:** customer personal data — ``receipt.customer.{full_name,
  inn, email, phone}``, card pan-fragments (``payment_method.card.
  first6/last4``), ``yoo_money.account_number``. MUST NOT persist
  post-processing per ФЗ-152 minimization.
* **TRANSPORT:** YooKassa-internal infra fields — ``recipient.{account_id,
  gateway_id}``, ``payment_method.id``, ``confirmation`` subtree
  (consumed pre-success). Low retention value; drop.
* **ROUNDTRIP:** our own application metadata sent to YooKassa и echoed
  back в ``metadata`` field (``user_id``, ``desired_balance``). Retain;
  это application-level state, not PII.

Note: ``payment_method.type`` (e.g. ``bank_card``, ``sbp``) is already
extracted to ``YookassaPayment.payment_method_type`` normalized column
at write time; the entire ``payment_method`` subtree is therefore
dropped from JSONB to avoid duplication and to prevent retention of PCI
fragments. Same applies to ``receipt.id`` → ``YookassaPayment.receipt_id``.

Adding a new field
------------------
1. Locate the field in the YooKassa webhook payload structure.
2. Categorize per definitions above (FISCAL / PII / TRANSPORT / ROUNDTRIP).
3. Top-level field → add to ``FISCAL_TOP_LEVEL`` / ``ROUNDTRIP_TOP_LEVEL``
   / ``TRANSPORT_TOP_LEVEL`` (alphabetical within category).
4. Field within ``receipt`` → add to ``RECEIPT_FISCAL_FIELDS`` if FISCAL,
   leave out otherwise (absence = drop).
5. Add a row to the test sample in ``tests/unit/utils/test_yookassa_payload.py``
   with both retained-positive and dropped-negative assertions.
"""

from __future__ import annotations

from typing import Any

# Top-level FISCAL fields (retain entirely — values opaque to projection).
FISCAL_TOP_LEVEL: frozenset[str] = frozenset({
    "amount",
    "authorization_details",
    "cancellation_details",
    "captured_at",
    "created_at",
    "deal",
    "description",
    "expires_at",
    "id",
    "income_amount",
    "paid",
    "receipt_registration",
    "refundable",
    "refunded_amount",
    "status",
    "transfers",
})

# `receipt` subtree allow-list (mixed PII + FISCAL под one key).
# Customer subtree (full_name/inn/email/phone) excluded — PII.
RECEIPT_FISCAL_FIELDS: frozenset[str] = frozenset({
    "fiscal_attribute",
    "fiscal_document_number",
    "fiscal_provider_id",
    "fiscal_storage_number",
    "id",
    "items",
    "registered_at",
    "status",
    "tax_system_code",
    "type",
})

# Roundtrip — our own application metadata.
ROUNDTRIP_TOP_LEVEL: frozenset[str] = frozenset({
    "metadata",
})

# Transport — internal infra fields retained for diagnostic value.
TRANSPORT_TOP_LEVEL: frozenset[str] = frozenset({
    "test",
})


def extract_persistable_metadata(payload: dict[str, Any] | None) -> dict[str, Any]:
    """Project a YooKassa webhook payload to its persistable subset.

    Drops PII (customer email/phone/inn/full_name, card pan-fragments,
    yoo_money account number) and low-value transport fields
    (``recipient`` infra IDs, ``payment_method`` subtree, ``confirmation``
    subtree). Retains fiscal data (amounts, items, timestamps, tax codes,
    fiscal receipt fields, banking auth details) and our roundtrip
    metadata.

    Returns a new dict; does not mutate the input.
    Defensive against non-dict input (returns empty dict).
    """
    if not isinstance(payload, dict):
        return {}

    result: dict[str, Any] = {}

    retained_top = FISCAL_TOP_LEVEL | ROUNDTRIP_TOP_LEVEL | TRANSPORT_TOP_LEVEL
    for key in retained_top:
        if key in payload:
            result[key] = payload[key]

    receipt = payload.get("receipt")
    if isinstance(receipt, dict):
        receipt_projection = {k: v for k, v in receipt.items() if k in RECEIPT_FISCAL_FIELDS}
        if receipt_projection:
            result["receipt"] = receipt_projection

    # `recipient`, `payment_method`, `confirmation`, `merchant_customer_id`
    # — entire subtrees dropped (absence-from-allow-list = drop).

    return result
