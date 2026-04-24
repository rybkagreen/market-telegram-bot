"""
S-47 contract-drift guard — pytest snapshot of critical backend response schemas.

Captures ``model_json_schema()`` for each of the critical Pydantic response
models consumed by the Mini App / Web Portal frontends. Any change to the
shape of a contract (added / removed / renamed field, type change) forces
the author to explicitly update the matching JSON snapshot file — which
makes the contract change visible in code review.

This plugs the class of drift seen in:
  * S-43 — ``owner_comment`` → ``owner_explanation`` rename slipped in silently
  * S-48 C1 — ``contracts/me`` 422, triggered by schema shape mismatch
  * S-46 — ``UserFeedback.response_text`` vs ``admin_response`` divergence

Updating snapshots
------------------
When you intentionally change a schema:

    UPDATE_SNAPSHOTS=1 poetry run pytest tests/unit/test_contract_schemas.py

Then commit the regenerated ``tests/unit/snapshots/*.json`` as part of the
same PR that changes the schema. Reviewers see the diff — drift becomes
visible.

The snapshots are stable JSON (sorted keys, 2-space indent), so diffs are
line-oriented and easy to review.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel

from src.api.routers.campaigns import CampaignListResponse, CampaignsListResponse
from src.api.routers.placements import PlacementResponse
from src.api.schemas.admin import (
    AdminContractListResponse,
    DisputeListAdminResponse,
    FeedbackListAdminResponse,
    UserAdminResponse,
    UserListAdminResponse,
)
from src.api.schemas.analytics import AIInsightsUnifiedResponse
from src.api.schemas.channel import ChannelResponse
from src.api.schemas.dispute import DisputeListResponse, DisputeResponse
from src.api.schemas.feedback import FeedbackListResponse
from src.api.schemas.legal_profile import (
    ContractListResponse,
    ContractResponse,
    LegalProfileResponse,
)
from src.api.schemas.payout import AdminPayoutListResponse, PayoutResponse
from src.api.schemas.user import UserResponse

SNAPSHOT_DIR = Path(__file__).parent / "snapshots"

# (snapshot_name, model_class) — snapshot_name is the file stem under SNAPSHOT_DIR.
#
# List-wrapper schemas (plan-04, 2026-04-21) are deliberately included here:
# the web_portal admin and Mini App pages consume the wrapper shape
# (`{items, total, limit, offset}` / `{placement_requests, total, page, …}`),
# not the bare list. A rename of `total → count` or `items → rows` would be
# invisible without an explicit snapshot.
#
# Skipped on purpose — endpoint either returns a bare list[X] (item schema
# already covers the contract) or builds an inline dict without a Pydantic
# wrapper:
#   * GET /api/payouts/                 → list[PayoutResponse]
#   * GET /api/admin/audit-logs         → inline dict (no wrapper class)
CONTRACT_SCHEMAS: list[tuple[str, type[BaseModel]]] = [
    ("user_response", UserResponse),
    ("user_admin_response", UserAdminResponse),
    ("placement_response", PlacementResponse),
    ("payout_response", PayoutResponse),
    ("contract_response", ContractResponse),
    ("dispute_response", DisputeResponse),
    ("legal_profile_response", LegalProfileResponse),
    ("channel_response", ChannelResponse),
    # ── list / pagination wrappers ──────────────────────────────────────
    ("admin_payout_list_response", AdminPayoutListResponse),
    ("admin_contract_list_response", AdminContractListResponse),
    ("user_list_admin_response", UserListAdminResponse),
    ("dispute_list_admin_response", DisputeListAdminResponse),
    ("feedback_list_admin_response", FeedbackListAdminResponse),
    ("dispute_list_response", DisputeListResponse),
    ("feedback_list_response", FeedbackListResponse),
    ("contract_list_response", ContractListResponse),
    ("campaign_list_response", CampaignListResponse),
    ("campaigns_list_response", CampaignsListResponse),
    # ── unified AI insights (new /analytics screen) ─────────────────────
    ("ai_insights_unified_response", AIInsightsUnifiedResponse),
]


def _dump(schema: dict[str, Any]) -> str:
    return json.dumps(schema, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _snapshot_path(name: str) -> Path:
    return SNAPSHOT_DIR / f"{name}.json"


@pytest.mark.parametrize(
    ("snapshot_name", "model_cls"),
    CONTRACT_SCHEMAS,
    ids=[name for name, _ in CONTRACT_SCHEMAS],
)
def test_contract_schema_matches_snapshot(snapshot_name: str, model_cls: type[BaseModel]) -> None:
    """Compare the model's JSON schema to its checked-in snapshot."""
    actual = model_cls.model_json_schema()
    actual_text = _dump(actual)
    path = _snapshot_path(snapshot_name)

    if os.environ.get("UPDATE_SNAPSHOTS") == "1":
        SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(actual_text, encoding="utf-8")
        pytest.skip(f"snapshot updated: {path.name}")

    if not path.exists():
        pytest.fail(
            f"Missing snapshot for {model_cls.__name__}: {path}\n"
            f"Run: UPDATE_SNAPSHOTS=1 pytest tests/unit/test_contract_schemas.py"
        )

    expected_text = path.read_text(encoding="utf-8")
    if actual_text != expected_text:
        pytest.fail(
            "\n".join([
                f"Contract drift in {model_cls.__name__} (snapshot: {path.name}).",
                "",
                "The schema shape changed. If this is intentional, regenerate the snapshot with:",
                "  UPDATE_SNAPSHOTS=1 poetry run pytest tests/unit/test_contract_schemas.py",
                "",
                "and commit the updated JSON alongside your schema change.",
                "",
                _diff(expected_text, actual_text),
            ])
        )


def _diff(expected: str, actual: str) -> str:
    import difflib

    diff = difflib.unified_diff(
        expected.splitlines(keepends=True),
        actual.splitlines(keepends=True),
        fromfile="snapshot (expected)",
        tofile="current schema (actual)",
        n=3,
    )
    return "".join(diff)


def test_contract_schemas_registry_has_no_duplicates() -> None:
    """Guard against accidental duplicate snapshot names in the registry."""
    names = [name for name, _ in CONTRACT_SCHEMAS]
    assert len(names) == len(set(names)), f"duplicate snapshot names: {names}"
