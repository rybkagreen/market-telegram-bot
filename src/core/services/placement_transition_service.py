"""PlacementTransitionService — single point of mutation for placement.status.

Phase 2 § 2.B.1 commit 3/4. Implements § 2.B.0 Decisions 2, 4, 5, 11, 12.

Two public methods:
- transition() — strict allow-list mode for organic transitions.
- transition_admin_override() — for admin-driven transitions outside
  the allow-list, requires explicit AdminOverrideReason.

Both methods append a row to placement_status_history (no UNIQUE
constraint per Decision 10 — ping-pong is legal). Both use
_sync_status_timestamps() to maintain placement timestamp invariants
per Decision 4 conflict matrix.

S-48 contract: methods do NOT open or commit transactions. The caller
owns the session lifecycle.

11 callers will be migrated to this service in § 2.B.2 (separate work).
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.schemas.transition_metadata import (
    AdminOverrideReason,
    TransitionMetadata,
    Trigger,
)
from src.db.models.placement_request import PlacementRequest, PlacementStatus
from src.db.models.placement_status_history import PlacementStatusHistory


class InvalidTransitionError(ValueError):
    """Raised when an organic transition is not in the allow-list."""


class TransitionInvariantError(RuntimeError):
    """Raised when a transition would violate a placement invariant
    (e.g. INV-1: status='escrow' requires escrow_transaction_id)."""


# Allow-list per § 2.B.0 Decision 1 state machine.
# Format: from_status -> set of allowed to_status.
_ALLOW_LIST: dict[PlacementStatus, set[PlacementStatus]] = {
    PlacementStatus.pending_owner: {
        PlacementStatus.counter_offer,
        PlacementStatus.pending_payment,
        PlacementStatus.cancelled,
    },
    PlacementStatus.counter_offer: {
        PlacementStatus.pending_owner,  # ping-pong
        PlacementStatus.pending_payment,
        PlacementStatus.cancelled,
    },
    PlacementStatus.pending_payment: {
        PlacementStatus.escrow,
        PlacementStatus.cancelled,
    },
    PlacementStatus.escrow: {
        PlacementStatus.published,
        PlacementStatus.failed,
        PlacementStatus.failed_permissions,
        PlacementStatus.refunded,
        # Advertiser cancel-after-escrow path with 50% refund —
        # bot/handlers/placement/placement.py:camp_cancel_after_escrow.
        PlacementStatus.cancelled,
    },
    PlacementStatus.published: {
        PlacementStatus.completed,
        PlacementStatus.failed,
        PlacementStatus.refunded,
        PlacementStatus.cancelled,
    },
    PlacementStatus.completed: set(),  # terminal
    PlacementStatus.failed: {PlacementStatus.refunded},  # Decision 12 two-step
    PlacementStatus.failed_permissions: {PlacementStatus.refunded},
    PlacementStatus.refunded: set(),  # terminal
    PlacementStatus.cancelled: set(),  # terminal
}


class PlacementTransitionService:
    """Single point of mutation for placement.status."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def transition(
        self,
        placement: PlacementRequest,
        to_status: PlacementStatus,
        actor_user_id: int | None,
        reason: str,
        trigger: Trigger,
        metadata: TransitionMetadata | None = None,
    ) -> PlacementStatusHistory:
        """Organic transition — strict allow-list.

        Raises:
            InvalidTransitionError: if (from_status, to_status) is not
                in the allow-list.
            TransitionInvariantError: if the resulting state would
                violate an invariant (INV-1 etc.).
        """
        from_status = placement.status
        if to_status not in _ALLOW_LIST.get(from_status, set()):
            raise InvalidTransitionError(
                f"Transition {from_status} -> {to_status} not in allow-list. "
                f"Use transition_admin_override() for admin-driven exceptions."
            )

        return await self._apply(
            placement, to_status, actor_user_id, reason, trigger, metadata
        )

    async def transition_admin_override(
        self,
        placement: PlacementRequest,
        to_status: PlacementStatus,
        actor_user_id: int,  # NOT optional — admin override requires identified actor
        reason: str,
        admin_override_reason: AdminOverrideReason,
        metadata: TransitionMetadata | None = None,
    ) -> PlacementStatusHistory:
        """Admin-driven transition — bypasses allow-list, requires reason.

        Allow-list is NOT consulted. Invariants ARE still enforced
        (admin cannot bypass INV-1 etc. via this path).
        """
        if metadata is None:
            metadata = TransitionMetadata(
                from_status=placement.status,
                to_status=to_status,
                trigger="admin_api",
                from_admin_id=actor_user_id,
                admin_override_reason=admin_override_reason,
            )
        else:
            metadata = metadata.model_copy(
                update={
                    "admin_override_reason": admin_override_reason,
                    "from_admin_id": actor_user_id,
                }
            )

        return await self._apply(
            placement,
            to_status,
            actor_user_id,
            reason,
            "admin_api",
            metadata,
        )

    async def _apply(
        self,
        placement: PlacementRequest,
        to_status: PlacementStatus,
        actor_user_id: int | None,
        reason: str,
        trigger: Trigger,
        metadata: TransitionMetadata | None,
    ) -> PlacementStatusHistory:
        """Common path — invariant check, timestamp sync, history append.

        Does NOT commit. Caller owns transaction (S-48).
        """
        from_status = placement.status

        final_metadata: TransitionMetadata = metadata if metadata is not None else TransitionMetadata(
            from_status=from_status,
            to_status=to_status,
            trigger=trigger,
        )

        self._sync_status_timestamps(placement, to_status)

        placement.status = to_status

        self._check_invariants(placement)

        history = PlacementStatusHistory(
            placement_id=placement.id,
            from_status=from_status,
            to_status=to_status,
            actor_user_id=actor_user_id,
            reason=reason,
            metadata_json=final_metadata.model_dump(mode="json", exclude_none=True),
        )
        self._session.add(history)

        await self._session.flush()

        return history

    def _sync_status_timestamps(
        self,
        placement: PlacementRequest,
        to_status: PlacementStatus,
    ) -> None:
        """Synchronise placement timestamp fields per Decision 4.

        Append-only fields (NEVER cleared): published_at, last_published_at,
        message_id, escrow_transaction_id, rejection_reason, counter_*.

        Conditional clears:
        - scheduled_delete_at: clear on published -> !completed.
        - expires_at: stays as-is on transition into escrow (append-only).

        completed_at / failed_at are NOT modelled on PlacementRequest in
        the current schema; transitions into completed / failed
        deliberately do not write a per-status timestamp here. Add
        fields + sync logic together if required later.
        """
        now = datetime.now(timezone.utc)

        if to_status == PlacementStatus.counter_offer:
            placement.expires_at = now.replace(microsecond=0) + timedelta(hours=24)
        elif to_status == PlacementStatus.pending_payment:
            placement.expires_at = now.replace(microsecond=0) + timedelta(hours=24)
        elif to_status == PlacementStatus.published:
            if placement.published_at is None:
                placement.published_at = now
            placement.last_published_at = now

        # Clear scheduled_delete_at on published -> !completed/!published.
        if (
            placement.status == PlacementStatus.published
            and to_status not in {PlacementStatus.completed, PlacementStatus.published}
        ):
            placement.scheduled_delete_at = None

    def _check_invariants(self, placement: PlacementRequest) -> None:
        """Raise TransitionInvariantError if placement violates invariants."""
        # INV-1: status='escrow' requires escrow_transaction_id
        if (
            placement.status == PlacementStatus.escrow
            and not placement.escrow_transaction_id
        ):
            raise TransitionInvariantError(
                "INV-1 violated: status='escrow' requires escrow_transaction_id to be set."
            )
