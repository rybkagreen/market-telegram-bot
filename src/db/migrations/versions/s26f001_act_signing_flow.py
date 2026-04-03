"""act_signing_flow

Revision ID: s26f001_act_signing_flow
Revises: s26e001_add_document_links
Create Date: 2026-04-03 23:30:00.000000

Additive migration for act signing flow & dual generation. SAFE FOR PROD.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "s26f001_act_signing_flow"
down_revision: str | None = "s26e001_add_document_links"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ─── Act: signing fields ────────────────────────────────────
    op.add_column(
        "acts",
        sa.Column(
            "act_type",
            sa.String(10),
            nullable=False,
            server_default="income",
        ),
    )
    op.add_column(
        "acts",
        sa.Column(
            "sign_status",
            sa.String(15),
            nullable=False,
            server_default="draft",
        ),
    )
    op.add_column(
        "acts",
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "acts",
        sa.Column("sign_method", sa.String(20), nullable=True),
    )
    op.add_column(
        "acts",
        sa.Column("ip_hash", sa.String(64), nullable=True),
    )
    op.add_column(
        "acts",
        sa.Column("user_agent_hash", sa.String(64), nullable=True),
    )
    op.create_index("ix_acts_sign_status", "acts", ["sign_status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_acts_sign_status", table_name="acts")
    op.drop_column("acts", "user_agent_hash")
    op.drop_column("acts", "ip_hash")
    op.drop_column("acts", "sign_method")
    op.drop_column("acts", "signed_at")
    op.drop_column("acts", "sign_status")
    op.drop_column("acts", "act_type")
