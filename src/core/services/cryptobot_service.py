"""
Сервис для работы с CryptoBot API (pay.crypt.bot).
Документация: https://help.crypt.bot/crypto-pay-api

Получить токен: @CryptoBot → My Apps → Create App
"""

import logging
from dataclasses import dataclass

import httpx

from src.config.settings import settings

logger = logging.getLogger(__name__)

CRYPTOBOT_API_URL = "https://pay.crypt.bot/api"
# Для тестирования: "https://testnet-pay.crypt.bot/api"

SUPPORTED_CURRENCIES = ["USDT", "TON", "BTC", "ETH", "LTC", "USDC"]


@dataclass
class Invoice:
    """Модель инвойса CryptoBot."""

    invoice_id: str
    status: str  # active | paid | expired | cancelled
    currency: str
    amount: float
    pay_url: str
    created_at: str
    paid_at: str | None = None


class CryptoBotService:
    """
    Клиент для CryptoBot Crypto Pay API.

    Usage:
        service = CryptoBotService()
        invoice = await service.create_invoice(currency="USDT", amount=10.0, payload="user:123")
        # Отправь invoice.pay_url пользователю
        # После оплаты — проверяй через get_invoice или webhook
    """

    def __init__(self) -> None:
        """Инициализация сервиса."""
        self.token = settings.cryptobot_token or ""
        self.headers = {"Crypto-Pay-API-Token": self.token} if self.token else {}

    async def _request(self, method: str, endpoint: str, **kwargs) -> dict:
        """Выполнить запрос к API."""
        if not self.token:
            raise ValueError("CryptoBot token not configured")

        url = f"{CRYPTOBOT_API_URL}/{endpoint}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(method, url, headers=self.headers, **kwargs)

            # Явная обработка HTTP 400 с подробным логированием
            if response.status_code == 400:
                error_body = await response.aread()
                logger.error(
                    f"CryptoBot API returned 400. "
                    f"URL: {url}, "
                    f"Method: {method}, "
                    f"Payload: {kwargs.get('json', kwargs.get('params', {}))}, "
                    f"Response: {error_body.decode('utf-8', errors='replace')}"
                )
                raise ValueError(f"CryptoBot API error 400: {error_body.decode('utf-8', errors='replace')}")

            response.raise_for_status()
            data = response.json()
            if not data.get("ok"):
                error = data.get("error", {})
                raise ValueError(
                    f"CryptoBot API error: {error.get('name', 'Unknown')} - "
                    f"{error.get('message', '')}"
                )
            return data["result"]

    async def create_invoice(
        self,
        currency: str,
        amount: float,
        payload: str = "",
        description: str = "Пополнение кредитов Market Bot",
        expires_in: int = 3600,
        bot_username: str = "RekharborBot",  # URL для кнопки после оплаты
    ) -> Invoice:
        """
        Создать счёт на оплату.

        Args:
            currency: Валюта (USDT, TON, BTC, ETH, LTC).
            amount: Сумма в указанной валюте.
            payload: Произвольные данные (например "user:123:credits:300").
            description: Описание платежа (видит пользователь).
            expires_in: Время жизни счёта в секундах (default 1 час).
            bot_username: Username бота для кнопки возврата.

        Returns:
            Invoice с pay_url для отправки пользователю.
        """
        if currency not in SUPPORTED_CURRENCIES:
            raise ValueError(f"Unsupported currency: {currency}. Supported: {SUPPORTED_CURRENCIES}")

        result = await self._request(
            "POST",
            "createInvoice",
            json={
                "currency_type": "crypto",
                "asset": currency,
                "amount": str(amount),
                "payload": payload,
                "description": description,
                "expires_in": expires_in,
                "allow_anonymous": True,
                "paid_btn_name": "Вернуться в бот",
                "paid_btn_url": f"https://t.me/{bot_username}",
            },
        )

        return Invoice(
            invoice_id=str(result["invoice_id"]),
            status=result["status"],
            currency=result["asset"],
            amount=float(result["amount"]),
            pay_url=result["pay_url"],
            created_at=result["created_at"],
        )

    async def get_invoice(self, invoice_id: str) -> Invoice:
        """Получить статус счёта по ID."""
        result = await self._request(
            "GET",
            "getInvoices",
            params={"invoice_ids": invoice_id},
        )
        items = result.get("items", [])
        if not items:
            raise ValueError(f"Invoice {invoice_id} not found")
        item = items[0]
        return Invoice(
            invoice_id=str(item["invoice_id"]),
            status=item["status"],
            currency=item["asset"],
            amount=float(item["amount"]),
            pay_url=item["pay_url"],
            created_at=item["created_at"],
            paid_at=item.get("paid_at"),
        )

    def calculate_credits(self, currency: str, amount: float) -> int:
        """
        Рассчитать количество кредитов за указанную сумму.

        Args:
            currency: Валюта.
            amount: Сумма.

        Returns:
            Количество кредитов (целое число).
        """
        rate = settings.currency_rates.get(currency.upper(), 0)
        if rate == 0:
            raise ValueError(f"Unknown currency rate for {currency}")
        return int(amount * rate)

    def get_min_amount(self, currency: str, min_credits: int = 300) -> float:
        """
        Минимальная сумма для покупки min_credits кредитов.

        Args:
            currency: Валюта.
            min_credits: Минимальное количество кредитов.

        Returns:
            Минимальная сумма в валюте.
        """
        rate = settings.currency_rates.get(currency.upper(), 1)
        return round(min_credits / rate, 8)

    async def get_balance(self) -> dict[str, float]:
        """
        Получить балансы бота (для мониторинга).

        Returns:
            Словарь {валюта: баланс}.
        """
        result = await self._request("GET", "getBalance")
        return {item["currency_code"]: float(item["available"]) for item in result}


# Синглтон
cryptobot_service = CryptoBotService()
