"""Structure invariants для src/utils/pii_keys.py canonical scrub list.

Drift between Sentry inits impossible by construction (both import
from here). These tests verify canonical list itself remains structurally
sound — count correct, no duplicates, deterministic order, critical PII
categories present.
"""
from __future__ import annotations

from src.utils.pii_keys import SENTRY_PII_KEYS


def test_count_eighteen_keys() -> None:
    """4 auth + 5 identity + 6 documents + 3 payment = 18."""
    assert len(SENTRY_PII_KEYS) == 18


def test_no_duplicates() -> None:
    assert len(set(SENTRY_PII_KEYS)) == len(SENTRY_PII_KEYS)


def test_immutable_tuple() -> None:
    assert isinstance(SENTRY_PII_KEYS, tuple)


def test_all_strings_lowercase_no_whitespace() -> None:
    for key in SENTRY_PII_KEYS:
        assert isinstance(key, str)
        assert key == key.lower(), f"non-lowercase key: {key}"
        assert " " not in key, f"whitespace в key: {key}"


def test_critical_auth_keys_present() -> None:
    for key in ("authorization", "password", "token", "x-api-key"):
        assert key in SENTRY_PII_KEYS


def test_critical_identity_keys_present() -> None:
    """ФЗ-152 critical PII categories."""
    for key in ("email", "phone", "full_name", "inn", "address"):
        assert key in SENTRY_PII_KEYS


def test_critical_payment_keys_present() -> None:
    for key in ("bank_account", "bank_corr_account", "yoomoney_wallet"):
        assert key in SENTRY_PII_KEYS


def test_critical_document_keys_present() -> None:
    for key in (
        "passport_number",
        "passport_series",
        "passport_issued_by",
        "passport_scan_file_id",
        "inn_scan_file_id",
        "file_id",
    ):
        assert key in SENTRY_PII_KEYS
