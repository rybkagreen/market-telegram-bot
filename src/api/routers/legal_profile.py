"""FastAPI router for legal profile management."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user_from_web_portal, get_db_session
from src.api.schemas.legal_profile import (
    FnsValidationError,
    FnsValidationResponse,
    LegalProfileCreate,
    LegalProfileResponse,
    LegalProfileUpdate,
    RequiredFieldsResponse,
    ScanUpload,
    ValidateEntityRequest,
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
    data = {
        c.name: getattr(profile, c.name)
        for c in profile.__table__.columns
        if c.name in _RESPONSE_FIELDS
    }
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
    current_user: Annotated[User, Depends(get_current_user_from_web_portal)],
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
    current_user: Annotated[User, Depends(get_current_user_from_web_portal)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> LegalProfileResponse:
    """Create legal profile for current user."""
    svc = LegalProfileService(session)
    profile = await svc.create_profile(current_user.id, data.model_dump(exclude_none=True))
    await session.commit()
    return _build_response(profile, current_user)


@router.patch("")
async def update_profile(
    data: LegalProfileUpdate,
    current_user: Annotated[User, Depends(get_current_user_from_web_portal)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> LegalProfileResponse:
    """Update legal profile of current user."""
    svc = LegalProfileService(session)
    profile = await svc.update_profile(current_user.id, data.model_dump(exclude_unset=True))
    await session.commit()
    return _build_response(profile, current_user)


@router.post(
    "/scan",
    responses={400: {"description": "Bad Request"}},
)
async def upload_scan(
    data: ScanUpload,
    current_user: Annotated[User, Depends(get_current_user_from_web_portal)],
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
    current_user: Annotated[User, Depends(get_current_user_from_web_portal)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    legal_status: Annotated[str, Query()],
) -> RequiredFieldsResponse:
    """Get required fields for a given legal status."""
    svc = LegalProfileService(session)
    try:
        result = await svc.get_required_fields(legal_status)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    return RequiredFieldsResponse(**result)


@router.post("/validate-inn")
async def validate_inn(
    data: ValidateInnRequest,
    current_user: Annotated[User, Depends(get_current_user_from_web_portal)],
) -> ValidateInnResponse:
    """Validate an INN number."""
    valid, inn_type = LegalProfileService.validate_inn(data.inn)
    return ValidateInnResponse(valid=valid, type=inn_type)


@router.post("/validate-entity")
async def validate_entity(
    data: ValidateEntityRequest,
    current_user: Annotated[User, Depends(get_current_user_from_web_portal)],
) -> FnsValidationResponse:
    """
    Валидация юрлица или ИП через контрольные суммы ФНС.

    Проверяет:
    - ИНН (контрольная сумма)
    - КПП (формат)
    - ОГРН/ОГРНИП (контрольная сумма)
    """
    from src.core.services.fns_validation_service import (
        validate_entity_documents,
        validate_entity_type_match,
        validate_individual_entrepreneur,
        validate_inn_type,
        validate_legal_entity,
    )

    # Cross-validate: does the selected status match the INN type?
    type_ok, type_error = validate_entity_type_match(data.legal_status, data.inn)
    if not type_ok:
        return FnsValidationResponse(
            is_valid=False,
            errors=[
                FnsValidationError(field="inn", message=type_error or "Несоответствие типа ИНН")
            ],
        )

    # Documents must match the status (OGRN for LLC, OGRNIP for IE, passport for
    # individual, nothing for self_employed). Catches the coarse 12-digit-INN
    # gap where individual / self_employed / IE are otherwise interchangeable.
    docs_ok, docs_error = validate_entity_documents(
        data.legal_status,
        ogrn=data.ogrn,
        ogrnip=data.ogrnip,
        passport_series=data.passport_series,
        passport_number=data.passport_number,
    )
    if not docs_ok:
        # field name depends on which document was wrong; default to a
        # generic "documents" bucket since the message identifies it.
        field = "ogrnip" if data.ogrnip else ("ogrn" if data.ogrn else "documents")
        return FnsValidationResponse(
            is_valid=False,
            errors=[FnsValidationError(field=field, message=docs_error or "Документы не соответствуют статусу")],
        )

    # Quick INN check
    inn_result = validate_inn_type(data.inn)
    if not inn_result["valid"]:
        return FnsValidationResponse(
            is_valid=False,
            errors=[FnsValidationError(field="inn", message=e) for e in inn_result["errors"]],
        )

    entity_type = inn_result["type"]

    if entity_type == "legal_entity":
        result = validate_legal_entity(data.inn, data.kpp, data.ogrn)
    elif entity_type == "individual":
        result = validate_individual_entrepreneur(data.inn, data.ogrnip)
    else:
        result = validate_legal_entity(data.inn, data.kpp, data.ogrn)

    return FnsValidationResponse(
        is_valid=result.is_valid,
        entity_type=result.entity_type,
        inn=result.inn,
        name=result.name,
        kpp=result.kpp,
        ogrn=result.ogrn,
        status=result.status,
        errors=[FnsValidationError(field=e.field, message=e.message) for e in result.errors],
        warnings=result.warnings,
    )
