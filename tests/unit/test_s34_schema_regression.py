"""
S-34 regression tests — Pydantic schema ↔ SQLAlchemy model mismatches.

These tests validate that the fixed schemas can round-trip correctly with
the actual field names present on the ORM models. They run without DB.
"""

from datetime import datetime, timezone
from decimal import Decimal

import pytest


class TestCampaignResponseSTOP1:
    """Regression: CampaignResponse must not crash when validated from PlacementRequest."""

    def test_campaign_response_fields_match_placement_request(self):
        """CampaignResponse must use model fields: ad_text, meta_json, proposed_schedule."""
        from src.api.routers.campaigns import CampaignResponse

        now = datetime.now(timezone.utc)
        resp = CampaignResponse(
            id=1,
            ad_text="Test ad text",
            status="pending_owner",
            meta_json={"key": "value"},
            proposed_schedule=now,
            created_at=now,
            updated_at=now,
        )
        assert resp.ad_text == "Test ad text"
        assert resp.meta_json == {"key": "value"}
        assert resp.proposed_schedule == now

    def test_campaign_response_no_title_field(self):
        """CampaignResponse must NOT have a title field (caused STOP-1 crash)."""
        from src.api.routers.campaigns import CampaignResponse

        assert not hasattr(CampaignResponse.model_fields, "title"), (
            "CampaignResponse.title was removed — it does not exist on PlacementRequest"
        )
        assert "title" not in CampaignResponse.model_fields

    def test_campaign_response_no_text_field(self):
        """CampaignResponse must NOT have a 'text' field (renamed to ad_text)."""
        from src.api.routers.campaigns import CampaignResponse

        assert "text" not in CampaignResponse.model_fields

    def test_campaign_response_no_filters_json_field(self):
        """CampaignResponse must NOT have 'filters_json' (renamed to meta_json)."""
        from src.api.routers.campaigns import CampaignResponse

        assert "filters_json" not in CampaignResponse.model_fields

    def test_campaign_response_no_scheduled_at_field(self):
        """CampaignResponse must NOT have 'scheduled_at' (renamed to proposed_schedule)."""
        from src.api.routers.campaigns import CampaignResponse

        assert "scheduled_at" not in CampaignResponse.model_fields

    def test_campaign_response_datetime_types(self):
        """CampaignResponse.created_at and updated_at must be datetime, not str."""
        from src.api.routers.campaigns import CampaignResponse

        created_at_annotation = CampaignResponse.model_fields["created_at"].annotation
        updated_at_annotation = CampaignResponse.model_fields["updated_at"].annotation
        assert created_at_annotation is datetime, f"created_at must be datetime, got {created_at_annotation}"
        assert updated_at_annotation is datetime, f"updated_at must be datetime, got {updated_at_annotation}"

    def test_campaign_response_from_orm_like_object(self):
        """CampaignResponse.model_validate must succeed on an ORM-like object."""
        from src.api.routers.campaigns import CampaignResponse

        class FakePlacementRequest:
            id = 42
            ad_text = "Some ad"
            status = "pending_owner"
            meta_json = None
            proposed_schedule = None
            created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
            updated_at = datetime(2026, 1, 2, tzinfo=timezone.utc)

        resp = CampaignResponse.model_validate(FakePlacementRequest())
        assert resp.id == 42
        assert resp.ad_text == "Some ad"
        assert resp.status == "pending_owner"


class TestCampaignUpdateSTOP1:
    """Regression: CampaignUpdate.model_dump must return correct field names for repo.update()."""

    def test_campaign_update_field_names(self):
        """CampaignUpdate must use ad_text, meta_json, proposed_schedule."""
        from src.api.routers.campaigns import CampaignUpdate

        assert "ad_text" in CampaignUpdate.model_fields
        assert "meta_json" in CampaignUpdate.model_fields
        assert "proposed_schedule" in CampaignUpdate.model_fields

        assert "title" not in CampaignUpdate.model_fields
        assert "text" not in CampaignUpdate.model_fields
        assert "filters_json" not in CampaignUpdate.model_fields
        assert "scheduled_at" not in CampaignUpdate.model_fields

    def test_campaign_update_model_dump_returns_correct_keys(self):
        """model_dump(exclude_unset=True) must return keys matching PlacementRequest attrs."""
        from datetime import datetime, timezone

        from src.api.routers.campaigns import CampaignUpdate

        update = CampaignUpdate(ad_text="New text", meta_json={"x": 1})
        dumped = update.model_dump(exclude_unset=True)

        assert "ad_text" in dumped
        assert "meta_json" in dumped
        assert "proposed_schedule" not in dumped  # not set
        assert "filters_json" not in dumped  # old name must not appear


