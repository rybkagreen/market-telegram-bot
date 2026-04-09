"""
Celery task for async document OCR validation.

Flow:
1. Receive upload_id
2. Load DocumentUpload record
3. Run OCR pipeline via DocumentValidationService
4. Extract structured data
5. Update DocumentUpload with results
6. Compare with user's legal profile if exists
"""

import json
import logging
from datetime import UTC, datetime

from src.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    max_retries=2,
    default_retry_delay=60,
    queue="default",
    name="document_ocr.process_document",
)
def process_document_ocr(self, upload_id: int) -> dict:  # NOSONAR: python:S3776
    """
    Async OCR processing for a single document upload.

    Args:
        upload_id: ID of DocumentUpload record.

    Returns:
        dict with processing results.
    """
    import asyncio

    from src.core.services.document_validation_service import (
        DocumentValidationService,
        validate_against_profile,
    )
    from src.db.models.document_upload import DocumentUpload
    from src.db.session import async_session_factory

    async def _process() -> dict:
        async with async_session_factory() as session:
            # Load upload record
            result = await session.execute(
                DocumentUpload.__table__.select().where(DocumentUpload.id == upload_id)
            )
            row = result.mappings().first()
            if not row:
                logger.error(f"DocumentUpload id={upload_id} not found")
                return {"error": "Upload not found"}

            user_id = row["user_id"]
            stored_path = row["stored_path"]
            file_type = row["file_type"]
            document_type = row["document_type"]

            # Mark as processing
            from sqlalchemy import update as sa_update

            await session.execute(
                sa_update(DocumentUpload)
                .where(DocumentUpload.id == upload_id)
                .values(
                    validation_status="processing",
                    processing_started_at=datetime.now(UTC),
                )
            )
            await session.commit()

            # Run OCR pipeline
            svc_result = DocumentValidationService.process_document(
                stored_path, file_type, user_id, document_type
            )

            # Check for errors
            if svc_result.get("error"):
                status = (
                    "failed" if "not extracted" in svc_result["error"].lower() else "unreadable"
                )
                await session.execute(
                    sa_update(DocumentUpload)
                    .where(DocumentUpload.id == upload_id)
                    .values(
                        validation_status=status,
                        error_message=svc_result["error"],
                        completed_at=datetime.now(UTC),
                    )
                )
                await session.commit()
                return {"upload_id": upload_id, "status": status, "error": svc_result["error"]}

            # Quality results
            quality = svc_result.get("quality", {})
            ocr = svc_result.get("ocr", {})
            extracted = svc_result.get("extracted", {})

            # Determine readability
            is_readable = quality.get("is_readable", True) if quality else True

            # Validation against existing profile
            validation = {}
            if extracted.get("inn"):
                # Load user's legal profile for comparison
                from src.db.models.legal_profile import LegalProfile

                profile_result = await session.execute(
                    LegalProfile.__table__.select().where(LegalProfile.user_id == user_id)
                )
                profile_row = profile_result.mappings().first()

                if profile_row:
                    profile_data = {
                        "inn": profile_row.get("inn"),
                        "kpp": profile_row.get("kpp"),
                        "ogrn": profile_row.get("ogrn"),
                        "ogrnip": profile_row.get("ogrnip"),
                        "bik": profile_row.get("bank_bik"),
                        "account": profile_row.get("bank_account"),
                        "name": profile_row.get("legal_name"),
                    }
                    validation = validate_against_profile(extracted, profile_data)

            # Update record with results
            update_values = {
                "ocr_text": ocr.get("text", "")[:10000],  # Limit text storage
                "ocr_confidence": ocr.get("confidence", 0.0),
                "image_quality_score": quality.get("score"),
                "quality_issues": json.dumps(quality.get("issues", [])),
                "is_readable": is_readable,
                "extracted_inn": extracted.get("inn"),
                "extracted_kpp": extracted.get("kpp"),
                "extracted_ogrn": extracted.get("ogrn"),
                "extracted_ogrnip": extracted.get("ogrnip"),
                "extracted_name": extracted.get("name"),
                "validation_status": "completed" if is_readable else "unreadable",
                "validation_details": json.dumps(validation) if validation else None,
                "completed_at": datetime.now(UTC),
            }

            if not is_readable:
                update_values["error_message"] = (
                    f"Низкое качество изображения: {', '.join(quality.get('issues', []))}"
                )

            await session.execute(
                sa_update(DocumentUpload)
                .where(DocumentUpload.id == upload_id)
                .values(**update_values)
            )
            await session.commit()

            return {
                "upload_id": upload_id,
                "status": "completed" if is_readable else "unreadable",
                "quality_score": quality.get("score"),
                "ocr_confidence": ocr.get("confidence"),
                "extracted": extracted,
                "validation": validation,
            }

    return asyncio.run(_process())
