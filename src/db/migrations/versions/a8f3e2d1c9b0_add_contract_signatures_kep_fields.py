"""add_contract_signatures_kep_fields

Revision ID: a8f3e2d1c9b0
Revises: b9c3d2e1f4a5
Create Date: 2026-03-23 10:00:00.000000

S8: Adds contract_signatures table (append-only signature audit trail)
    and kep_requested, kep_request_email, role columns to contracts.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a8f3e2d1c9b0"
down_revision = "b9c3d2e1f4a5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "contract_signatures",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("contract_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("legal_status", sa.String(length=30), nullable=False),
        sa.Column(
            "signed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("signature_method", sa.String(length=20), nullable=False),
        sa.Column("document_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "template_version",
            sa.String(length=20),
            server_default="1.0",
            nullable=False,
        ),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(["contract_id"], ["contracts.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_contract_signatures_contract_id", "contract_signatures", ["contract_id"]
    )
    op.create_index(
        "ix_contract_signatures_user_id", "contract_signatures", ["user_id"]
    )
    op.create_index(
        "ix_contract_signatures_signed_at", "contract_signatures", ["signed_at"]
    )

    op.add_column(
        "contracts",
        sa.Column(
            "kep_requested",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )
    op.add_column(
        "contracts",
        sa.Column("kep_request_email", sa.String(length=254), nullable=True),
    )
    op.add_column(
        "contracts",
        sa.Column("role", sa.String(length=20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("contracts", "role")
    op.drop_column("contracts", "kep_request_email")
    op.drop_column("contracts", "kep_requested")

    op.drop_index("ix_contract_signatures_signed_at", table_name="contract_signatures")
    op.drop_index("ix_contract_signatures_user_id", table_name="contract_signatures")
    op.drop_index(
        "ix_contract_signatures_contract_id", table_name="contract_signatures"
    )
    op.drop_table("contract_signatures")
