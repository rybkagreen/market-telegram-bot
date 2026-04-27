"""TransitionMetadata Pydantic schema.

Phase 2 § 2.B.0 Decision 5. Closed model (extra="forbid"),
Literal enums for trigger and admin_override_reason. Fields are the
ONLY allowed metadata for placement status transitions — extension
requires explicit code change + review.

PII fields are explicitly forbidden by absence — see Decision 5
forbidden list. JSONB storage in placement_status_history.metadata_json
serializes via model_dump().
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from src.db.models.placement_request import PlacementStatus

# Closed Literal enums — extension requires explicit code change.
ErrorCode = Literal[
    "publication_failed",
    "permission_denied",
    "ord_registration_failed",
    "payment_timeout",
    "rate_limited",
    "unknown",
]

Trigger = Literal[
    "api",
    "celery_beat",
    "celery_signal",
    "admin_api",
    "system",
]

AdminOverrideReason = Literal[
    "dispute_resolution",
    "escrow_force_release",
    "manual_data_repair",
    "legal_takedown",
]


class TransitionMetadata(BaseModel):
    """Closed metadata schema for placement status transitions.

    Forbidden fields (FZ-152 + Decision 5 PII guard): telegram_id,
    ip_address, user_agent, phone_number, email, inn, passport_*,
    bank_account, legal_name, free-form description/comment,
    free-form rejection_reason text.

    Required: from_status, to_status, trigger.
    All other fields optional.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    # Required
    from_status: PlacementStatus | None  # None for synthetic backfill rows
    to_status: PlacementStatus
    trigger: Trigger

    # Optional — service or task context
    task_name: str | None = None
    error_code: ErrorCode | None = None
    gate_attempt: int | None = None
    from_admin_id: int | None = None  # internal users.id, NEVER telegram_id
    celery_task_id: str | None = None
    idempotency_key: str | None = None
    correlation_id: str | None = None  # RESERVED — populated by middleware in Phase 3 (see BACKLOG BL-014)
    placement_id: int | None = None  # conditional — for cross-table denormalisation if needed
    attempted_at: datetime | None = None
    admin_override_reason: AdminOverrideReason | None = None
    legacy: bool | None = None  # True only on synthetic backfill rows (Decision 6 spec)
