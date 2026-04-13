"""Pydantic v2 schemas for Act API responses."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from src.db.models.act import Act


class ActResponse(BaseModel):
    """Act API response schema.

    sign_status values: draft | pending | signed | auto_signed
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    placement_request_id: int
    act_number: str | None = None
    sign_status: str
    pdf_url: str | None = None
    signed_at: datetime | None = None
    created_at: datetime | None = None


def act_to_response(act: Act) -> ActResponse:
    """Build ActResponse from ORM object, mapping pdf_path → pdf_url."""
    return ActResponse(
        id=act.id,
        placement_request_id=act.placement_request_id,
        act_number=act.act_number,
        sign_status=act.sign_status,
        pdf_url=f"/api/acts/{act.id}/pdf" if act.pdf_path else None,
        signed_at=act.signed_at,
        created_at=act.created_at,
    )


class ActListResponse(BaseModel):
    """List of acts with total count."""

    items: list[ActResponse]
    total: int
