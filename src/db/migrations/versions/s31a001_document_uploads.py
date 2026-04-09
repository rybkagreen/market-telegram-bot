"""add_document_uploads_table

Revision ID: s31a001_document_uploads
Revises: s28a001_add_yandex_ord_fields
Create Date: 2026-04-05 12:00:00.000000

Adds document_uploads table for OCR-based legal profile validation.
"""

import sqlalchemy as sa
from alembic import op

revision = "s31a001_document_uploads"
down_revision = "fix_platform_account_enc"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "document_uploads",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer, nullable=False, index=True),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("stored_path", sa.String(500), nullable=False),
        sa.Column("file_type", sa.String(16), nullable=False),
        sa.Column("file_size", sa.Integer, nullable=False),
        sa.Column("document_type", sa.String(32), nullable=False),
        sa.Column("image_quality_score", sa.Numeric(3, 2), nullable=True),
        sa.Column("quality_issues", sa.Text, nullable=True),
        sa.Column("is_readable", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("ocr_text", sa.Text, nullable=True),
        sa.Column("ocr_confidence", sa.Numeric(3, 2), nullable=True),
        sa.Column("extracted_inn", sa.String(20), nullable=True),
        sa.Column("extracted_kpp", sa.String(20), nullable=True),
        sa.Column("extracted_ogrn", sa.String(20), nullable=True),
        sa.Column("extracted_ogrnip", sa.String(20), nullable=True),
        sa.Column("extracted_name", sa.String(500), nullable=True),
        sa.Column("validation_status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("validation_details", sa.Text, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )


def downgrade() -> None:
    op.drop_table("document_uploads")
