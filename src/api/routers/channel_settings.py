"""
FastAPI router для настроек каналов (ChannelSettings).
"""

import logging
from datetime import time
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import CurrentUser, get_db_session
from src.db.repositories.channel_settings_repo import ChannelSettingsRepo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/channels/{channel_id}/settings", tags=["channel-settings"])

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
    start_time: str
    end_time: str
    break_start_time: str | None
    break_end_time: str | None
    max_posts_per_day: int
    min_hours_between_posts: int
    daily_package_enabled: bool
    daily_package_discount: int
    weekly_package_enabled: bool
    weekly_package_discount: int
    subscription_enabled: bool
    sub_min_days: int
    sub_max_days: int
    auto_accept_enabled: bool
    updated_at: str

    model_config = {"from_attributes": True}


class ChannelSettingsUpdateRequest(BaseModel):
    """Запрос на частичное обновление настроек."""

    price_per_post: int | None = Field(None, ge=100, description="Цена >= 100")
    start_time: str | None = Field(None, description="HH:MM формат")
    end_time: str | None = Field(None, description="HH:MM формат")
    break_start_time: str | None = Field(None, description="HH:MM или null")
    break_end_time: str | None = Field(None, description="HH:MM или null")
    max_posts_per_day: int | None = Field(None, ge=1, le=5, description="1-5")
    min_hours_between_posts: int | None = Field(None, ge=2, le=8, description="2-8")
    daily_package_enabled: bool | None = None
    daily_package_discount: int | None = Field(None, ge=1, le=50, description="1-50")
    weekly_package_enabled: bool | None = None
    weekly_package_discount: int | None = Field(None, ge=1, le=50, description="1-50")
    subscription_enabled: bool | None = None
    sub_min_days: int | None = Field(None, ge=7, description=">= 7")
    sub_max_days: int | None = Field(None, le=365, description="<= 365")
    auto_accept_enabled: bool | None = None

    @field_validator("start_time", "end_time", "break_start_time", "break_end_time")
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


