"""
FastAPI router для настроек каналов (ChannelSettings).
"""

import logging
from datetime import time
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import CurrentUser, get_db_session
from src.constants.payments import OWNER_SHARE
from src.db.repositories.channel_settings_repo import ChannelSettingsRepo

logger = logging.getLogger(__name__)

router = APIRouter(tags=["channel-settings"])

# =============================================================================
# Schemas
# =============================================================================


def parse_time_str(value: str) -> time:
    """Парсинг строки времени в формате HH:MM."""
    try:
        return time.fromisoformat(value)
    except ValueError as e:
        raise ValueError(f"Invalid time format: {value}. Use HH:MM") from e


class ChannelSettingsResponse(BaseModel):
    """Ответ с настройками канала."""

    channel_id: int
    price_per_post: Decimal
    owner_payout: Decimal
    publish_start_time: str
    publish_end_time: str
    break_start_time: str | None = None
    break_end_time: str | None = None
    max_posts_per_day: int
    allow_format_post_24h: bool
    allow_format_post_48h: bool
    allow_format_post_7d: bool
    allow_format_pin_24h: bool
    allow_format_pin_48h: bool
    auto_accept_enabled: bool
    updated_at: str

    model_config = {"from_attributes": True}


class ChannelSettingsUpdateRequest(BaseModel):
    """Запрос на частичное обновление настроек."""

    price_per_post: int | None = Field(None, ge=100, description="Цена >= 100")
    publish_start_time: str | None = Field(None, description="HH:MM формат")
    publish_end_time: str | None = Field(None, description="HH:MM формат")
    break_start_time: str | None = Field(None, description="HH:MM или null")
    break_end_time: str | None = Field(None, description="HH:MM или null")
    max_posts_per_day: int | None = Field(None, ge=1, le=5, description="1-5")
    allow_format_post_24h: bool | None = None
    allow_format_post_48h: bool | None = None
    allow_format_post_7d: bool | None = None
    allow_format_pin_24h: bool | None = None
    allow_format_pin_48h: bool | None = None
    auto_accept_enabled: bool | None = None

    @field_validator("publish_start_time", "publish_end_time", "break_start_time", "break_end_time")
    @classmethod
    def validate_time_format(cls, v: str | None) -> str | None:
        """Валидация формата времени."""
        if v is None:
            return v
        try:
            time.fromisoformat(v)
        except ValueError as e:
            raise ValueError(f"Invalid time format: {v}. Use HH:MM") from e
        return v


# =============================================================================
# Endpoints
# =============================================================================


