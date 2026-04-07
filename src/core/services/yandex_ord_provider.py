"""
YandexOrdProvider — реальная интеграция с Яндекс ОРД API v7.

Использует httpx.AsyncClient с Bearer auth.
Все вызовы идемпотентны через детерминированные ID (upsert на стороне ОРД).

API документация: https://ord.yandex.ru/api/doc (тестовый стенд)
"""

import logging
from datetime import datetime

import httpx

from src.core.services.ord_provider import OrdProvider

logger = logging.getLogger(__name__)

# ─── Мажоритеты ─────────────────────────────────────────────────

ORG_TYPE_MAP: dict[str, str] = {
    "legal_entity": "ul",
    "individual_entrepreneur": "ip",
    "self_employed": "fl",
    "individual": "fl",
}

SUCCESS_STATUSES = {"ERIR sync success", "ERIR async success"}
ERROR_STATUSES = {"ERIR sync error", "ERIR async error", "ORD rejected"}


class OrdRegistrationError(Exception):
    """Raised when Yandex ORD API returns a non-recoverable error."""


class YandexOrdProvider(OrdProvider):
    """Реальный провайдер Яндекс ОРД API v7."""

    def __init__(
        self, api_key: str, base_url: str, rekharbor_org_id: str, rekharbor_inn: str
    ) -> None:
        self._api_key = api_key
        # Убираем trailing slash если есть
        self._base_url = base_url.rstrip("/")
        self._rekharbor_org_id = rekharbor_org_id
        self._rekharbor_inn = rekharbor_inn
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30.0,
        )
        logger.info(
            "YandexOrdProvider initialized (base_url=%s, key=...%s)", self._base_url, api_key[-4:]
        )

    async def close(self) -> None:
        await self._client.aclose()

    # ─── Internal helpers ───────────────────────────────────────

    async def _request(
        self,
        method: str,
        path: str,
        json_body: dict | None = None,
        params: dict | None = None,
    ) -> dict:
        """Выполнить HTTP-запрос к ОРД с обработкой ошибок."""
        try:
            resp = await self._client.request(method, path, json=json_body, params=params)
        except httpx.ConnectTimeout as e:
            raise OrdRegistrationError(f"Connection timeout to ORD API: {e}") from e
        except httpx.RequestError as e:
            raise OrdRegistrationError(f"Request error to ORD API: {e}") from e

        # 5xx — retry (caller должен обрабатывать)
        if resp.status_code >= 500:
            raise OrdRegistrationError(f"ORD server error {resp.status_code}: {resp.text[:500]}")

        # 422 — валидация
        if resp.status_code == 422:
            logger.error("ORD validation error (422): %s", resp.text[:1000])
            raise OrdRegistrationError(f"ORD validation error (422): {resp.text[:500]}")

        # 4xx — ошибка клиента
        if resp.status_code >= 400:
            raise OrdRegistrationError(f"ORD client error {resp.status_code}: {resp.text[:500]}")

        return resp.json()

    # ─── Org type mapping ──────────────────────────────────────

    @staticmethod
    def _map_org_type(legal_status: str) -> str:
        return ORG_TYPE_MAP.get(legal_status, "fl")

    @staticmethod
    def _determine_vat_rate(org_type: str) -> str:
        """Определить ставку НДС по типу организации.
        ЮЛ (ul) — НДС 22%, остальные — без НДС (100).
        """
        return "22" if org_type == "ul" else "100"

    # ─── Protocol methods ──────────────────────────────────────

    async def register_advertiser(self, user_id: int, name: str, inn: str | None) -> str:
        """POST /api/v7/organization — зарегистрировать рекламодателя.

        Детерминированный ID: 'org-{user_id}'.
        При повторной отправке обновляет существующую организацию (upsert).
        """
        org_id = f"org-{user_id}"
        payload: dict = {
            "id": org_id,
            "inn": inn or "",
            "isOrs": False,
            "isRr": False,
        }
        if name:
            payload["name"] = name

        await self._request("POST", "/api/v7/organization", json_body=payload)
        logger.info("ORD: registered advertiser org_id=%s", org_id)
        return org_id

    async def register_platform(self, channel_id: int, channel_url: str, channel_name: str) -> str:
        """POST /api/v7/platforms — зарегистрировать Telegram-канал как площадку.

        platform_type = 'site', URL = https://t.me/{username}.
        Детерминированный ID: 'platform-{channel_id}'.
        """
        platform_id = f"platform-{channel_id}"
        payload: dict = {
            "organizationId": self._rekharbor_org_id,
            "platforms": [
                {
                    "platformId": platform_id,
                    "type": "site",
                    "name": channel_name,
                    "url": channel_url,
                    "isOwned": False,
                }
            ],
        }

        await self._request("POST", "/api/v7/platforms", json_body=payload)
        logger.info("ORD: registered platform platform_id=%s (channel=%s)", platform_id, channel_id)
        return platform_id

    async def register_contract(
        self,
        placement_request_id: int,
        advertiser_ord_id: str,
        amount_rub: str,
        date_str: str,
    ) -> str:
        """POST /api/v7/contract — зарегистрировать договор между РД и РР.

        РекХарбор = РР (исполнитель), рекламодатель = РД (заказчик).
        Детерминированный ID: 'contract-{placement_request_id}'.
        """
        contract_id = f"contract-{placement_request_id}"
        payload: dict = {
            "id": contract_id,
            "type": "contract",
            "contractorId": self._rekharbor_org_id,
            "clientId": advertiser_ord_id,
            "isRegReport": True,
            "date": date_str,
            "amount": amount_rub,
            "subjectType": "distribution",
        }

        await self._request("POST", "/api/v7/contract", json_body=payload)
        logger.info("ORD: registered contract contract_id=%s", contract_id)
        return contract_id

    async def register_creative(
        self,
        placement_request_id: int,
        ad_text: str,
        media_type: str,
        advertiser_ord_id: str,
    ) -> str:
        """POST /api/v7/creative — зарегистрировать креатив, получить token (= erid).

        Возвращает token — это маркировочный erid для вставки в текст рекламы.
        Также response содержит requestId для последующего polling статуса ЕРИР.

        Важно: token !== erir_id. Token возвращается немедленно, но регистрация
        в ЕРИР завершается асинхронно (нужно polling через /status).
        """
        creative_id = f"creative-{placement_request_id}"
        contract_id = f"contract-{placement_request_id}"

        # Определяем форму креатива
        if media_type in ("video",):
            creative_form = "text_video_block"
        elif media_type in ("photo", "image"):
            creative_form = "text_graphic_block"
        else:
            creative_form = "text_block"

        payload: dict = {
            "id": creative_id,
            "creativeType": "creative",
            "form": creative_form,
            "isSocial": False,
            "isSocialQuota": False,
            "contractIds": [contract_id],
            "textData": [ad_text],
            "kktuCodes": ["30.10.1"],  # Размещение рекламы
        }

        result = await self._request("POST", "/api/v7/creative", json_body=payload)

        # Token — это erid для маркировки
        token = result.get("token", "")
        request_id = result.get("requestId", "")

        if not token:
            raise OrdRegistrationError(f"ORD creative response missing 'token' field: {result}")

        logger.info(
            "ORD: registered creative creative_id=%s, token=%s...%s, request_id=%s",
            creative_id,
            token[:8],
            token[-4:] if len(token) > 12 else "",
            request_id,
        )
        # Возвращаем token как erid. request_id сохраняется отдельно.
        # Caller должен сохранить: erid=token, yandex_request_id=request_id
        return token

    async def report_publication(
        self,
        erid: str,
        published_at: datetime,
        placement_request_id: int,
    ) -> bool:
        """POST /api/v7/statistics — репорт факта публикации.

        amount_rub берётся из placement_request (caller должен передать).
        Для MVP используем заглушку amount=1 (факт — 1 публикация).
        """
        creative_id = f"creative-{placement_request_id}"
        channel_id_str = str(placement_request_id)  # caller может передать channel_id

        pub_date = published_at.date().isoformat()

        payload: dict = {
            "statistics": [
                {
                    "creativeId": creative_id,
                    "platformId": f"platform-{channel_id_str}",
                    "dateStartFact": pub_date,
                    "dateEndFact": pub_date,
                    "dateStartPlan": pub_date,
                    "dateEndPlan": pub_date,
                    "impsFact": 1,
                    "impsPlan": 1,
                    "type": "other",
                    "amount": {
                        "excludingVat": "0",
                        "vatRate": "100",
                        "vat": "0",
                        "includingVat": "0",
                    },
                }
            ]
        }

        await self._request("POST", "/api/v7/statistics", json_body=payload)
        logger.info(
            "ORD: reported publication erid=%s...%s", erid[:8], erid[-4:] if len(erid) > 12 else ""
        )
        return True

    async def get_status(self, request_id: str) -> str:
        """GET /api/v7/status?reqid={request_id} — polling статуса ЕРИР.

        Returns статус из response (строка).
        """
        result = await self._request("GET", "/api/v7/status", params={"reqid": request_id})
        status = result.get("status", "unknown")
        logger.debug("ORD status polling: reqid=%s, status=%s", request_id, status)
        return status

    async def check_erir_status(self, request_id: str) -> dict:
        """Extended status check — возвращает полный ответ для analysis.

        Caller проверяет:
        - status in SUCCESS_STATUSES → erir_confirmed
        - status in ERROR_STATUSES → erir_failed
        - иначе → pending (retry)
        """
        return await self._request("GET", "/api/v7/status", params={"reqid": request_id})
