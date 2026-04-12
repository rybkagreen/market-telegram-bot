"""add advertiser counter-offer fields to placement_requests

Revision ID: 0002_adv_counter
Revises: 0001_initial_schema
Create Date: 2026-04-10

FIX #4: Added separate fields for advertiser's counter-offers to prevent data collision
with owner's counter-offer price/schedule/comment fields.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_adv_counter"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add advertiser_counter_price column
    op.add_column(
        "placement_requests",
        sa.Column("advertiser_counter_price", sa.Numeric(10, 2), nullable=True),
    )

    # Add advertiser_counter_schedule column
    op.add_column(
        "placement_requests",
        sa.Column("advertiser_counter_schedule", sa.DateTime(timezone=True), nullable=True),
    )

    # Add advertiser_counter_comment column
    op.add_column(
        "placement_requests", sa.Column("advertiser_counter_comment", sa.Text(), nullable=True)
    )


def downgrade() -> None:
    # Remove columns in reverse order
    op.drop_column("placement_requests", "advertiser_counter_comment")
    op.drop_column("placement_requests", "advertiser_counter_schedule")
    op.drop_column("placement_requests", "advertiser_counter_price")
