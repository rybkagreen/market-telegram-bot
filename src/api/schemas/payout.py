"""
Pydantic схемы для выплат (PayoutRequest).

Используются в API роутере /api/payouts для валидации
входящих данных и форматирования ответов.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class PayoutStatus(str, Enum):
    """Статусы заявок на выплату."""

    pending = "pending"
    processing = "processing"
    paid = "paid"
    rejected = "rejected"
    cancelled = "cancelled"


class PayoutCreate(BaseModel):
    """Схема создания заявки на выплату."""

    amount: Decimal = Field(..., gt=0, description="Сумма выплаты (gross)")
    payment_details: str = Field(
        ..., min_length=5, max_length=512, description="Реквизиты для выплаты"
    )


class PayoutResponse(BaseModel):
    """Ответ с данными заявки на выплату."""

    id: int
    owner_id: int
    gross_amount: Decimal
    fee_amount: Decimal
    net_amount: Decimal
    status: PayoutStatus
    requisites: str
    admin_id: int | None = None
    processed_at: datetime | None = None
    rejection_reason: str | None = None
    ndfl_withheld: Decimal | None = None
    npd_status: str | None = None
    npd_receipt_number: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RejectPayoutRequest(BaseModel):
    """Запрос на отклонение выплаты."""

    reason: str = Field(..., min_length=1, max_length=512, description="Причина отклонения")
