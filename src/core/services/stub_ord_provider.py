# TODO: заменить на реальный провайдер (Яндекс/VK/OZON ОРД)
"""
StubOrdProvider — stub implementation of OrdProvider protocol.
Used until a real ORD provider is configured via ORD_PROVIDER env var.
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class StubOrdProvider:
    """Stub ORD provider — all methods log a warning and return synthetic values."""

    async def register_advertiser(self, user_id: int, name: str, inn: str | None) -> str:
        logger.warning("ORD stub: реальный провайдер не настроен (register_advertiser)")
        return f"STUB-ADV-{user_id}"

    async def register_platform(self, channel_id: int, channel_url: str, channel_name: str) -> str:
        logger.warning("ORD stub: реальный провайдер не настроен (register_platform)")
        return f"STUB-PLATFORM-{channel_id}"

    async def register_contract(
        self,
        placement_request_id: int,
        advertiser_ord_id: str,
        amount_rub: str,
        date_str: str,
    ) -> str:
        logger.warning("ORD stub: реальный провайдер не настроен (register_contract)")
        return f"STUB-CONTRACT-{placement_request_id}"

    async def register_creative(
        self,
        placement_request_id: int,
        ad_text: str,
        media_type: str,
        advertiser_ord_id: str,
    ) -> str:
        logger.warning("ORD stub: реальный провайдер не настроен (register_creative)")
        ts = int(datetime.now().timestamp())
        return f"STUB-ERID-{placement_request_id}-{ts}"

    async def report_publication(
        self,
        erid: str,
        published_at: datetime,
        placement_request_id: int,
    ) -> bool:
        logger.warning("ORD stub: реальный провайдер не настроен (report_publication)")
        return True

    async def get_status(self, erid: str) -> str:
        return "stub"
