"""add_dispute_enum_values

Revision ID: s32a001_add_dispute_enums
Revises: s31a001_document_uploads
Create Date: 2026-04-09 12:00:00.000000

Expands PostgreSQL enum types for disputes to support frontend values:
- disute_reason: adds not_published, wrong_time, wrong_text, early_deletion, other
- dispute_status: adds closed
- dispute_resolution: adds full_refund, partial_refund, no_refund, warning
"""

from alembic import op

revision = "s32a001_add_dispute_enums"
down_revision = "s31a001_document_uploads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Expand PostgreSQL enum types with frontend-compatible values."""

    # Expand disputereason
    op.execute("ALTER TYPE disputereason ADD VALUE IF NOT EXISTS 'not_published'")
    op.execute("ALTER TYPE disputereason ADD VALUE IF NOT EXISTS 'wrong_time'")
    op.execute("ALTER TYPE disputereason ADD VALUE IF NOT EXISTS 'wrong_text'")
    op.execute("ALTER TYPE disputereason ADD VALUE IF NOT EXISTS 'early_deletion'")
    op.execute("ALTER TYPE disputereason ADD VALUE IF NOT EXISTS 'other'")

    # Expand disputestatus
    op.execute("ALTER TYPE disputestatus ADD VALUE IF NOT EXISTS 'closed'")

    # Expand disputeresolution
    op.execute("ALTER TYPE disputeresolution ADD VALUE IF NOT EXISTS 'full_refund'")
    op.execute("ALTER TYPE disputeresolution ADD VALUE IF NOT EXISTS 'partial_refund'")
    op.execute("ALTER TYPE disputeresolution ADD VALUE IF NOT EXISTS 'no_refund'")
    op.execute("ALTER TYPE disputeresolution ADD VALUE IF NOT EXISTS 'warning'")


def downgrade() -> None:
    """
    PostgreSQL does not support removing enum values.
    To downgrade, you would need to recreate the enum type without the new values.
    This is intentionally left as a no-op to avoid data loss.
    """
    pass
