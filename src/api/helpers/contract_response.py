"""Shared ORM→Pydantic conversion for Contract responses across routers.

Used by:
- src/api/routers/contracts.py — individual contract endpoints
- src/api/routers/placements.py — supplementary agreement pair endpoint
"""

from src.api.schemas.legal_profile import (
    ContractResponse,
    ContractStatus,
    ContractType,
    SignatureMethod,
)
from src.db.models.contract import Contract


def contract_to_response(contract: Contract) -> ContractResponse:
    """Build ContractResponse from ORM object."""
    pdf_url = f"/api/contracts/{contract.id}/pdf" if contract.pdf_file_path else None
    return ContractResponse(
        id=contract.id,
        user_id=contract.user_id,
        contract_type=ContractType(contract.contract_type),
        contract_status=ContractStatus(contract.contract_status),
        placement_id=contract.placement_id,
        parent_contract_id=contract.parent_contract_id,
        template_version=contract.template_version,
        signature_method=SignatureMethod(contract.signature_method)
        if contract.signature_method
        else None,
        signed_at=contract.signed_at,
        expires_at=contract.expires_at,
        pdf_url=pdf_url,
        kep_requested=contract.kep_requested,
        kep_request_email=contract.kep_request_email,
        role=contract.role,
        created_at=contract.created_at,
        updated_at=contract.updated_at,
    )
