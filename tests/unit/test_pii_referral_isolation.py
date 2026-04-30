"""BL-050: ReferralItem must not leak PII (first_name/last_name) of OTHER
users.

`GET /api/users/me/referrals` returns a list of `ReferralItem` representing
referrals of the current user. Those referrals are *other* users — exposing
their `first_name`/`last_name` is a ФЗ-152 violation (audit MED-6,
PII_AUDIT_2026-04-28 § 2.2 line 115).

Self-context schemas (`UserResponse` for `/api/users/me`) are unaffected —
own first_name is not a leak.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.api.routers.users import ReferralItem, ReferralStatsResponse


class TestReferralItemPIIIsolation:
    """ReferralItem schema must not have first_name/last_name fields."""

    def test_referral_item_has_no_first_name_field(self) -> None:
        """BL-050: first_name must NOT be a field on ReferralItem."""
        assert "first_name" not in ReferralItem.model_fields, (
            "first_name leaked в ReferralItem (BL-050 regression)"
        )

    def test_referral_item_has_no_last_name_field(self) -> None:
        """BL-050: last_name must NOT be a field on ReferralItem."""
        assert "last_name" not in ReferralItem.model_fields, (
            "last_name leaked в ReferralItem (BL-050 regression)"
        )

    def test_referral_item_serialised_dict_has_no_pii_keys(self) -> None:
        """Even with extra-allowed schemas, dumped dict must have no PII keys."""
        item = ReferralItem(
            id=42,
            username="bob",
            created_at="2026-04-30T00:00:00Z",
            is_active=True,
        )
        dumped = item.model_dump()
        assert "first_name" not in dumped
        assert "last_name" not in dumped

    def test_referral_item_rejects_unknown_first_name_kwarg(self) -> None:
        """Pydantic should ignore (default) или reject unknown first_name kwarg."""
        # Pydantic default is to ignore unknown fields, but model_dump won't
        # emit them. Either behaviour satisfies the BL-050 contract — what
        # matters is the OUT shape.
        try:
            item = ReferralItem(
                id=1,
                username="x",
                created_at="2026-04-30T00:00:00Z",
                is_active=False,
                first_name="ShouldBeIgnored",  # type: ignore[call-arg]
            )
        except ValidationError:
            return  # strict mode rejected — also fine
        assert "first_name" not in item.model_dump()

    def test_referral_item_required_fields(self) -> None:
        """Sanity: schema accepts the documented PII-safe shape."""
        item = ReferralItem(
            id=7,
            username=None,
            created_at="2026-04-30T00:00:00Z",
            is_active=False,
        )
        dumped = item.model_dump()
        assert dumped == {
            "id": 7,
            "username": None,
            "created_at": "2026-04-30T00:00:00Z",
            "is_active": False,
        }


class TestReferralStatsResponseShape:
    """Top-level response wrapper must inherit the leak-free ReferralItem."""

    def test_referral_stats_response_referrals_are_pii_safe(self) -> None:
        """When ReferralStatsResponse is dumped, no first_name/last_name appears."""
        from decimal import Decimal

        resp = ReferralStatsResponse(
            referral_code="ABC",
            referral_link="https://t.me/RekHarborBot?start=ABC",
            total_referrals=2,
            active_referrals=1,
            total_earned_rub=Decimal("100.00"),
            referrals=[
                ReferralItem(
                    id=1,
                    username="alice",
                    created_at="2026-04-30T00:00:00Z",
                    is_active=True,
                ),
                ReferralItem(
                    id=2,
                    username=None,
                    created_at="2026-04-29T00:00:00Z",
                    is_active=False,
                ),
            ],
        )
        dumped = resp.model_dump()
        for ref in dumped["referrals"]:
            assert "first_name" not in ref
            assert "last_name" not in ref


@pytest.mark.parametrize(
    "leaky_field",
    ["first_name", "last_name", "telegram_id"],
)
def test_referral_item_field_blacklist(leaky_field: str) -> None:
    """Parametrised guard: explicitly forbid known leak vectors.

    `telegram_id` was previously declared in the frontend `ReferralItem` type
    but never returned by the backend. We keep it on the blacklist so any
    future "let's just add telegram_id" PR fails this test.
    """
    assert leaky_field not in ReferralItem.model_fields, (
        f"{leaky_field} в ReferralItem — PII leak (BL-050)"
    )
