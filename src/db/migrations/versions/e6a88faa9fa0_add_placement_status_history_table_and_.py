"""add placement_status_history table and drop ord_blocked enum

Revision ID: e6a88faa9fa0
Revises: 0001_initial_schema
Create Date: 2026-04-27 07:01:50.867405

Implements Phase 2 § 2.B.0 Decisions 1 (state-machine spec) + 10 (PK).
- placement_status_history: autoincrement BIGINT PK, NOT (placement_id, status) UNIQUE,
  index on (placement_id, changed_at DESC) for timeline queries.
- Drop ord_blocked from placementstatus enum (declared in DB enum
  but not in ORM model — Decision 1 schema cleanup).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "e6a88faa9fa0"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create placement_status_history
    op.create_table(
        "placement_status_history",
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column(
            "placement_id",
            sa.Integer(),
            sa.ForeignKey("placement_requests.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "from_status",
            postgresql.ENUM(name="placementstatus", create_type=False),
            nullable=True,
        ),
        sa.Column(
            "to_status",
            postgresql.ENUM(name="placementstatus", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "actor_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("reason", sa.String(length=64), nullable=False),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
    )
    op.create_index(
        "ix_psh_placement_changed",
        "placement_status_history",
        ["placement_id", sa.text("changed_at DESC")],
    )

    # 2. Drop ord_blocked from placementstatus enum (Decision 1).
    # PostgreSQL does not support DROP VALUE FROM ENUM directly; rename the
    # old type, create a new type without ord_blocked, migrate every column
    # that uses it, then drop the old type. Safe because no rows reference
    # ord_blocked in pre-prod (verified via backfill audit).
    #
    # The placement_escrow_integrity CHECK constraint references
    # 'escrow'::placementstatus literal; drop it before the type swap
    # (it cannot be re-typed across the rename) and recreate after.
    op.execute(
        "ALTER TABLE placement_requests DROP CONSTRAINT placement_escrow_integrity"
    )
    op.execute("ALTER TYPE placementstatus RENAME TO placementstatus_old")
    op.execute(
        """
        CREATE TYPE placementstatus AS ENUM (
            'pending_owner', 'counter_offer', 'pending_payment', 'escrow',
            'published', 'completed', 'failed', 'failed_permissions',
            'refunded', 'cancelled'
        )
        """
    )
    op.execute(
        """
        ALTER TABLE placement_requests
        ALTER COLUMN status TYPE placementstatus
        USING status::text::placementstatus
        """
    )
    op.execute(
        """
        ALTER TABLE placement_status_history
        ALTER COLUMN from_status TYPE placementstatus
        USING from_status::text::placementstatus
        """
    )
    op.execute(
        """
        ALTER TABLE placement_status_history
        ALTER COLUMN to_status TYPE placementstatus
        USING to_status::text::placementstatus
        """
    )
    op.execute("DROP TYPE placementstatus_old")
    op.execute(
        """
        ALTER TABLE placement_requests
        ADD CONSTRAINT placement_escrow_integrity
        CHECK (
            status <> 'escrow'::placementstatus
            OR (escrow_transaction_id IS NOT NULL AND final_price IS NOT NULL)
        )
        """
    )


def downgrade() -> None:
    # 1. Recreate ord_blocked enum value.
    op.execute(
        "ALTER TABLE placement_requests DROP CONSTRAINT placement_escrow_integrity"
    )
    op.execute("ALTER TYPE placementstatus RENAME TO placementstatus_new")
    op.execute(
        """
        CREATE TYPE placementstatus AS ENUM (
            'pending_owner', 'counter_offer', 'pending_payment', 'escrow',
            'published', 'completed', 'failed', 'failed_permissions',
            'refunded', 'cancelled', 'ord_blocked'
        )
        """
    )
    op.execute(
        """
        ALTER TABLE placement_requests
        ALTER COLUMN status TYPE placementstatus
        USING status::text::placementstatus
        """
    )
    op.execute(
        """
        ALTER TABLE placement_status_history
        ALTER COLUMN from_status TYPE placementstatus
        USING from_status::text::placementstatus
        """
    )
    op.execute(
        """
        ALTER TABLE placement_status_history
        ALTER COLUMN to_status TYPE placementstatus
        USING to_status::text::placementstatus
        """
    )
    op.execute("DROP TYPE placementstatus_new")
    op.execute(
        """
        ALTER TABLE placement_requests
        ADD CONSTRAINT placement_escrow_integrity
        CHECK (
            status <> 'escrow'::placementstatus
            OR (escrow_transaction_id IS NOT NULL AND final_price IS NOT NULL)
        )
        """
    )

    # 2. Drop placement_status_history.
    op.drop_index("ix_psh_placement_changed", table_name="placement_status_history")
    op.drop_table("placement_status_history")
