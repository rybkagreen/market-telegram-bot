"""FastAPI router for contract management."""

import logging
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user, get_db_session
from src.api.schemas.legal_profile import (
    AcceptRulesRequest,
    ContractListResponse,
    ContractResponse,
    ContractSignRequest,
    ContractStatus,
    ContractType,
    GenerateContractRequest,
    KepRequestBody,
    SignatureMethod,
)
from src.core.services.contract_service import ContractService
from src.db.models.contract import Contract
from src.db.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/contracts", tags=["contracts"])


def _contract_to_response(contract: Contract) -> ContractResponse:
    """Build ContractResponse from ORM object."""
    pdf_url = f"/api/contracts/{contract.id}/pdf" if contract.pdf_file_path else None
    return ContractResponse(
        id=contract.id,
        user_id=contract.user_id,
        contract_type=ContractType(contract.contract_type),
        contract_status=ContractStatus(contract.contract_status),
        placement_request_id=contract.placement_request_id,
        template_version=contract.template_version,
        signature_method=SignatureMethod(contract.signature_method) if contract.signature_method else None,
        signed_at=contract.signed_at,
        expires_at=contract.expires_at,
        pdf_url=pdf_url,
        kep_requested=contract.kep_requested,
        kep_request_email=contract.kep_request_email,
        role=contract.role,
        created_at=contract.created_at,
        updated_at=contract.updated_at,
    )


@router.post("/generate", status_code=201, responses={400: {"description": "Bad Request"}})
async def generate_contract(
    data: GenerateContractRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ContractResponse:
    """Generate a new contract."""
    svc = ContractService(session)
    contract = await svc.generate_contract(
        current_user.id, data.contract_type.value, data.placement_request_id
    )
    await session.commit()
    return _contract_to_response(contract)


@router.post(
    "/accept-rules",
    responses={400: {"description": "Bad Request"}},
)
async def accept_rules(
    data: AcceptRulesRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    """Accept platform rules and privacy policy."""
    if not (data.accept_platform_rules and data.accept_privacy_policy):
        raise HTTPException(
            status_code=400,
            detail="Both platform_rules and privacy_policy must be accepted",
        )
    svc = ContractService(session)
    await svc.accept_platform_rules(current_user.id)
    await session.commit()
    return {"success": True}


@router.get("")
async def list_contracts(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    type: ContractType | None = None,
    status: str | None = None,
) -> ContractListResponse:
    """List contracts for current user."""
    svc = ContractService(session)
    contracts = await svc.get_user_contracts(current_user.id, type.value if type else None)
    if status:
        contracts = [c for c in contracts if c.contract_status == status]
    items = [_contract_to_response(c) for c in contracts]
    return ContractListResponse(items=items, total=len(items))


@router.get(
    "/{contract_id}",
    responses={403: {"description": "Forbidden"}, 404: {"description": "Not found"}},
)
async def get_contract(
    contract_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ContractResponse:
    """Get a single contract by ID."""
    result = await session.execute(select(Contract).where(Contract.id == contract_id))
    contract = result.scalar_one_or_none()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    if contract.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return _contract_to_response(contract)


@router.post(
    "/{contract_id}/sign",
    responses={400: {"description": "Bad Request"}, 403: {"description": "Forbidden"}},
)
async def sign_contract(
    contract_id: int,
    data: ContractSignRequest,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ContractResponse:
    """Sign a contract."""
    svc = ContractService(session)
    try:
        ip = request.client.host if request.client else None
        contract = await svc.sign_contract(
            contract_id=contract_id,
            user_id=current_user.id,
            method=data.signature_method.value,
            sms_code=data.sms_code,
            ip_address=ip,
        )
        await session.commit()
        return _contract_to_response(contract)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post(
    "/request-kep",
    responses={400: {"description": "Bad Request"}, 403: {"description": "Forbidden"}},
)
async def request_kep(
    data: KepRequestBody,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    """Запросить КЭП-версию договора (для ЮЛ и ИП)."""
    svc = ContractService(session)
    try:
        await svc.request_kep_version(data.contract_id, current_user.id, data.email)
        await session.commit()
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    try:
        from src.core.services.notification_service import (
            NotificationService,  # type: ignore[import-untyped]
        )

        notif = NotificationService()
        profile = current_user.legal_profile
        legal_name = profile.legal_name if profile else "Unknown"
        inn = profile.inn if profile else "—"
        # NotificationService does not have notify_admin — log instead
        logger.info(
            "KEP request: user=%s (INN: %s), contract=#%s, email=%s",
            legal_name, inn, data.contract_id, data.email,
        )
        _ = notif  # reference to suppress unused var warning
    except Exception:
        pass  # notification failure must not block the request

    return {
        "success": True,
        "message": "Запрос принят. Мы направим КЭП-версию в течение 2 рабочих дней.",
    }


@router.get(
    "/{contract_id}/pdf",
    responses={403: {"description": "Forbidden"}, 404: {"description": "Not found"}},
)
async def download_pdf(
    contract_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> FileResponse:
    """Download a contract PDF."""
    result = await session.execute(select(Contract).where(Contract.id == contract_id))
    contract = result.scalar_one_or_none()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    if contract.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    if not contract.pdf_file_path:
        raise HTTPException(status_code=404, detail="PDF not generated yet")
    pdf = Path(contract.pdf_file_path)
    if not pdf.exists():
        raise HTTPException(status_code=404, detail="PDF file not found on disk")
    return FileResponse(str(pdf), media_type="application/pdf", filename=f"contract_{contract_id}.pdf")
