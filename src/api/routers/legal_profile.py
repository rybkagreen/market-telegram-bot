"""FastAPI router for legal profile management."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user, get_db_session
from src.api.schemas.legal_profile import (
    LegalProfileCreate,
    LegalProfileResponse,
    LegalProfileUpdate,
    RequiredFieldsResponse,
    ScanUpload,
    ValidateInnRequest,
    ValidateInnResponse,
)
from src.core.services.legal_profile_service import LegalProfileService
from src.db.models.user import User
from src.db.repositories.legal_profile_repo import LegalProfileRepo

router = APIRouter(prefix="/api/legal-profile", tags=["legal-profile"])

_RESPONSE_FIELDS = set(LegalProfileResponse.model_fields)


def _mask_bank_account(account: str | None) -> str | None:
    """Return masked bank account number (****1234) for API responses."""
    if not account:
        return None
    return "****" + account[-4:] if len(account) >= 4 else "****"


def _build_response(profile, user: User) -> LegalProfileResponse:
    """Construct LegalProfileResponse from ORM object."""
    data = {c.name: getattr(profile, c.name) for c in profile.__table__.columns if c.name in _RESPONSE_FIELDS}
    # Mask sensitive fields before returning to API caller
    data["bank_account"] = _mask_bank_account(data.get("bank_account"))
    data["bank_corr_account"] = _mask_bank_account(data.get("bank_corr_account"))
    return LegalProfileResponse(
        **data,
        has_passport_data=bool(profile.passport_series),
        has_inn_scan=bool(profile.inn_scan_file_id),
        has_passport_scan=bool(profile.passport_scan_file_id),
        has_self_employed_cert=bool(profile.self_employed_cert_file_id),
        has_company_doc=bool(profile.company_doc_file_id),
        is_complete=user.legal_status_completed,
    )


@router.get("/me")
async def get_my_profile(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> LegalProfileResponse | None:
    """Get legal profile of current user."""
    profile = await LegalProfileRepo(session).get_by_user_id(current_user.id)
    if profile is None:
        return None
    return _build_response(profile, current_user)


@router.post("", status_code=201)
async def create_profile(
    data: LegalProfileCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> LegalProfileResponse:
    """Create legal profile for current user."""
    svc = LegalProfileService(session)
    profile = await svc.create_profile(current_user.id, data.model_dump(exclude_none=True))
    await session.commit()
    await session.refresh(current_user)
    return _build_response(profile, current_user)


@router.patch("")
async def update_profile(
    data: LegalProfileUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> LegalProfileResponse:
    """Update legal profile of current user."""
    svc = LegalProfileService(session)
    profile = await svc.update_profile(current_user.id, data.model_dump(exclude_unset=True))
    await session.commit()
    await session.refresh(current_user)
    return _build_response(profile, current_user)


@router.post(
    "/scan",
    responses={400: {"description": "Bad Request"}},
)
async def upload_scan(
    data: ScanUpload,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    """Upload a document scan file_id for current user's legal profile."""
    svc = LegalProfileService(session)
    try:
        await svc.upload_scan(current_user.id, data.scan_type, data.file_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    await session.commit()
    return {"success": True}


@router.get("/required-fields")
async def get_required_fields(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    legal_status: Annotated[str, Query()],
) -> RequiredFieldsResponse:
    """Get required fields for a given legal status."""
    svc = LegalProfileService(session)
    result = await svc.get_required_fields(legal_status)
    return RequiredFieldsResponse(**result)


@router.post("/validate-inn")
async def validate_inn(
    data: ValidateInnRequest,
    current_user: Annotated[User, Depends(get_current_user)],
) -> ValidateInnResponse:
    """Validate an INN number."""
    valid, inn_type = LegalProfileService.validate_inn(data.inn)
    return ValidateInnResponse(valid=valid, type=inn_type)
