"""
SQLAlchemy TypeDecorators for transparent field-level encryption.
Uses Fernet (AES-128-CBC + HMAC-SHA256) from the cryptography library.
"""

import hashlib
import hmac
import logging

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import String
from sqlalchemy.types import TypeDecorator

logger = logging.getLogger(__name__)


def _get_fernet() -> Fernet:
    """Lazy-load Fernet to avoid settings import at module level."""
    from src.config.settings import settings

    return Fernet(settings.field_encryption_key.encode())


class EncryptedString(TypeDecorator):
    """
    Fernet-encrypted string column.
    Null-safe: None stays None.
    Legacy plaintext values that fail decryption are returned as None with a warning.
    """

    impl = String
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect) -> str | None:  # type: ignore[override]
        if value is None:
            return None
        return _get_fernet().encrypt(value.encode()).decode()

    def process_result_value(self, value: str | None, dialect) -> str | None:  # type: ignore[override]
        if value is None:
            return None
        try:
            return _get_fernet().decrypt(value.encode()).decode()
        except (InvalidToken, Exception):
            logger.warning("Failed to decrypt field — returning None (may be legacy plaintext)")
            return None


class HashableEncryptedString(EncryptedString):
    """
    Like EncryptedString but also provides a static HMAC-SHA256 hash method
    for indexed search without decryption. Use for INN.
    """

    @staticmethod
    def hash_value(plaintext: str) -> str:
        """
        Compute HMAC-SHA256 of plaintext using SEARCH_HASH_KEY.
        Used to build inn_hash for indexed lookup without decryption.
        """
        from src.config.settings import settings

        key = settings.search_hash_key.encode()
        return hmac.new(key, plaintext.encode(), hashlib.sha256).hexdigest()
