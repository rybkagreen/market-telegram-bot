"""
Log sanitizer — prevents PII from appearing in structured logs and error responses.
Register sanitized_validation_error_handler in main.py.
"""

import logging
from copy import deepcopy
from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

SENSITIVE_FIELD_NAMES = frozenset(
    {
        "passport_series",
        "passport_number",
        "passport_issued_by",
        "bank_account",
        "bank_corr_account",
        "yoomoney_wallet",
        "inn_scan_file_id",
        "passport_scan_file_id",
        "self_employed_cert_file_id",
        "company_doc_file_id",
        "file_id",
        "signature_ip",
    }
)


def sanitize_dict(data: Any) -> Any:
    """Recursively redact sensitive keys from a dict (or list of dicts)."""
    if isinstance(data, dict):
        return {
            k: "***REDACTED***" if k in SENSITIVE_FIELD_NAMES else sanitize_dict(v)
            for k, v in data.items()
        }
    if isinstance(data, list):
        return [sanitize_dict(item) for item in data]
    return data


async def sanitized_validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Override default 422 handler to sanitize body before logging."""
    try:
        body = await request.json()
        sanitized = sanitize_dict(deepcopy(body))
    except Exception:
        sanitized = None

    logger.warning(
        "Validation error on %s %s",
        request.method,
        request.url.path,
        extra={"body": sanitized, "errors": exc.errors()},
    )
    return JSONResponse(status_code=422, content={"detail": exc.errors()})
