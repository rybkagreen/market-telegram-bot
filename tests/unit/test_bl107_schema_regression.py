"""BL-107 schema regression tests — TelegramChat blogger registry fields.

Validates Phase B.1 schema additions per ФЗ-303 / BL-107:
- 7 new fields on TelegramChat
- New BloggerRegistryVerificationMethod enum (2 values)
- FK constraint blogger_registry_verified_by_admin_id → users.id с ondelete SET NULL

Tests are pure ORM / introspection — no DB connection required.
"""

from datetime import UTC, datetime

from sqlalchemy.orm import RelationshipProperty

from src.core.enums.blogger_registry import BloggerRegistryVerificationMethod
from src.db.models.telegram_chat import TelegramChat


class TestBloggerRegistryVerificationMethodEnum:
    """BloggerRegistryVerificationMethod enum contract (BL-107)."""

    def test_enum_has_exactly_two_values(self):
        """Enum must have exactly TRUSTCHANNELBOT_ADMIN + MANUAL_EVIDENCE — nothing else."""
        values = {m.value for m in BloggerRegistryVerificationMethod}
        assert values == {"trustchannelbot_admin", "manual_evidence"}

    def test_trustchannelbot_admin_value(self):
        """TRUSTCHANNELBOT_ADMIN serializes к exact lowercase string."""
        assert (
            BloggerRegistryVerificationMethod.TRUSTCHANNELBOT_ADMIN.value == "trustchannelbot_admin"
        )

    def test_manual_evidence_value(self):
        """MANUAL_EVIDENCE serializes к exact lowercase string."""
        assert BloggerRegistryVerificationMethod.MANUAL_EVIDENCE.value == "manual_evidence"

    def test_enum_is_str_enum(self):
        """Members must be str subclass (StrEnum) для JSON serialization compatibility."""
        assert isinstance(BloggerRegistryVerificationMethod.TRUSTCHANNELBOT_ADMIN, str)


class TestTelegramChatBloggerRegistryFields:
    """7 new TelegramChat fields per BL-107 Phase B.1 design."""

    def test_is_blogger_registry_verified_present(self):
        """is_blogger_registry_verified column exists и NOT nullable."""
        col = TelegramChat.__table__.columns["is_blogger_registry_verified"]
        assert col.nullable is False
        assert col.default is not None or col.server_default is not None

    def test_blogger_registry_verified_at_present(self):
        """blogger_registry_verified_at exists и nullable."""
        col = TelegramChat.__table__.columns["blogger_registry_verified_at"]
        assert col.nullable is True

    def test_blogger_registry_application_number_present(self):
        """blogger_registry_application_number — String(64) nullable."""
        col = TelegramChat.__table__.columns["blogger_registry_application_number"]
        assert col.nullable is True
        assert col.type.length == 64

    def test_blogger_registry_verified_by_admin_id_fk(self):
        """blogger_registry_verified_by_admin_id FK → users.id с ondelete SET NULL."""
        col = TelegramChat.__table__.columns["blogger_registry_verified_by_admin_id"]
        assert col.nullable is True
        fks = list(col.foreign_keys)
        assert len(fks) == 1
        assert fks[0].column.table.name == "users"
        assert fks[0].column.name == "id"
        assert fks[0].ondelete == "SET NULL"

    def test_blogger_registry_verification_method_enum(self):
        """blogger_registry_verification_method maps к BloggerRegistryVerificationMethod."""
        col = TelegramChat.__table__.columns["blogger_registry_verification_method"]
        assert col.nullable is True
        # Enum inferred from Mapped[Enum] — exposes enum class on column.type
        assert col.type.enum_class is BloggerRegistryVerificationMethod

    def test_member_count_at_verification_present(self):
        """member_count_at_verification exists, nullable int."""
        col = TelegramChat.__table__.columns["member_count_at_verification"]
        assert col.nullable is True

    def test_last_blogger_registry_check_at_present(self):
        """last_blogger_registry_check_at exists, nullable timestamp."""
        col = TelegramChat.__table__.columns["last_blogger_registry_check_at"]
        assert col.nullable is True


class TestTelegramChatORMInstance:
    """ORM-level instantiation — fields accept correct types."""

    def test_default_unverified_state(self):
        """New TelegramChat без explicit verification fields defaults безопасно."""
        chat = TelegramChat(
            telegram_id=12345,
            username="test_channel",
            title="Test Channel",
            owner_id=1,
        )
        # Python-side default — server_default applies в DB only
        assert (
            chat.is_blogger_registry_verified is False or chat.is_blogger_registry_verified is None
        )
        assert chat.blogger_registry_verified_at is None
        assert chat.blogger_registry_application_number is None
        assert chat.blogger_registry_verified_by_admin_id is None
        assert chat.blogger_registry_verification_method is None
        assert chat.member_count_at_verification is None
        assert chat.last_blogger_registry_check_at is None

    def test_verified_state_population(self):
        """All fields accept expected types."""
        now = datetime.now(UTC)
        chat = TelegramChat(
            telegram_id=12345,
            username="big_channel",
            title="Big Channel",
            owner_id=1,
            is_blogger_registry_verified=True,
            blogger_registry_verified_at=now,
            blogger_registry_application_number="GU-2026-12345",
            blogger_registry_verified_by_admin_id=99,
            blogger_registry_verification_method=BloggerRegistryVerificationMethod.TRUSTCHANNELBOT_ADMIN,
            member_count_at_verification=15000,
            last_blogger_registry_check_at=now,
        )
        assert chat.is_blogger_registry_verified is True
        assert chat.blogger_registry_verified_at == now
        assert chat.blogger_registry_application_number == "GU-2026-12345"
        assert chat.blogger_registry_verified_by_admin_id == 99
        assert (
            chat.blogger_registry_verification_method
            == BloggerRegistryVerificationMethod.TRUSTCHANNELBOT_ADMIN
        )
        assert chat.member_count_at_verification == 15000
        assert chat.last_blogger_registry_check_at == now

    def test_manual_evidence_method_accepted(self):
        """Manual evidence verification method assignable."""
        chat = TelegramChat(
            telegram_id=12345,
            username="test_channel",
            title="Test",
            owner_id=1,
            blogger_registry_verification_method=BloggerRegistryVerificationMethod.MANUAL_EVIDENCE,
        )
        assert (
            chat.blogger_registry_verification_method
            == BloggerRegistryVerificationMethod.MANUAL_EVIDENCE
        )

    def test_existing_relationships_unaffected(self):
        """Existing relationships (owner, channel_settings, etc.) still present."""
        rel_names = {
            r.key
            for r in TelegramChat.__mapper__.relationships
            if isinstance(r, RelationshipProperty)
        }
        # Sanity — Phase B.1 only adds columns; no new relationships
        assert "owner" in rel_names
        assert "channel_settings" in rel_names
        assert "channel_mediakit" in rel_names
        assert "placement_requests" in rel_names