@router.get(
    "/",
    responses={
        404: {"description": "Channel not found"},
        403: {"description": "Not channel owner"},
    },
)
async def get_channel_settings(
    channel_id: int,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ChannelSettingsResponse:
    """Получить настройки канала."""
    from src.db.models.telegram_chat import TelegramChat

    # Проверка что канал принадлежит пользователю
    channel = await session.get(TelegramChat, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    if channel.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not channel owner")

    # Получить или создать настройки
    repo = ChannelSettingsRepo(session)
    settings = await repo.get_or_create(channel_id)

    # Вычислить payout владельца
    owner_payout = settings.price_per_post * OWNER_SHARE

    return ChannelSettingsResponse(
        channel_id=settings.channel_id,
        price_per_post=settings.price_per_post,
        owner_payout=owner_payout,
        publish_start_time=settings.publish_start_time.isoformat(),
        publish_end_time=settings.publish_end_time.isoformat(),
        break_start_time=settings.break_start_time.isoformat()
        if settings.break_start_time
        else None,
        break_end_time=settings.break_end_time.isoformat() if settings.break_end_time else None,
        max_posts_per_day=settings.max_posts_per_day,
        allow_format_post_24h=settings.allow_format_post_24h,
        allow_format_post_48h=settings.allow_format_post_48h,
        allow_format_post_7d=settings.allow_format_post_7d,
        allow_format_pin_24h=settings.allow_format_pin_24h,
        allow_format_pin_48h=settings.allow_format_pin_48h,
        auto_accept_enabled=settings.auto_accept_enabled,
        updated_at=settings.updated_at.isoformat(),
    )


def _validate_time_ranges(request: ChannelSettingsUpdateRequest) -> None:
    """Validate publish and break time range ordering."""
    if request.publish_start_time and request.publish_end_time:
        start = time.fromisoformat(request.publish_start_time)
        end = time.fromisoformat(request.publish_end_time)
        if end <= start:
            raise HTTPException(status_code=422, detail="end_time must be greater than start_time")

    if request.break_start_time and request.break_end_time:
        break_start = time.fromisoformat(request.break_start_time)
        break_end = time.fromisoformat(request.break_end_time)
        if break_end <= break_start:
            raise HTTPException(
                status_code=422, detail="break_end_time must be greater than break_start_time"
            )


def _build_update_data(request: ChannelSettingsUpdateRequest) -> dict:
    """Build a dict of only the fields present in the partial-update request."""
    update_data: dict = {}
    if request.price_per_post is not None:
        update_data["price_per_post"] = Decimal(str(request.price_per_post))
    if request.publish_start_time is not None:
        update_data["publish_start_time"] = time.fromisoformat(request.publish_start_time)
    if request.publish_end_time is not None:
        update_data["publish_end_time"] = time.fromisoformat(request.publish_end_time)
    if request.break_start_time is not None:
        update_data["break_start_time"] = time.fromisoformat(request.break_start_time)
    if request.break_end_time is not None:
        update_data["break_end_time"] = time.fromisoformat(request.break_end_time)
    if request.max_posts_per_day is not None:
        update_data["max_posts_per_day"] = request.max_posts_per_day
    if request.allow_format_post_24h is not None:
        update_data["allow_format_post_24h"] = request.allow_format_post_24h
    if request.allow_format_post_48h is not None:
        update_data["allow_format_post_48h"] = request.allow_format_post_48h
    if request.allow_format_post_7d is not None:
        update_data["allow_format_post_7d"] = request.allow_format_post_7d
    if request.allow_format_pin_24h is not None:
        update_data["allow_format_pin_24h"] = request.allow_format_pin_24h
    if request.allow_format_pin_48h is not None:
        update_data["allow_format_pin_48h"] = request.allow_format_pin_48h
    if request.auto_accept_enabled is not None:
        update_data["auto_accept_enabled"] = request.auto_accept_enabled
    return update_data


@router.patch(
    "/",
    responses={
        404: {"description": "Channel not found"},
        403: {"description": "Not channel owner"},
        422: {"description": "Invalid time range"},
    },
)
async def update_channel_settings(
    channel_id: int,
    request: ChannelSettingsUpdateRequest,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ChannelSettingsResponse:
    """Частичное обновление настроек канала."""
    from src.db.models.telegram_chat import TelegramChat

    # Проверка что канал принадлежит пользователю
    channel = await session.get(TelegramChat, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    if channel.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not channel owner")

    _validate_time_ranges(request)

    repo = ChannelSettingsRepo(session)
    update_data = _build_update_data(request)
    settings = await repo.update_settings(channel_id, **update_data)

    # Вычислить payout владельца
    owner_payout = settings.price_per_post * OWNER_SHARE

    return ChannelSettingsResponse(
        channel_id=settings.channel_id,
        price_per_post=settings.price_per_post,
        owner_payout=owner_payout,
        publish_start_time=settings.publish_start_time.isoformat(),
        publish_end_time=settings.publish_end_time.isoformat(),
        break_start_time=settings.break_start_time.isoformat()
        if settings.break_start_time
        else None,
        break_end_time=settings.break_end_time.isoformat() if settings.break_end_time else None,
        max_posts_per_day=settings.max_posts_per_day,
        allow_format_post_24h=settings.allow_format_post_24h,
        allow_format_post_48h=settings.allow_format_post_48h,
        allow_format_post_7d=settings.allow_format_post_7d,
        allow_format_pin_24h=settings.allow_format_pin_24h,
        allow_format_pin_48h=settings.allow_format_pin_48h,
        auto_accept_enabled=settings.auto_accept_enabled,
        updated_at=settings.updated_at.isoformat(),
    )
