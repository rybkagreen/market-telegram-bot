"""fix_review_unique_per_reviewer

Revision ID: j5k6l7m8n9o0
Revises: h2i3j4k5l6m7
Create Date: 2026-03-30 00:00:00.000000

Меняем UNIQUE(placement_request_id) → UNIQUE(placement_request_id, reviewer_id),
чтобы advertiser и owner могли каждый оставить свой отзыв по одному placement.
"""

from alembic import op

revision: str = "j5k6l7m8n9o0"
down_revision: str = "h2i3j4k5l6m7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop old single-column unique constraint
    op.drop_constraint("reviews_placement_request_id_key", "reviews", type_="unique")
    # Create composite unique constraint: one review per (placement, reviewer)
    op.create_unique_constraint(
        "uq_reviews_placement_reviewer",
        "reviews",
        ["placement_request_id", "reviewer_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_reviews_placement_reviewer", "reviews", type_="unique")
    op.create_unique_constraint(
        "reviews_placement_request_id_key",
        "reviews",
        ["placement_request_id"],
    )
