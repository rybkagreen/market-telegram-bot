"""
Campaigns router для управления рекламными кампаниями.
"""

import logging
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from src.api.dependencies import CurrentUser
from src.db.models.campaign import CampaignStatus
from src.db.models.mailing_log import MailingLog
from src.db.repositories.campaign_repo import CampaignRepository
from src.db.session import async_session_factory

logger = logging.getLogger(__name__)

router = APIRouter()

CampaignStatusLiteral = Literal["draft", "queued", "running", "done", "error", "paused", "cancelled"]


# === Pydantic схемы ===


class CampaignFiltersInput(BaseModel):
    """Фильтры таргетинга для кампании."""

    topics: list[str] | None = None
    min_members: int = 0
    max_members: int = 1000000
    blacklist: list[int] | None = None


class CampaignCreate(BaseModel):
    """Создание кампании."""

    title: str = Field(..., min_length=1, max_length=255)
    text: str = Field(..., min_length=1, max_length=5000)
    topic: str | None = Field(None, max_length=100)
    ai_description: str | None = None
    filters: CampaignFiltersInput | None = None
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

        # Преобразуем фильтры в формат JSON
        filters_json = None
        if campaign_data.filters:
            filters_json = {
                "topics": campaign_data.filters.topics or [],
                "min_members": campaign_data.filters.min_members,
                "max_members": campaign_data.filters.max_members,
                "blacklist": campaign_data.filters.blacklist or [],
            }

        # Создаём кампанию со статусом draft
        campaign = await campaign_repo.create(
            {
                "user_id": current_user.id,
                "title": campaign_data.title,
                "text": campaign_data.text,
                "topic": campaign_data.topic,
                "status": CampaignStatus.DRAFT,
                "filters_json": filters_json,
                "scheduled_at": campaign_data.scheduled_at,
            }
        )

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


# ─── Mini App API ───────────────────────────────────────────────


class CampaignItem(BaseModel):
    """Краткая информация о кампании для списка."""

    id: int
    title: str
    status: str
    created_at: str
    sent_count: int
    target_count: int | None
    error_msg: str | None


class CampaignsListResponse(BaseModel):
    """Список кампаний для Mini App."""

    items: list[CampaignItem]
    total: int
    page: int
    pages: int


class CampaignStats(BaseModel):
    """Детальная статистика кампании."""

    campaign_id: int
    title: str
    status: str
    total_logs: int
    sent: int
    failed: int
    skipped: int
    success_rate: float
    started_at: str | None
    finished_at: str | None


