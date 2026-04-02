"""add_publication_log

Revision ID: h2i3j4k5l6m7
Revises: g1h2i3j4k5l6
Create Date: 2026-03-24 10:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "h2i3j4k5l6m7"
down_revision: str | None = "g1h2i3j4k5l6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "publication_logs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("placement_id", sa.Integer(), nullable=False),
        sa.Column("channel_id", sa.BigInteger(), nullable=False),
        sa.Column("event_type", sa.String(length=30), nullable=False),
        sa.Column("message_id", sa.BigInteger(), nullable=True),
        sa.Column("post_url", sa.String(length=500), nullable=True),
        sa.Column("erid", sa.String(length=100), nullable=True),
        sa.Column(
            "detected_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("extra", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(
            ["placement_id"],
            ["placement_requests.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_publication_logs_placement_id",
        "publication_logs",
        ["placement_id"],
    )
    op.create_index(
        "ix_publication_logs_channel_id",
        "publication_logs",
        ["channel_id"],
    )
    op.create_index(
        "ix_publication_logs_event_type",
        "publication_logs",
        ["event_type"],
    )
    op.create_index(
        "ix_publication_logs_detected_at",
        "publication_logs",
        ["detected_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_publication_logs_detected_at", table_name="publication_logs")
    op.drop_index("ix_publication_logs_event_type", table_name="publication_logs")
    op.drop_index("ix_publication_logs_channel_id", table_name="publication_logs")
    op.drop_index("ix_publication_logs_placement_id", table_name="publication_logs")
    op.drop_table("publication_logs")
