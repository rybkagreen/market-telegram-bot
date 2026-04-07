"""drop unused PG enum types feedbackstatus and mailingstatus

These types were created by earlier migrations but the columns
(user_feedback.status and mailing_logs.status) were always stored
as varchar(32). The orphaned PG enum types cause Alembic autogenerate
drift and SQLAlchemy to emit ::feedbackstatus casts that fail at runtime.

Revision ID: c7e2d4f8a1b9
Revises: 671474e06737
Create Date: 2026-03-22 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c7e2d4f8a1b9"
down_revision: str | None = "671474e06737"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Drop orphaned PG enum types — columns are already varchar(32)
    op.execute("DROP TYPE IF EXISTS feedbackstatus")
    op.execute("DROP TYPE IF EXISTS mailingstatus")


def downgrade() -> None:
    # Recreate enum types for rollback safety (values match original migrations)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE feedbackstatus AS ENUM ('new', 'in_progress', 'resolved', 'rejected');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE mailingstatus AS ENUM (
                'pending_approval', 'queued', 'pending', 'sent', 'failed',
                'skipped', 'rejected', 'changes_requested', 'paid'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
