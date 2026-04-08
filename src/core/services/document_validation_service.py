"""
Document Validation Service — OCR + quality check + data extraction.

Pipeline:
1. File validation (type, size)
2. HEIC → JPEG conversion (if needed)
3. Image quality assessment (blur, brightness, resolution)
4. OCR text extraction (PyMuPDF for PDF, Tesseract for images)
5. Structured data extraction (INN, KPP, OGRN, names)
6. Validation against user-entered data
"""

import logging
import re
from pathlib import Path
from typing import Any

import cv2
import fitz  # PyMuPDF
import pytesseract
from PIL import Image

logger = logging.getLogger(__name__)

# ─── Constants ───────────────────────────────────────────────────────

UPLOAD_DIR = Path("/data/uploads/legal_profiles")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_TYPES = {"jpg", "jpeg", "png", "webp", "heic", "pdf"}

# Quality thresholds
MIN_RESOLUTION = 800  # minimum width or height in pixels
BLUR_THRESHOLD = 100  # Laplacian variance below this = blurry
DARK_THRESHOLD = 30   # mean brightness below this = too dark

# ─── Regex patterns for data extraction ──────────────────────────────

INN_PATTERN = re.compile(r'(?:ИНН|inn)[\s:]*\.?\s*(\d{10}|\d{12})', re.IGNORECASE)
KPP_PATTERN = re.compile(r'(?:КПП|kpp)[\s:]*\.?\s*(\d{9})', re.IGNORECASE)
OGRN_PATTERN = re.compile(r'(?:ОГРН|ogrn)[\s:]*\.?\s*(\d{13})', re.IGNORECASE)
OGRNIP_PATTERN = re.compile(r'(?:ОГРНИП|ogrnip)[\s:]*\.?\s*(\d{15})', re.IGNORECASE)
BIK_PATTERN = re.compile(r'(?:БИК|bik)[\s:]*\.?\s*(\d{9})', re.IGNORECASE)
ACCOUNT_PATTERN = re.compile(r'(?:р[./]?с|расчетный\s+счет|сч[её]т)[\s:]*\.?\s*([\d]{20})', re.IGNORECASE)


