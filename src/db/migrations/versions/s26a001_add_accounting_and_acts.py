"""add_accounting_and_acts

Revision ID: s26a001_add_accounting_acts
Revises: a1b2c3d4e5f6
Create Date: 2026-04-03 16:00:00.000000

Auto-generated additive migration for Sprint A.1. SAFE FOR PROD.
Adds: document_counters table, acts table.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "s26a001_add_accounting_acts"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ─── Document Counters ───────────────────────────────────────────
    op.create_table(
        "document_counters",
        sa.Column("prefix", sa.String(4), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("current_seq", sa.Integer(), server_default="0", nullable=False),
        sa.PrimaryKeyConstraint("prefix", "year"),
    )

    # ─── Acts ────────────────────────────────────────────────────────
    op.create_table(
        "acts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("placement_request_id", sa.Integer(), nullable=False),
        sa.Column("act_number", sa.String(20), nullable=False),
        sa.Column(
            "act_date", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("pdf_path", sa.String(255), nullable=False),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("meta_json", JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["placement_request_id"],
            ["placement_requests.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_acts_placement_request_id", "acts", ["placement_request_id"], unique=False)
    op.create_index("ix_acts_act_number", "acts", ["act_number"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_acts_act_number", table_name="acts")
    op.drop_index("ix_acts_placement_request_id", table_name="acts")
    op.drop_table("acts")
    op.drop_table("document_counters")
