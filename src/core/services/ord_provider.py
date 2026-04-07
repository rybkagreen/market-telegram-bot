"""
Abstract OrdProvider protocol — interface for ORD (advertising registry) integration.

To connect a real provider (Yandex/VK/OZON ORD), implement this protocol
and call OrdService.set_provider(your_provider_instance).
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol, runtime_checkable


@dataclass
class OrdRegistrationResult:
    """Result of registering a creative in ORD."""

    erid: str
    provider: str
    raw_response: dict | None = field(default=None)


@runtime_checkable
class OrdProvider(Protocol):
    """Protocol for ORD provider implementations."""

    async def register_advertiser(self, user_id: int, name: str, inn: str | None) -> str:
        """Register an advertiser in ORD. Returns ord_advertiser_id."""
        ...

    async def register_creative(
        self,
        placement_request_id: int,
        ad_text: str,
        media_type: str,
        advertiser_ord_id: str,
    ) -> str:
        """Register an ad creative and return erid."""
        ...

    async def register_platform(self, channel_id: int, channel_url: str, channel_name: str) -> str:
        """Register a Telegram channel as a platform (site) in ORD.
        Returns deterministic platform_ord_id: 'platform-{channel_id}'."""
        ...

    async def register_contract(
        self,
        placement_request_id: int,
        advertiser_ord_id: str,
        amount_rub: str,
        date_str: str,
    ) -> str:
        """Register a contract between advertiser (RD) and RekHarbor (RR) in ORD.
        Returns deterministic contract_ord_id: 'contract-{placement_request_id}'."""
        ...

    async def report_publication(
        self,
        erid: str,
        published_at: datetime,
        placement_request_id: int,
    ) -> bool:
        """Report a publication fact to ORD. Returns True on success."""
        ...

    async def get_status(self, erid: str) -> str:
        """Get the current status of an erid registration."""
        ...