def validate_file_type(filename: str) -> str | None:
    """Validate file extension, return lowercase extension or None if invalid."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext in ALLOWED_TYPES:
        return ext
    return None


def check_image_quality(image_path: str) -> dict[str, Any]:
    """
    Check image quality: blur, brightness, resolution.

    Returns:
        dict with score (0–1), issues list, and is_readable flag.
    """
    img = cv2.imread(image_path)
    if img is None:
        return {"score": 0.0, "issues": ["cannot_read"], "is_readable": False}

    h, w = img.shape[:2]

    issues: list[str] = []

    # Resolution check
    if max(w, h) < MIN_RESOLUTION:
        issues.append("low_resolution")

    # Blur detection (Laplacian variance)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    if laplacian_var < BLUR_THRESHOLD:
        issues.append("blurry")

    # Brightness check
    brightness = gray.mean()
    if brightness < DARK_THRESHOLD:
        issues.append("too_dark")
    elif brightness > 220:
        issues.append("too_bright")

    # Calculate score (0–1)
    score = 1.0
    if "blurry" in issues:
        score -= 0.4
    if "too_dark" in issues or "too_bright" in issues:
        score -= 0.2
    if "low_resolution" in issues:
        score -= 0.2
    score = max(0.0, score)

    return {
        "score": round(score, 2),
        "issues": issues,
        "is_readable": len(issues) == 0,
        "resolution": f"{w}x{h}",
        "brightness": round(brightness, 1),
        "laplacian_variance": round(laplacian_var, 1),
    }


def convert_heic_to_jpeg(heic_path: str) -> str | None:
    """Convert HEIC to JPEG. Returns JPEG path or None on failure."""
    try:
        from pillow_heif import register_heif_opener
        register_heif_opener()

        img = Image.open(heic_path)
        jpeg_path = heic_path.rsplit(".", 1)[0] + ".jpg"
        img.convert("RGB").save(jpeg_path, "JPEG", quality=90)
        return jpeg_path
    except Exception as e:
        logger.error(f"HEIC conversion failed: {e}")
        return None


def extract_text_from_pdf(pdf_path: str) -> tuple[str, float]:
    """Extract text from PDF using PyMuPDF. Returns (text, confidence)."""
    try:
        doc = fitz.open(pdf_path)
        full_text = []
        total_confidence = 0.0
        page_count = 0

        for page in doc:
            text = page.get_text()
            full_text.append(text)
            # PyMuPDF doesn't provide confidence, estimate based on text density
            if text.strip():
                total_confidence += 0.85  # PDF text is usually reliable
                page_count += 1

        doc.close()
        confidence = total_confidence / max(page_count, 1)
        return "\n".join(full_text), round(confidence, 2)
    except Exception as e:
        logger.error(f"PDF extraction failed: {e}")
        return "", 0.0


def extract_text_from_image(image_path: str) -> tuple[str, float]:
    """Extract text from image using Tesseract OCR. Returns (text, confidence)."""
    try:
        # Russian + English
        data = pytesseract.image_to_data(
            image_path,
            lang="rus+eng",
            output_type=pytesseract.Output.DICT,
        )

        # Build text with confidence
        text_parts = []
        total_conf = 0.0
        count = 0

        for i, word in enumerate(data["text"]):
            conf = int(data["conf"][i])
            if conf > 0 and word.strip():
                text_parts.append(word)
                total_conf += conf
                count += 1

        text = " ".join(text_parts)
        confidence = (total_conf / max(count, 1)) / 100.0  # Normalize to 0–1

        return text, round(confidence, 2)
    except Exception as e:
        logger.error(f"Image OCR failed: {e}")
        return "", 0.0


def extract_structured_data(text: str) -> dict[str, str | None]:
    """Extract INN, KPP, OGRN, etc. from OCR text."""
    result: dict[str, str | None] = {
        "inn": None,
        "kpp": None,
        "ogrn": None,
        "ogrnip": None,
        "bik": None,
        "account": None,
        "name": None,
    }

    # INN
    inn_match = INN_PATTERN.search(text)
    if inn_match:
        result["inn"] = inn_match.group(1)
    else:
        # Try standalone 10 or 12 digit numbers
        standalone = re.findall(r'\b(\d{10}|\d{12})\b', text)
        if standalone:
            result["inn"] = standalone[0]

    # KPP
    kpp_match = KPP_PATTERN.search(text)
    if kpp_match:
        result["kpp"] = kpp_match.group(1)

    # OGRN
    ogrn_match = OGRN_PATTERN.search(text)
    if ogrn_match:
        result["ogrn"] = ogrn_match.group(1)

    # OGRNIP
    ogrnip_match = OGRNIP_PATTERN.search(text)
    if ogrnip_match:
        result["ogrnip"] = ogrnip_match.group(1)

    # BIK
    bik_match = BIK_PATTERN.search(text)
    if bik_match:
        result["bik"] = bik_match.group(1)

    # Bank account
    acc_match = ACCOUNT_PATTERN.search(text)
    if acc_match:
        result["account"] = acc_match.group(1)

    # Company name — try to extract from common patterns
    name_match = re.search(r'(?:Наименование|Название|Организация|ООО|ИП)[\s:]*[„"]?([^\n"]+)', text)
    if name_match:
        result["name"] = name_match.group(1).strip()[:200]

    return result


def validate_against_profile(extracted: dict[str, str | None], profile_data: dict[str, str | None]) -> dict[str, Any]:
    """
    Compare extracted OCR data with user-entered profile data.

    Returns:
        dict with field-level match results and overall confidence.
    """
    fields_to_check = ["inn", "kpp", "ogrn", "ogrnip", "bik", "account", "name"]
    results: dict[str, Any] = {}
    match_count = 0
    total_fields = 0

    for field in fields_to_check:
        extracted_val = (extracted.get(field) or "").strip().lower()
        profile_val = (profile_data.get(field) or "").strip().lower()

        if not extracted_val and not profile_val:
            continue  # Both empty, skip

        total_fields += 1

        if not extracted_val:
            results[field] = {"match": False, "reason": "not_extracted", "confidence": 0.0}
        elif not profile_val:
            results[field] = {"match": True, "reason": "profile_empty", "confidence": 0.5}
        elif extracted_val == profile_val:
            results[field] = {"match": True, "reason": "exact_match", "confidence": 1.0}
            match_count += 1
        elif extracted_val in profile_val or profile_val in extracted_val:
            results[field] = {"match": True, "reason": "partial_match", "confidence": 0.7}
            match_count += 0.5
        else:
            results[field] = {"match": False, "reason": "mismatch", "confidence": 0.0}

    overall_confidence = match_count / max(total_fields, 1)

    return {
        "fields": results,
        "overall_confidence": round(overall_confidence, 2),
        "total_fields_checked": total_fields,
        "matched_fields": match_count,
    }


class DocumentValidationService:
    """Main service for document upload and validation."""

    @staticmethod
    def save_uploaded_file(user_id: int, filename: str, file_content: bytes) -> tuple[str, int]:
        """
        Save uploaded file to disk.

        Returns:
            (stored_path, file_size)
        """
        import uuid

        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
        user_dir = UPLOAD_DIR / str(user_id)
        user_dir.mkdir(parents=True, exist_ok=True)

        stored_name = f"{uuid.uuid4().hex}.{ext}"
        stored_path = str(user_dir / stored_name)

        with open(stored_path, "wb") as f:
            f.write(file_content)

        return stored_path, len(file_content)

    @staticmethod
    def process_document(stored_path: str, file_type: str, user_id: int, document_type: str) -> dict[str, Any]:
        """
        Full OCR + validation pipeline.

        Returns:
            dict with quality, OCR, extraction, and validation results.
        """
        result: dict[str, Any] = {
            "quality": {},
            "ocr": {"text": "", "confidence": 0.0},
            "extracted": {},
            "validation": {},
            "error": None,
        }

        try:
            # Step 1: HEIC conversion
            actual_path = stored_path
            if file_type == "heic":
                jpeg_path = convert_heic_to_jpeg(stored_path)
                if jpeg_path:
                    actual_path = jpeg_path
                    file_type = "jpg"
                else:
                    result["error"] = "Не удалось конвертировать HEIC"
                    return result

            # Step 2: Image quality check (for images only)
            if file_type != "pdf":
                quality = check_image_quality(actual_path)
                result["quality"] = quality

                if not quality["is_readable"]:
                    return result  # Stop if unreadable

            # Step 3: OCR
            if file_type == "pdf":
                text, confidence = extract_text_from_pdf(actual_path)
            else:
                text, confidence = extract_text_from_image(actual_path)

            result["ocr"] = {"text": text, "confidence": confidence}

            if not text.strip():
                result["error"] = "Не удалось извлечь текст из документа"
                return result

            # Step 4: Extract structured data
            extracted = extract_structured_data(text)
            result["extracted"] = extracted

            return result

        except Exception as e:
            logger.error(f"Document processing failed for user {user_id}: {e}")
            result["error"] = f"Ошибка обработки: {str(e)}"
            return result
