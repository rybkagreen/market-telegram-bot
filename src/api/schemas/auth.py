"""
Auth-bridge response schemas — Phase 0 (mini_app → web_portal JWT exchange).

`TicketResponse` and `AuthTokenResponse` are public contracts:
both shapes are pinned by `tests/unit/test_contract_schemas.py`.
"""

from typing import Literal

from pydantic import BaseModel


class TicketResponse(BaseModel):
    """Short-lived JWT ticket returned by /api/auth/exchange-miniapp-to-portal."""

    ticket: str
    portal_url: str
    expires_in: int


class AuthTokenResponse(BaseModel):
    """Full-session JWT issued after consuming a ticket or signing in directly."""

    access_token: str
    token_type: Literal["bearer"] = "bearer"
    source: Literal["mini_app", "web_portal"]
