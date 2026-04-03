"""
Abstract EdoProvider protocol — interface for EDO (electronic document management) integration.

To connect a real provider (Diadoc, SBIS, Kontur), implement this protocol
and pass the instance to services that need EDO functionality.
"""

from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class EdoProvider(Protocol):
    """Protocol for EDO provider implementations."""

    async def sign_document(self, doc_path: Path) -> str:
        """Sign a document and return the signature/document ID."""
        ...

    async def get_status(self, doc_id: str) -> str:
        """Get the current status of a signed document. Returns: draft/signed/sent/error."""
        ...

    async def send_signed(self, doc_id: str, signature: str) -> dict:
        """Send a signed document to the counterparty. Returns status dict."""
        ...