@router.get("/", response_model=ChannelSettingsResponse)
async def get_channel_settings(
    channel_id: int,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
) -> ChannelSettingsResponse:
    """Получить настройки канала."""
    from src.db.models.analytics import TelegramChat

    # Проверка что канал принадлежит пользователю
    channel = await session.get(TelegramChat, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    if channel.owner_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not channel owner")

    # Получить или создать настройки
    repo = ChannelSettingsRepo(session)
    settings = await repo.get_or_create_default(channel_id, current_user.id)

    # Вычислить payout владельца
    owner_payout = settings.price_per_post * Decimal("0.80")

    return ChannelSettingsResponse(
        channel_id=settings.channel_id,
        price_per_post=settings.price_per_post,
        owner_payout=owner_payout,
        start_time=settings.publish_start_time.isoformat(),
        end_time=settings.publish_end_time.isoformat(),
        break_start_time=settings.break_start_time.isoformat() if settings.break_start_time else None,
        break_end_time=settings.break_end_time.isoformat() if settings.break_end_time else None,
        max_posts_per_day=settings.daily_package_max,
        min_hours_between_posts=4,  # Константа
        daily_package_enabled=settings.daily_package_enabled,
        daily_package_discount=settings.daily_package_discount,
        weekly_package_enabled=settings.weekly_package_enabled,
        weekly_package_discount=settings.weekly_package_discount,
        subscription_enabled=settings.subscription_enabled,
        sub_min_days=settings.subscription_min_days,
        sub_max_days=settings.subscription_max_days,
        auto_accept_enabled=settings.auto_accept_enabled,
        updated_at=settings.updated_at.isoformat(),
    )


@router.patch("/", response_model=ChannelSettingsResponse)
async def update_channel_settings(
    channel_id: int,
    request: ChannelSettingsUpdateRequest,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
) -> ChannelSettingsResponse:
    """Частичное обновление настроек канала."""
    from src.db.models.analytics import TelegramChat

    # Проверка что канал принадлежит пользователю
    channel = await session.get(TelegramChat, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    if channel.owner_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not channel owner")

    # Валидация start_time < end_time
    if request.start_time and request.end_time:
        start = time.fromisoformat(request.start_time)
        end = time.fromisoformat(request.end_time)
        if end <= start:
            raise HTTPException(
                status_code=422, detail="end_time must be greater than start_time"
            )

    # Валидация break times
    if request.break_start_time and request.break_end_time:
        break_start = time.fromisoformat(request.break_start_time)
        break_end = time.fromisoformat(request.break_end_time)
        if break_end <= break_start:
            raise HTTPException(
                status_code=422, detail="break_end_time must be greater than break_start_time"
            )

    # Валидация sub_max_days > sub_min_days
    if request.sub_min_days and request.sub_max_days and request.sub_max_days <= request.sub_min_days:
        raise HTTPException(
            status_code=422, detail="sub_max_days must be greater than sub_min_days"
        )

    # Обновление настроек
    repo = ChannelSettingsRepo(session)

    update_data = {}
    if request.price_per_post is not None:
        update_data["price_per_post"] = Decimal(str(request.price_per_post))
    if request.start_time is not None:
        update_data["publish_start_time"] = time.fromisoformat(request.start_time)
    if request.end_time is not None:
        update_data["publish_end_time"] = time.fromisoformat(request.end_time)
    if request.break_start_time is not None:
        update_data["break_start_time"] = (
            time.fromisoformat(request.break_start_time) if request.break_start_time else None
        )
    if request.break_end_time is not None:
        update_data["break_end_time"] = (
            time.fromisoformat(request.break_end_time) if request.break_end_time else None
        )
    if request.max_posts_per_day is not None:
        update_data["daily_package_max"] = request.max_posts_per_day
    if request.min_hours_between_posts is not None:
        # Это поле не существует в модели, игнорируем
        pass
    if request.daily_package_enabled is not None:
        update_data["daily_package_enabled"] = request.daily_package_enabled
    if request.daily_package_discount is not None:
        update_data["daily_package_discount"] = request.daily_package_discount
    if request.weekly_package_enabled is not None:
        update_data["weekly_package_enabled"] = request.weekly_package_enabled
    if request.weekly_package_discount is not None:
        update_data["weekly_package_discount"] = request.weekly_package_discount
    if request.subscription_enabled is not None:
        update_data["subscription_enabled"] = request.subscription_enabled
    if request.sub_min_days is not None:
        update_data["subscription_min_days"] = request.sub_min_days
    if request.sub_max_days is not None:
        update_data["subscription_max_days"] = request.sub_max_days
    if request.auto_accept_enabled is not None:
        update_data["auto_accept_enabled"] = request.auto_accept_enabled

    settings = await repo.upsert(channel_id, current_user.id, **update_data)

    # Вычислить payout владельца
    owner_payout = settings.price_per_post * Decimal("0.80")

    return ChannelSettingsResponse(
        channel_id=settings.channel_id,
        price_per_post=settings.price_per_post,
        owner_payout=owner_payout,
        start_time=settings.publish_start_time.isoformat(),
        end_time=settings.publish_end_time.isoformat(),
        break_start_time=settings.break_start_time.isoformat() if settings.break_start_time else None,
        break_end_time=settings.break_end_time.isoformat() if settings.break_end_time else None,
        max_posts_per_day=settings.daily_package_max,
        min_hours_between_posts=4,
        daily_package_enabled=settings.daily_package_enabled,
        daily_package_discount=settings.daily_package_discount,
        weekly_package_enabled=settings.weekly_package_enabled,
        weekly_package_discount=settings.weekly_package_discount,
        subscription_enabled=settings.subscription_enabled,
        sub_min_days=settings.subscription_min_days,
        sub_max_days=settings.subscription_max_days,
        auto_accept_enabled=settings.auto_accept_enabled,
        updated_at=settings.updated_at.isoformat(),
    )
