"""drift_fix_post_t1_2_5f_egrul_idempotency_audit_action_enum

Revision ID: cd59fc72b378
Revises: e6a88faa9fa0
Create Date: 2026-05-08 08:24:14.666132

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'cd59fc72b378'
down_revision: str | None = 'e6a88faa9fa0'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# PayoutMethodType enum used for payout_requests.payout_method_type alter.
# Autogenerate omits CREATE TYPE for VARCHAR→ENUM column changes, so we
# materialise the type explicitly via SQLAlchemy's ENUM helper.
payout_method_enum = postgresql.ENUM(
    'bank_card', 'yoomoney', 'sbp', 'bank_transfer',
    name='payoutmethodtype',
    create_type=False,
)


def upgrade() -> None:
    op.alter_column('audit_logs', 'action',
               existing_type=sa.VARCHAR(length=20),
               type_=sa.String(length=64),
               existing_nullable=False)
    op.add_column('legal_profiles', sa.Column('egrul_egrip_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('payout_requests', sa.Column('idempotency_key', sa.String(length=128), nullable=True))

    payout_method_enum.create(op.get_bind(), checkfirst=True)
    op.alter_column('payout_requests', 'payout_method_type',
               existing_type=sa.VARCHAR(length=16),
               type_=sa.Enum('bank_card', 'yoomoney', 'sbp', 'bank_transfer', name='payoutmethodtype'),
               existing_nullable=True,
               postgresql_using='payout_method_type::text::payoutmethodtype')

    op.create_index(op.f('ix_payout_requests_idempotency_key'), 'payout_requests', ['idempotency_key'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_payout_requests_idempotency_key'), table_name='payout_requests')
    op.alter_column('payout_requests', 'payout_method_type',
               existing_type=sa.Enum('bank_card', 'yoomoney', 'sbp', 'bank_transfer', name='payoutmethodtype'),
               type_=sa.VARCHAR(length=16),
               existing_nullable=True,
               postgresql_using='payout_method_type::text')
    payout_method_enum.drop(op.get_bind(), checkfirst=True)

    op.drop_column('payout_requests', 'idempotency_key')
    op.drop_column('legal_profiles', 'egrul_egrip_snapshot')
    op.alter_column('audit_logs', 'action',
               existing_type=sa.String(length=64),
               type_=sa.VARCHAR(length=20),
               existing_nullable=False)
