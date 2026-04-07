"""add badge tables and streak fields

Revision ID: p1q2r3s4t5u6
Revises: j5k6l7m8n9o0
Create Date: 2026-04-02 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "p1q2r3s4t5u6"
down_revision: str | None = "j5k6l7m8n9o0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create badges table
    op.create_table(
        "badges",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("icon_emoji", sa.String(length=8), nullable=False),
        sa.Column("xp_reward", sa.Integer(), server_default="0", nullable=False),
        sa.Column("credits_reward", sa.Integer(), server_default="0", nullable=False),
        sa.Column("category", sa.String(length=16), nullable=False),
        sa.Column("condition_type", sa.String(length=32), nullable=False),
        sa.Column("condition_value", sa.Float(), server_default="0", nullable=False),
        sa.Column("is_rare", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    # Create badge_achievements table
    op.create_table(
        "badge_achievements",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("badge_id", sa.Integer(), nullable=False),
        sa.Column("achievement_type", sa.String(length=64), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["badge_id"], ["badges.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # Add badge_id to user_badges
    op.add_column(
        "user_badges",
        sa.Column("badge_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_user_badges_badge_id",
        "user_badges",
        "badges",
        ["badge_id"],
        ["id"],
    )

    # Add streak fields to users
    op.add_column(
        "users",
        sa.Column("login_streak_days", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "users",
        sa.Column("max_streak_days", sa.Integer(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("users", "max_streak_days")
    op.drop_column("users", "login_streak_days")
    op.drop_constraint("fk_user_badges_badge_id", "user_badges", type_="foreignkey")
    op.drop_column("user_badges", "badge_id")
    op.drop_table("badge_achievements")
    op.drop_table("badges")