@router.get("/list", response_model=CampaignsListResponse)
async def list_campaigns_mini_app(
    current_user: CurrentUser,
    status_filter: CampaignStatusLiteral | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
):
    """
    Список кампаний пользователя для Mini App.
    """
    async with async_session_factory() as session:
        # Базовый запрос
        base_q = select(Campaign).where(Campaign.user_id == current_user.id)
        count_q = select(func.count(Campaign.id)).where(
            Campaign.user_id == current_user.id
        )

        if status_filter:
            base_q = base_q.where(Campaign.status == status_filter)
            count_q = count_q.where(Campaign.status == status_filter)

        # Считаем total
        total_result = await session.execute(count_q)
        total = total_result.scalar() or 0

        # Получаем страницу
        offset = (page - 1) * limit
        result = await session.execute(
            base_q.order_by(Campaign.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        campaigns = result.scalars().all()

        # Для каждой кампании считаем sent_count
        items = []
        for camp in campaigns:
            sent_result = await session.execute(
                select(func.count(MailingLog.id)).where(
                    MailingLog.campaign_id == camp.id,
                    MailingLog.status == "sent",
                )
            )
            sent_count = sent_result.scalar() or 0

            items.append(CampaignItem(
                id=camp.id,
                title=camp.title or "Без названия",
                status=camp.status.value if hasattr(camp.status, "value") else str(camp.status),
                created_at=camp.created_at.isoformat() if camp.created_at else "",
                sent_count=sent_count,
                target_count=camp.total_chats or None,
                error_msg=getattr(camp, "error_message", None),
            ))

    pages = max(1, (total + limit - 1) // limit)
    return CampaignsListResponse(items=items, total=total, page=page, pages=pages)


@router.get("/{campaign_id}/stats", response_model=CampaignStats)
async def get_campaign_stats(
    campaign_id: int,
    current_user: CurrentUser,
):
    """Детальная статистика по одной кампании."""
    async with async_session_factory() as session:
        # Проверяем что кампания принадлежит пользователю
        result = await session.execute(
            select(Campaign).where(
                Campaign.id == campaign_id,
                Campaign.user_id == current_user.id,
            )
        )
        campaign = result.scalar_one_or_none()
        if not campaign:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campaign not found",
            )

        # Статистика из логов
        stats_result = await session.execute(
            select(
                func.count(MailingLog.id).label("total"),
                func.count(MailingLog.id).filter(
                    MailingLog.status == "sent"
                ).label("sent"),
                func.count(MailingLog.id).filter(
                    MailingLog.status == "failed"
                ).label("failed"),
                func.count(MailingLog.id).filter(
                    MailingLog.status == "skipped"
                ).label("skipped"),
                func.min(MailingLog.sent_at).label("started_at"),
                func.max(MailingLog.sent_at).label("finished_at"),
            ).where(MailingLog.campaign_id == campaign_id)
        )
        s = stats_result.one()

    total = s.total or 0
    sent = s.sent or 0
    success_rate = round(sent / total * 100, 1) if total > 0 else 0.0

    camp_status = (
        campaign.status.value
        if hasattr(campaign.status, "value")
        else str(campaign.status)
    )

    return CampaignStats(
        campaign_id=campaign.id,
        title=campaign.title or "Без названия",
        status=camp_status,
        total_logs=total,
        sent=sent,
        failed=s.failed or 0,
        skipped=s.skipped or 0,
        success_rate=success_rate,
        started_at=s.started_at.isoformat() if s.started_at else None,
        finished_at=s.finished_at.isoformat() if s.finished_at else None,
    )


# ─── Удалить кампанию ────────────────────────────────────────────


@router.delete("/{campaign_id}", status_code=204)
async def delete_campaign(
    campaign_id: int,
    current_user: CurrentUser,
) -> None:
    """
    Удалить кампанию.
    Можно удалить только черновики и завершённые/ошибочные кампании.
    Нельзя удалять running и queued.
    """
    async with async_session_factory() as session:
        result = await session.execute(
            select(Campaign).where(
                Campaign.id == campaign_id,
                Campaign.user_id == current_user.id,
            )
        )
        campaign = result.scalar_one_or_none()

        if not campaign:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campaign not found",
            )

        camp_status = (
            campaign.status.value
            if hasattr(campaign.status, "value")
            else str(campaign.status)
        )

        if camp_status in ("running", "queued"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot delete running or queued campaign",
            )

        await session.delete(campaign)
        await session.commit()


# ─── Дублировать кампанию ────────────────────────────────────────


class DuplicateResponse(BaseModel):
    id: int
    title: str


@router.post("/{campaign_id}/duplicate", response_model=DuplicateResponse)
async def duplicate_campaign(
    campaign_id: int,
    current_user: CurrentUser,
) -> DuplicateResponse:
    """
    Создать копию кампании в статусе 'draft'.
    Копируется: title, text, filters_json.
    Не копируется: статус, логи, scheduled_at.
    """
    async with async_session_factory() as session:
        result = await session.execute(
            select(Campaign).where(
                Campaign.id == campaign_id,
                Campaign.user_id == current_user.id,
            )
        )
        source = result.scalar_one_or_none()

        if not source:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campaign not found",
            )

        new_title = f"{source.title or 'Кампания'} (копия)"

        new_campaign = Campaign(
            user_id=current_user.id,
            title=new_title,
            text=source.text,
            status=CampaignStatus.DRAFT,
            filters_json=source.filters_json,
        )
        session.add(new_campaign)
        await session.commit()
        await session.refresh(new_campaign)

    return DuplicateResponse(id=new_campaign.id, title=new_title)
