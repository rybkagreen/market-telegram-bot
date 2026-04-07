"""add yandex ord fields to ord_registrations

Revision ID: s28a001_add_yandex_ord_fields
Revises: s26f001_act_signing_flow
Create Date: 2026-04-04 00:00:00.000000

Adds Yandex ORD-specific columns for tracking:
- yandex_request_id: request_id from POST /creative for polling /status
- platform_ord_id: platform ID registered in Yandex ORD
- contract_ord_id: contract ID registered in Yandex ORD
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "s28a001_add_yandex_ord_fields"
down_revision = "s26f001_act_signing_flow"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ord_registrations",
        sa.Column("yandex_request_id", sa.String(128), nullable=True),
    )
    op.add_column(
        "ord_registrations",
        sa.Column("platform_ord_id", sa.String(128), nullable=True),
    )
    op.add_column(
        "ord_registrations",
        sa.Column("contract_ord_id", sa.String(128), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("ord_registrations", "contract_ord_id")
    op.drop_column("ord_registrations", "platform_ord_id")
    op.drop_column("ord_registrations", "yandex_request_id")
