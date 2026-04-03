"""
StubEdoProvider — stub implementation of EdoProvider protocol.
Used until a real EDO provider is configured.
"""

import logging
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class StubEdoProvider:
    """Stub EDO provider — all methods log and return synthetic values."""

    async def sign_document(self, doc_path: Path) -> str:
        """Sign a document (stub). Returns synthetic doc_id."""
        logger.info(
            "EDO stub: sign_document called for %s",
            doc_path.name,
        )
        ts = int(datetime.now(UTC).timestamp())
        return f"STUB-EDO-SIGN-{ts}"

    async def get_status(self, doc_id: str) -> str:
        """Get document status (stub). Returns 'signed' for any doc_id."""
        logger.info("EDO stub: get_status called for %s", doc_id)
        return "signed"

    async def send_signed(self, doc_id: str, signature: str) -> dict:
        """Send signed document (stub). Returns success dict."""
        logger.info(
            "EDO stub: send_signed called for doc_id=%s, signature=%s",
            doc_id,
            signature[:20] if signature else None,
        )
        return {
            "status": "sent",
            "doc_id": doc_id,
            "sent_at": datetime.now(UTC).isoformat(),
            "provider": "stub",
        }
