"""DocumentUpload model — tracking uploaded legal documents for OCR validation."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class DocumentUpload(Base):
    """Модель загруженного документа для OCR-валидации."""

    __tablename__ = "document_uploads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    # File info
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(String(16), nullable=False)  # pdf, jpg, png, webp, heic
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)  # bytes

    # Document type (what kind of document this is)
    document_type: Mapped[str] = mapped_column(String(32), nullable=False)
    # Options: inn_certificate, ogrn_certificate, bank_details, passport, tax_registration,
    #          self_employed_certificate, other

    # Passport page tracking (which pages this upload contains)
    passport_page_group: Mapped[str | None] = mapped_column(
        String(16), nullable=True
    )  # "main_pages" (2-3), "registration" (propiska), None for non-passport

    # Image quality check results
    image_quality_score: Mapped[float | None] = mapped_column(
        Numeric(3, 2), nullable=True
    )  # 0.00–1.00
    quality_issues: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # JSON: ["blurry", "dark", "low_res"]
    is_readable: Mapped[bool] = mapped_column(
        "is_readable", nullable=False, default=False, server_default="false"
    )

    # OCR results
    ocr_text: Mapped[str | None] = mapped_column(Text, nullable=True)  # Full extracted text
    ocr_confidence: Mapped[float | None] = mapped_column(Numeric(3, 2), nullable=True)  # 0.00–1.00

    # Extracted structured data
    extracted_inn: Mapped[str | None] = mapped_column(String(20), nullable=True)
    extracted_kpp: Mapped[str | None] = mapped_column(String(20), nullable=True)
    extracted_ogrn: Mapped[str | None] = mapped_column(String(20), nullable=True)
    extracted_name: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Validation against user-entered data
    validation_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending", server_default="pending"
    )
    # Options: pending, processing, completed, failed, unreadable
    validation_details: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # JSON: {field: {match: bool, confidence: float}}

    # Processing metadata
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    processing_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<DocumentUpload(id={self.id}, user_id={self.user_id}, type={self.document_type}, status={self.validation_status})>"
