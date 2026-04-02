"""add_escrow_transaction_id_to_placement_requests

Revision ID: g1h2i3j4k5l6
Revises: e5f6a7b8c9d0
Create Date: 2026-03-23 01:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "g1h2i3j4k5l6"
down_revision: str | None = "e5f6a7b8c9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    col_exists = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name='placement_requests' AND column_name='escrow_transaction_id'"
        )
    ).fetchone()
    if not col_exists:
        op.add_column(
            "placement_requests",
            sa.Column(
                "escrow_transaction_id",
                sa.Integer(),
                sa.ForeignKey("transactions.id"),
                nullable=True,
            ),
        )
    idx_exists = conn.execute(
        sa.text(
            "SELECT 1 FROM pg_indexes WHERE tablename='placement_requests' "
            "AND indexname='ix_placement_requests_escrow_transaction_id'"
        )
    ).fetchone()
    if not idx_exists:
        op.create_index(
            "ix_placement_requests_escrow_transaction_id",
            "placement_requests",
            ["escrow_transaction_id"],
        )


def downgrade() -> None:
    op.drop_index("ix_placement_requests_escrow_transaction_id", table_name="placement_requests")
    op.drop_column("placement_requests", "escrow_transaction_id")
