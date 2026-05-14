"""Discriminated Pydantic schemas for ContractEvent.event_type values.

Closed Literal enums — adding a new event type requires updating this schema,
not just stringifying it at the recorder call site.

Phase 4 covers the ДС (supplementary agreement) lifecycle. Future event types
(KEP request/delivery, revocation, expiry roll) will extend ContractEventType
and add their own metadata classes.

Mirrors the TransitionMetadata pattern (transition_metadata.py): frozen,
extra='forbid', closed Literal discriminator.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class _BaseContractEventMetadata(BaseModel):
    """Base for closed event-metadata schemas (frozen, extra='forbid')."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class SupplementaryGeneratedMetadata(_BaseContractEventMetadata):
    """Metadata for `supplementary_generated` — ДС row created for placement."""

    placement_id: int
    role: Literal["owner", "advertiser"]
    parent_contract_id: int


class SupplementaryNotifiedMetadata(_BaseContractEventMetadata):
    """Metadata for `supplementary_notified` — sign-prompt enqueued for the party."""

    placement_id: int
    role: Literal["owner", "advertiser"]
    notification_channel: Literal["telegram", "email", "web_portal"]


class SupplementarySignedMetadata(_BaseContractEventMetadata):
    """Metadata for `supplementary_signed` — party signed their ДС side."""

    placement_id: int
    role: Literal["owner", "advertiser"]
    signature_method: Literal["button_accept", "sms_code"]


class SupplementaryActivatedMetadata(_BaseContractEventMetadata):
    """Metadata for `supplementary_activated` — both sides signed; ДС pair active."""

    placement_id: int
    both_sides_signed_at: datetime


ContractEventType = Literal[
    "supplementary_generated",
    "supplementary_notified",
    "supplementary_signed",
    "supplementary_activated",
]
