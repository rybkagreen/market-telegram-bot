"""FastAPI router for act management and signing."""

import hashlib
import logging
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user, get_db_session
from src.db.models.act import Act
from src.db.models.placement_request import PlacementRequest
from src.db.models.user import User
from src.db.repositories.act_repo import ActRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/acts", tags=["acts"])

_ACT_NOT_FOUND = "Act not found"
_PLACEMENT_NOT_FOUND = "Placement not found"
_ACCESS_DENIED = "Access denied"


def _act_to_dict(act: Act) -> dict:
    """Build dict response from Act ORM object."""
    return {
        "id": act.id,
        "act_number": act.act_number,
        "act_type": act.act_type,
        "act_date": act.act_date.isoformat() if act.act_date else None,
        "sign_status": act.sign_status,
        "signed_at": act.signed_at.isoformat() if act.signed_at else None,
        "sign_method": act.sign_method,
        "pdf_url": f"/api/acts/{act.id}/pdf" if act.pdf_path else None,
        "placement_request_id": act.placement_request_id,
        "created_at": act.created_at.isoformat() if act.created_at else None,
    }


@router.get("/mine")
async def list_my_acts(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    limit: int = 50,
) -> dict:
    """Получить список актов текущего пользователя."""
    repo = ActRepository(session)
    acts = await repo.list_by_user(current_user.id, limit)
    items = [_act_to_dict(a) for a in acts]
    return {"items": items, "total": len(items)}


@router.get("/{act_id}")
async def get_act(
    act_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    """Получить акт по ID."""
    result = await session.execute(select(Act).join(PlacementRequest).where(Act.id == act_id))
    act = result.scalar_one_or_none()
    if not act:
        raise HTTPException(status_code=404, detail=_ACT_NOT_FOUND)

    # Проверка доступа
    placement = await session.get(PlacementRequest, act.placement_request_id)
    if not placement:
        raise HTTPException(status_code=404, detail=_PLACEMENT_NOT_FOUND)
    if placement.advertiser_id != current_user.id and placement.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail=_ACCESS_DENIED)

    return _act_to_dict(act)


@router.post("/{act_id}/sign")
async def sign_act(
    act_id: int,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    """Подписать акт (акцепт через интерфейс)."""
    result = await session.execute(select(Act).join(PlacementRequest).where(Act.id == act_id))
    act = result.scalar_one_or_none()
    if not act:
        raise HTTPException(status_code=404, detail=_ACT_NOT_FOUND)

    # Проверка доступа
    placement = await session.get(PlacementRequest, act.placement_request_id)
    if not placement:
        raise HTTPException(status_code=404, detail=_PLACEMENT_NOT_FOUND)
    if placement.advertiser_id != current_user.id and placement.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail=_ACCESS_DENIED)

    # Проверка статуса
    if act.sign_status in ("signed", "auto_signed"):
        raise HTTPException(status_code=400, detail=f"Act already {act.sign_status}")

    # Хэшируем IP и User-Agent
    client_ip = request.client.host if request.client else ""
    user_agent = request.headers.get("User-Agent", "")
    ip_hash = hashlib.sha256(client_ip.encode()).hexdigest()
    ua_hash = hashlib.sha256(user_agent.encode()).hexdigest()

    from datetime import UTC, datetime

    act.sign_status = "signed"
    act.signed_at = datetime.now(UTC)
    act.sign_method = "click_accept"
    act.ip_hash = ip_hash
    act.user_agent_hash = ua_hash

    await session.flush()
    await session.refresh(act)

    logger.info(
        f"Act {act.act_number} signed by user {current_user.id} "
        f"(method=click_accept, ip_hash={ip_hash[:12]}...)"
    )

    return _act_to_dict(act)


@router.get("/{act_id}/pdf")
async def download_act_pdf(
    act_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> FileResponse:
    """Скачать PDF акта."""
    result = await session.execute(select(Act).where(Act.id == act_id))
    act = result.scalar_one_or_none()
    if not act:
        raise HTTPException(status_code=404, detail=_ACT_NOT_FOUND)

    # Проверка доступа
    placement = await session.get(PlacementRequest, act.placement_request_id)
    if not placement:
        raise HTTPException(status_code=404, detail=_PLACEMENT_NOT_FOUND)
    if placement.advertiser_id != current_user.id and placement.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail=_ACCESS_DENIED)

    if not act.pdf_path:
        raise HTTPException(status_code=404, detail="PDF not generated")

    pdf = Path(act.pdf_path)
    if not pdf.exists():
        raise HTTPException(status_code=404, detail="PDF file not found on disk")

    return FileResponse(
        str(pdf),
        media_type="application/pdf",
        filename=f"{act.act_number}.pdf",
    )
