"""
Campaigns router для управления рекламными кампаниями.
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.api.dependencies import CurrentUser
from src.db.models.campaign import CampaignStatus
from src.db.repositories.campaign_repo import CampaignRepository
from src.db.session import async_session_factory

logger = logging.getLogger(__name__)

router = APIRouter()


# === Pydantic схемы ===

class CampaignCreate(BaseModel):
    """Создание кампании."""

    title: str = Field(..., min_length=1, max_length=255)
    text: str = Field(..., min_length=1, max_length=5000)
    ai_description: str | None = None
    filters_json: dict[str, Any] | None = None
    scheduled_at: str | None = None


class CampaignUpdate(BaseModel):
    """Обновление кампании."""

    title: str | None = Field(None, min_length=1, max_length=255)
    text: str | None = Field(None, min_length=1, max_length=5000)
    filters_json: dict[str, Any] | None = None
    scheduled_at: str | None = None


class CampaignResponse(BaseModel):
    """Ответ с данными кампании."""

    id: int
    title: str
    text: str
    status: str
    filters_json: dict[str, Any] | None
    scheduled_at: str | None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class CampaignListResponse(BaseModel):
    """Список кампаний с пагинацией."""

    campaigns: list[CampaignResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


# === Эндпоинты ===

@router.post("", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    campaign_data: CampaignCreate,
    current_user: CurrentUser,
):
    """
    Создать новую рекламную кампанию.

    Args:
        campaign_data: Данные кампании.
        current_user: Текущий пользователь.

    Returns:
        Созданная кампания.
    """
    async with async_session_factory() as session:
        campaign_repo = CampaignRepository(session)

        # Создаём кампанию со статусом draft
        campaign = await campaign_repo.create({
            "user_id": current_user.id,
            "title": campaign_data.title,
            "text": campaign_data.text,
            "status": CampaignStatus.DRAFT,
            "filters_json": campaign_data.filters_json,
            "scheduled_at": campaign_data.scheduled_at,
        })

        logger.info(f"Campaign {campaign.id} created by user {current_user.id}")

        return campaign


@router.get("", response_model=CampaignListResponse)
async def get_campaigns(  # noqa: B008
    current_user: CurrentUser,
    status: CampaignStatus | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """
    Получить список кампаний пользователя.

    Args:
        current_user: Текущий пользователь.
        status: Фильтр по статусу.
        page: Номер страницы.
        page_size: Размер страницы.

    Returns:
        Список кампаний с пагинацией.
    """
    async with async_session_factory() as session:
        campaign_repo = CampaignRepository(session)

        campaigns, total = await campaign_repo.get_by_user(
            user_id=current_user.id,
            status=status,
            page=page,
            page_size=page_size,
        )

        has_more = (page * page_size) < total

        return CampaignListResponse(
            campaigns=[CampaignResponse.model_validate(c) for c in campaigns],
            total=total,
            page=page,
            page_size=page_size,
            has_more=has_more,
        )


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: int,
    current_user: CurrentUser,
):
    """
    Получить кампанию по ID.

    Args:
        campaign_id: ID кампании.
        current_user: Текущий пользователь.

    Returns:
        Данные кампании.
    """
    async with async_session_factory() as session:
        campaign_repo = CampaignRepository(session)
        campaign = await campaign_repo.get_by_id(campaign_id)

        if not campaign:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campaign not found",
            )

        # Проверяем принадлежность
        if campaign.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

        return campaign


@router.patch("/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: int,
    campaign_data: CampaignUpdate,
    current_user: CurrentUser,
):
    """
    Обновить кампанию.

    Args:
        campaign_id: ID кампании.
        campaign_data: Данные для обновления.
        current_user: Текущий пользователь.

    Returns:
        Обновлённая кампания.
    """
    async with async_session_factory() as session:
        campaign_repo = CampaignRepository(session)
        campaign = await campaign_repo.get_by_id(campaign_id)

        if not campaign:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campaign not found",
            )

        if campaign.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

        # Можно обновлять только draft кампании
        if campaign.status != CampaignStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can only update draft campaigns",
            )

        # Обновляем
        update_data = campaign_data.model_dump(exclude_unset=True)
        updated = await campaign_repo.update(campaign_id, update_data)

        return updated


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_campaign(
    campaign_id: int,
    current_user: CurrentUser,
):
    """
    Удалить кампанию.

    Args:
        campaign_id: ID кампании.
        current_user: Текущий пользователь.
    """
    async with async_session_factory() as session:
        campaign_repo = CampaignRepository(session)
        campaign = await campaign_repo.get_by_id(campaign_id)

        if not campaign:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campaign not found",
            )

        if campaign.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

        await campaign_repo.delete(campaign_id)


@router.post("/{campaign_id}/start")
async def start_campaign(
    campaign_id: int,
    current_user: CurrentUser,
):
    """
    Запустить кампанию.

    Args:
        campaign_id: ID кампании.
        current_user: Текущий пользователь.

    Returns:
        Статус операции.
    """
    from src.tasks.mailing_tasks import send_campaign

    async with async_session_factory() as session:
        campaign_repo = CampaignRepository(session)
        campaign = await campaign_repo.get_by_id(campaign_id)

        if not campaign:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campaign not found",
            )

        if campaign.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

        # Обновляем статус на queued
        await campaign_repo.update_status(campaign_id, CampaignStatus.QUEUED)

        # Отправляем задачу в Celery
        send_campaign.delay(campaign_id)

        logger.info(f"Campaign {campaign_id} started by user {current_user.id}")

        return {"status": "queued", "campaign_id": campaign_id}


@router.post("/{campaign_id}/cancel")
async def cancel_campaign(
    campaign_id: int,
    current_user: CurrentUser,
):
    """
    Отменить кампанию.

    Args:
        campaign_id: ID кампании.
        current_user: Текущий пользователь.

    Returns:
        Статус операции.
    """
    async with async_session_factory() as session:
        campaign_repo = CampaignRepository(session)
        campaign = await campaign_repo.get_by_id(campaign_id)

        if not campaign:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campaign not found",
            )

        if campaign.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

        # Можно отменить только queued или running
        if campaign.status not in [CampaignStatus.QUEUED, CampaignStatus.RUNNING]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel campaign with status {campaign.status.value}",
            )

        await campaign_repo.update_status(
            campaign_id,
            CampaignStatus.CANCELLED,
        )

        logger.info(f"Campaign {campaign_id} cancelled by user {current_user.id}")

        return {"status": "cancelled", "campaign_id": campaign_id}
