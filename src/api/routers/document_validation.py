"""
Document upload and validation endpoints.

POST /api/legal-profile/documents/upload — Upload a document for OCR validation
GET  /api/legal-profile/documents/:id/status — Check processing status
GET  /api/legal-profile/documents — List uploaded documents
DELETE /api/legal-profile/documents/:id — Delete uploaded document
"""

import json
import logging
from contextlib import suppress
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select

from src.api.dependencies import get_current_user
from src.core.services.document_validation_service import (
    MAX_FILE_SIZE,
    DocumentValidationService,
    validate_file_type,
)
from src.db.models.user import User as UserModel
from src.db.session import async_session_factory

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/legal-profile/documents", tags=["Document Validation"])


class DocumentUploadResponse(BaseModel):
    upload_id: int
    status: str
    file_type: str
    document_type: str


class DocumentStatusResponse(BaseModel):
    upload_id: int
    status: str
    file_type: str
    document_type: str
    image_quality_score: float | None = None
    quality_issues: list[str] | None = None
    is_readable: bool = False
    ocr_confidence: float | None = None
    extracted_inn: str | None = None
    extracted_kpp: str | None = None
    extracted_ogrn: str | None = None
    extracted_name: str | None = None
    validation_details: dict | None = None
    error_message: str | None = None
    created_at: str | None = None
    completed_at: str | None = None


# ─── Upload Document ───────────────────────────────────────────────


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    current_user: Annotated[UserModel, Depends(get_current_user)],
    file: Annotated[UploadFile, File(...)],
    document_type: Annotated[str, Form(...)],
):
    """
    Upload a legal document for OCR validation.

    Supported formats: JPG, JPEG, PNG, WEBP, HEIC, PDF
    Max size: 10 MB
    """
    # Validate file type
    if not file.filename:
        raise HTTPException(status_code=400, detail="Имя файла не указано")

    file_type = validate_file_type(file.filename)
    if not file_type:
        raise HTTPException(
            status_code=400,
            detail="Неподдерживаемый формат. Допустимые: JPG, PNG, WEBP, HEIC, PDF",
        )

    # Validate document type
    allowed_doc_types = {
        "inn_certificate",
        "ogrn_certificate",
        "bank_details",
        "passport",
        "tax_registration",
        "self_employed_certificate",
        "other",
    }
    if document_type not in allowed_doc_types:
        raise HTTPException(
            status_code=400,
            detail=f"Недопустимый тип документа. Варианты: {', '.join(allowed_doc_types)}",
        )

    # Read file content
    content = await file.read()
    file_size = len(content)

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Файл слишком большой (макс. 10 МБ). Ваш: {file_size // 1024 // 1024} МБ",
        )

    if file_size < 1000:
        raise HTTPException(status_code=400, detail="Файл слишком маленький")

    # Save file
    stored_path, actual_size = DocumentValidationService.save_uploaded_file(
        current_user.id, file.filename, content
    )

    # Create DB record

    from src.db.models.document_upload import DocumentUpload

    async with async_session_factory() as session:
        upload = DocumentUpload(
            user_id=current_user.id,
            original_filename=file.filename,
            stored_path=stored_path,
            file_type=file_type,
            file_size=actual_size,
            document_type=document_type,
        )
        session.add(upload)
        await session.flush()
        await session.refresh(upload)
        await session.commit()

    # Trigger async OCR processing
    from src.tasks.document_ocr_tasks import process_document_ocr

    process_document_ocr.delay(upload.id)

    logger.info(
        f"User {current_user.id} uploaded document: {file.filename} "
        f"(type={document_type}, id={upload.id})"
    )

    return DocumentUploadResponse(
        upload_id=upload.id,
        status="pending",
        file_type=file_type,
        document_type=document_type,
    )


# ─── Get Document Status ─────────────────────────────────────────────


@router.get("/{upload_id}/status", response_model=DocumentStatusResponse)
async def get_document_status(
    upload_id: int,
    current_user: Annotated[UserModel, Depends(get_current_user)],
):
    """Check processing status of an uploaded document."""
    from src.db.models.document_upload import DocumentUpload

    async with async_session_factory() as session:
        result = await session.execute(
            select(DocumentUpload).where(
                DocumentUpload.id == upload_id,
                DocumentUpload.user_id == current_user.id,
            )
        )
        upload = result.scalar_one_or_none()

        if not upload:
            raise HTTPException(status_code=404, detail="Документ не найден")

        # Parse quality issues
        quality_issues = None
        if upload.quality_issues:
            try:
                quality_issues = json.loads(upload.quality_issues)
            except (json.JSONDecodeError, TypeError):
                quality_issues = [upload.quality_issues]

        # Parse validation details
        validation_details = None
        if upload.validation_details:
            with suppress(json.JSONDecodeError, TypeError):
                validation_details = json.loads(upload.validation_details)

        return DocumentStatusResponse(
            upload_id=upload.id,
            status=upload.validation_status,
            file_type=upload.file_type,
            document_type=upload.document_type,
            image_quality_score=float(upload.image_quality_score)
            if upload.image_quality_score
            else None,
            quality_issues=quality_issues,
            is_readable=upload.is_readable,
            ocr_confidence=float(upload.ocr_confidence) if upload.ocr_confidence else None,
            extracted_inn=upload.extracted_inn,
            extracted_kpp=upload.extracted_kpp,
            extracted_ogrn=upload.extracted_ogrn,
            extracted_name=upload.extracted_name,
            validation_details=validation_details,
            error_message=upload.error_message,
            created_at=str(upload.created_at) if upload.created_at else None,
            completed_at=str(upload.completed_at) if upload.completed_at else None,
        )


# ─── List Documents ──────────────────────────────────────────────────


@router.get("")
async def list_documents(
    current_user: Annotated[UserModel, Depends(get_current_user)],
):
    """List all uploaded documents for current user."""
    from src.db.models.document_upload import DocumentUpload

    async with async_session_factory() as session:
        result = await session.execute(
            select(DocumentUpload)
            .where(DocumentUpload.user_id == current_user.id)
            .order_by(DocumentUpload.created_at.desc())
        )
        uploads = result.scalars().all()

        return {
            "documents": [
                {
                    "id": u.id,
                    "filename": u.original_filename,
                    "file_type": u.file_type,
                    "document_type": u.document_type,
                    "status": u.validation_status,
                    "is_readable": u.is_readable,
                    "uploaded_at": str(u.created_at),
                }
                for u in uploads
            ]
        }


# ─── Delete Document ─────────────────────────────────────────────────


@router.delete("/{upload_id}")
async def delete_document(
    upload_id: int,
    current_user: Annotated[UserModel, Depends(get_current_user)],
):
    """Delete an uploaded document."""
    import os

    from src.db.models.document_upload import DocumentUpload

    async with async_session_factory() as session:
        result = await session.execute(
            select(DocumentUpload).where(
                DocumentUpload.id == upload_id,
                DocumentUpload.user_id == current_user.id,
            )
        )
        upload = result.scalar_one_or_none()

        if not upload:
            raise HTTPException(status_code=404, detail="Документ не найден")

        # Delete file from disk
        try:
            if os.path.exists(upload.stored_path):
                os.remove(upload.stored_path)
        except OSError as e:
            logger.warning(f"Failed to delete file {upload.stored_path}: {e}")

        # Delete DB record
        await session.delete(upload)
        await session.commit()

    return {"success": True}
