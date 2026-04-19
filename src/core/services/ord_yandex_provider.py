"""
Yandex ORD Provider implementation for production use.
"""

import logging
from datetime import datetime

from src.core.services.ord_provider import OrdProvider

logger = logging.getLogger(__name__)


class YandexOrdProvider(OrdProvider):
    _NOT_IMPL_MSG = "Yandex ORD integration required"

    def __init__(self, api_key: str, api_url: str):
        self.api_key = api_key
        self.api_url = api_url.rstrip('/')

    async def register_advertiser(self, user_id: int, name: str, inn: str | None) -> str:
        raise NotImplementedError(self._NOT_IMPL_MSG)

    async def register_platform(self, channel_id: int, channel_url: str, channel_name: str) -> str:
        raise NotImplementedError(self._NOT_IMPL_MSG)

    async def register_contract(self, placement_request_id: int, advertiser_ord_id: str, amount_rub: str, date_str: str) -> str:
        raise NotImplementedError(self._NOT_IMPL_MSG)

    async def register_creative(self, placement_request_id: int, ad_text: str, media_type: str, advertiser_ord_id: str) -> str:
        raise NotImplementedError(self._NOT_IMPL_MSG)

    async def report_publication(self, erid: str, published_at: datetime, placement_request_id: int) -> bool:
        raise NotImplementedError(self._NOT_IMPL_MSG)

    async def get_status(self, erid: str) -> str:
        raise NotImplementedError(self._NOT_IMPL_MSG)
