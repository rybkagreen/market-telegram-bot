"""FastAPI router for ORD (advertising registry) registration."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user, get_db_session
from src.api.schemas.legal_profile import OrdRegistrationResponse, RegisterOrdRequest
from src.core.services.ord_service import get_ord_service
from src.db.models.placement_request import PlacementRequest
from src.db.models.user import User

router = APIRouter(prefix="/api/ord", tags=["ord"])


@router.get(
    "/{placement_request_id}",
    responses={404: {"description": "Not found"}},
)
async def get_ord_status(
    placement_request_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> OrdRegistrationResponse:
    """Get ORD registration status for a placement."""
    svc = get_ord_service(session)
    registration = await svc.get_status(placement_request_id)
    if not registration:
        raise HTTPException(status_code=404, detail="ORD registration not found")
    return OrdRegistrationResponse.model_validate(registration)


@router.post(
    "/register",
    status_code=201,
    responses={403: {"description": "Forbidden"}, 404: {"description": "Not found"}},
)
async def register_creative(
    data: RegisterOrdRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> OrdRegistrationResponse:
    """Register an ad creative in ORD."""
    result = await session.execute(
        select(PlacementRequest).where(PlacementRequest.id == data.placement_request_id)
    )
    placement = result.scalar_one_or_none()
    if not placement:
        raise HTTPException(status_code=404, detail="Placement not found")
    if placement.advertiser_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    svc = get_ord_service(session)
    ad_text = getattr(placement, "ad_text", "") or ""
    media_type = getattr(placement, "media_type", "none") or "none"
    registration = await svc.register_creative(data.placement_request_id, ad_text, media_type)
    await session.commit()
    return OrdRegistrationResponse.model_validate(registration)