class TestChannelResponseSTOP2:
    """Regression: ChannelResponse constructors must include owner_id and created_at."""

    def test_channel_response_requires_owner_id(self):
        """ChannelResponse.owner_id must be a required field."""
        from src.api.schemas.channel import ChannelResponse

        field = ChannelResponse.model_fields["owner_id"]
        assert field.is_required(), "owner_id must be required — no default value"

    def test_channel_response_requires_created_at(self):
        """ChannelResponse.created_at must be a required field."""
        from src.api.schemas.channel import ChannelResponse

        field = ChannelResponse.model_fields["created_at"]
        assert field.is_required(), "created_at must be required — no default value"

    def test_channel_response_raises_without_owner_id(self):
        """ChannelResponse construction must fail without owner_id (replicates old crash)."""
        from pydantic import ValidationError

        from src.api.schemas.channel import ChannelResponse

        with pytest.raises(ValidationError):
            ChannelResponse(
                id=1,
                telegram_id=123456789,
                username="test_channel",
                title="Test Channel",
                # owner_id intentionally omitted
                created_at="2026-01-01T00:00:00",
            )

    def test_channel_response_raises_without_created_at(self):
        """ChannelResponse construction must fail without created_at (replicates old crash)."""
        from pydantic import ValidationError

        from src.api.schemas.channel import ChannelResponse

        with pytest.raises(ValidationError):
            ChannelResponse(
                id=1,
                telegram_id=123456789,
                username="test_channel",
                title="Test Channel",
                owner_id=7,
                # created_at intentionally omitted
            )

    def test_channel_response_succeeds_with_all_required_fields(self):
        """ChannelResponse must succeed when all required fields are provided."""
        from src.api.schemas.channel import ChannelResponse

        resp = ChannelResponse(
            id=1,
            telegram_id=123456789,
            username="test_channel",
            title="Test Channel",
            owner_id=7,
            created_at="2026-01-01T00:00:00",
        )
        assert resp.owner_id == 7
        assert resp.created_at == "2026-01-01T00:00:00"


class TestChannelSettingsResponseP21:
    """Regression: ChannelSettingsResponse must NOT have from_attributes=True."""

    def test_channel_settings_response_no_from_attributes(self):
        """ChannelSettingsResponse.model_config must not have from_attributes=True."""
        from src.api.routers.channel_settings import ChannelSettingsResponse

        config = ChannelSettingsResponse.model_config
        assert not config.get("from_attributes", False), (
            "from_attributes=True removed: schema is always constructed manually, "
            "never via model_validate(orm_object)"
        )


class TestUserResponseP23:
    """Regression: UserResponse.first_name must be non-optional."""

    def test_user_response_first_name_required(self):
        """UserResponse.first_name must be str (not Optional[str])."""
        from src.api.schemas.user import UserResponse

        field = UserResponse.model_fields["first_name"]
        assert field.is_required(), "first_name must be required — model User.first_name is NOT NULL"

    def test_user_response_first_name_annotation(self):
        """UserResponse.first_name annotation must be str, not str | None."""
        from src.api.schemas.user import UserResponse

        annotation = UserResponse.model_fields["first_name"].annotation
        assert annotation is str, f"Expected str, got {annotation}"


class TestPlacementCreateRequestP31:
    """Regression: proposed_price must be Decimal to match model."""

    def test_proposed_price_accepts_decimal_string(self):
        """PlacementCreateRequest must accept Decimal-compatible JSON number."""
        from datetime import datetime, timezone

        from src.api.routers.placements import PlacementCreateRequest

        req = PlacementCreateRequest(
            channel_id=1,
            proposed_price=Decimal("1500.00"),
            ad_text="Test ad text here",
            proposed_schedule=datetime.now(timezone.utc).isoformat(),
        )
        assert isinstance(req.proposed_price, Decimal)
        assert req.proposed_price == Decimal("1500.00")

    def test_proposed_price_coerces_integer(self):
        """PlacementCreateRequest.proposed_price must coerce int to Decimal."""
        from datetime import datetime, timezone

        from src.api.routers.placements import PlacementCreateRequest

        req = PlacementCreateRequest(
            channel_id=1,
            proposed_price=1000,
            ad_text="Test ad text here",
            proposed_schedule=datetime.now(timezone.utc).isoformat(),
        )
        assert isinstance(req.proposed_price, Decimal)
