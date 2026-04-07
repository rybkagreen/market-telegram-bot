"""add_sent_count_to_placement_requests

Revision ID: 671474e06737
Revises: 400a42ff6da0
Create Date: 2026-03-21 20:48:14.617347

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "671474e06737"
down_revision: str | None = "400a42ff6da0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add missing columns to placement_requests
    op.add_column(
        "placement_requests",
        sa.Column("sent_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "placement_requests",
        sa.Column("failed_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "placement_requests",
        sa.Column("click_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "placement_requests",
        sa.Column("last_published_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Add missing columns to transactions
    op.add_column("transactions", sa.Column("payment_status", sa.String(length=32), nullable=True))
    op.add_column(
        "transactions",
        sa.Column("balance_before", sa.Numeric(precision=12, scale=2), nullable=True),
    )
    op.add_column(
        "transactions", sa.Column("balance_after", sa.Numeric(precision=12, scale=2), nullable=True)
    )

    # Fix mailing_logs indexes (renamed in model)
    op.drop_index(op.f("ix_mailing_logs_sent_at"), table_name="mailing_logs", if_exists=True)
    op.drop_index(op.f("ix_mailing_logs_status_chat"), table_name="mailing_logs", if_exists=True)
    op.create_index("ix_mailing_sent_at", "mailing_logs", ["sent_at"], unique=False)
    op.create_index("ix_mailing_status_chat", "mailing_logs", ["status", "chat_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_mailing_status_chat", table_name="mailing_logs")
    op.drop_index("ix_mailing_sent_at", table_name="mailing_logs")
    op.create_index(
        op.f("ix_mailing_logs_status_chat"), "mailing_logs", ["status", "chat_id"], unique=False
    )
    op.create_index(op.f("ix_mailing_logs_sent_at"), "mailing_logs", ["sent_at"], unique=False)
    op.drop_column("transactions", "balance_after")
    op.drop_column("transactions", "balance_before")
    op.drop_column("transactions", "payment_status")
    op.drop_column("placement_requests", "last_published_at")
    op.drop_column("placement_requests", "click_count")
    op.drop_column("placement_requests", "failed_count")
    op.drop_column("placement_requests", "sent_count")
