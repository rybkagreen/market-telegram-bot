"""
Non-PII consent endpoint — platform rules + privacy policy acknowledgement.

Phase 1 §1.B.2 carve-out (FZ-152 scope policy).
================================================

Why this lives outside `contracts.py`:

- The mini_app legal strip moves *all PII flows* (legal profile, contract
  signing, acts, document validation) to web_portal-only authentication. As
  a side-effect, contracts.py is now uniformly `get_current_user_from_web_portal`
  and a forbidden-pattern check enforces that.
- Accepting platform rules and privacy policy, however, is a non-PII
  operation: input is two booleans, the service writes only timestamps
  and the constant `signature_method = "button_accept"`. Routing it
  through `web_portal-only` would force every new mini_app user to
  bounce to the browser during onboarding — 3-4 extra steps for what is
  fundamentally a flag-set, with no PII upside.
- Carving the endpoint out into a separate router with `get_current_user`
  (both audiences) preserves the mini_app onboarding flow without
  weakening the FZ-152 contract: contracts.py stays uniformly web_portal,
  with no exception-of-the-week to remember.

Scope policy (mirrored in IMPLEMENTATION_PLAN_ACTIVE.md "Общие правила"):
exception from heavy-strip is permitted only when the endpoint is
*provably non-PII*. Justification must live in this docstring AND in the
phase CHANGES doc. If PII is ever required here, this endpoint must
move to web_portal-only authentication immediately.

URL preserved as `/api/contracts/accept-rules` for backward compatibility
with existing clients (mini_app + web_portal).
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user, get_db_session
from src.api.schemas.legal_profile import AcceptRulesRequest
from src.core.services.contract_service import ContractService
from src.db.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/contracts", tags=["legal-acceptance"])


@router.post(
    "/accept-rules",
    responses={400: {"description": "Bad Request"}},
)
async def accept_rules(
    data: AcceptRulesRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    """Accept platform rules and privacy policy.

    Non-PII consent endpoint. Accepts boolean acknowledgement of platform
    rules and privacy policy. No PII fields permitted in request or response.
    If PII is ever required here, this must move to web_portal-only
    authentication.
    """
    if not (data.accept_platform_rules and data.accept_privacy_policy):
        raise HTTPException(
            status_code=400,
            detail="Both platform_rules and privacy_policy must be accepted",
        )
    svc = ContractService(session)
    await svc.accept_platform_rules(current_user.id)
    await session.commit()
    return {"success": True}
