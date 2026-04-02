"""add_platform_legal_fields

Revision ID: d1e2f3a4b5c6
Revises: a8f3e2d1c9b0
Create Date: 2026-03-23 12:00:00.000000

Adds legal/requisites columns to platform_account for use in contract templates.
"""

import sqlalchemy as sa
from alembic import op

revision = "d1e2f3a4b5c6"
down_revision = "a8f3e2d1c9b0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("platform_account", sa.Column("legal_name", sa.String(500), nullable=True))
    op.add_column("platform_account", sa.Column("inn", sa.String(12), nullable=True))
    op.add_column("platform_account", sa.Column("kpp", sa.String(9), nullable=True))
    op.add_column("platform_account", sa.Column("ogrn", sa.String(15), nullable=True))
    op.add_column("platform_account", sa.Column("address", sa.Text(), nullable=True))
    op.add_column("platform_account", sa.Column("bank_name", sa.String(200), nullable=True))
    op.add_column("platform_account", sa.Column("bank_account", sa.String(20), nullable=True))
    op.add_column("platform_account", sa.Column("bank_bik", sa.String(9), nullable=True))
    op.add_column("platform_account", sa.Column("bank_corr_account", sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column("platform_account", "bank_corr_account")
    op.drop_column("platform_account", "bank_bik")
    op.drop_column("platform_account", "bank_account")
    op.drop_column("platform_account", "bank_name")
    op.drop_column("platform_account", "address")
    op.drop_column("platform_account", "ogrn")
    op.drop_column("platform_account", "kpp")
    op.drop_column("platform_account", "inn")
    op.drop_column("platform_account", "legal_name")
