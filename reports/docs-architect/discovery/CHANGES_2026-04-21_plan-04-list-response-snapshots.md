# CHANGES 2026-04-21 — plan-04 list-response contract snapshots

## Scope

Follow-up to `FIX_PLAN_06_followups/plan-04-list-response-contract-snapshots.md`
(P2). Closes the gap left by §6.1 Variant B: only item schemas
(`UserResponse`, `PlacementResponse`, …) were snapshot-locked, but the
web_portal admin pages and Mini App actually consume the **pagination
wrapper** shape (`{items, total, limit, offset}`). A rename of
`total → count` or `items → rows` would have shipped silently.

Tests-only sprint. No `src/` changes.

## Affected files

### Modified

| File | Change |
|---|---|
| `tests/unit/test_contract_schemas.py` | added 10 list-wrapper schemas to `CONTRACT_SCHEMAS`; documented why `/api/payouts/` and `/api/admin/audit-logs` are deliberately excluded |
| `CLAUDE.md` | rewrote `Contract drift guard` section: 18 schemas (8 items + 10 wrappers), explicit list of skipped endpoints with reason |

### New — snapshots

10 JSON files under `tests/unit/snapshots/` covering exactly the
wrappers consumed by routers:

| Snapshot | Wrapper | Router endpoint |
|---|---|---|
| `admin_payout_list_response.json` | `AdminPayoutListResponse` (`schemas.payout`) | `GET /api/admin/payouts` (admin.py:1094) |
| `admin_contract_list_response.json` | `AdminContractListResponse` (`schemas.admin`) | `GET /api/admin/contracts` (admin.py:1027) |
| `user_list_admin_response.json` | `UserListAdminResponse` (`schemas.admin`) | `GET /api/admin/users` (admin.py:211) |
| `dispute_list_admin_response.json` | `DisputeListAdminResponse` (`schemas.admin`) | `GET /api/admin/disputes` (disputes.py:506) |
| `feedback_list_admin_response.json` | `FeedbackListAdminResponse` (`schemas.admin`) | `GET /api/admin/feedback` (feedback.py:119) |
| `dispute_list_response.json` | `DisputeListResponse` (`schemas.dispute`) | `GET /api/disputes/` (disputes.py:117) |
| `feedback_list_response.json` | `FeedbackListResponse` (`schemas.feedback`) | `GET /api/feedback/` (feedback.py:66) |
| `contract_list_response.json` | `ContractListResponse` (`schemas.legal_profile`) | `GET /api/contracts/` (contracts.py:99) |
| `campaign_list_response.json` | `CampaignListResponse` (`routers.campaigns`) | `GET /api/campaigns` (campaigns.py:120) |
| `campaigns_list_response.json` | `CampaignsListResponse` (`routers.campaigns`) | `GET /api/campaigns/list` (campaigns.py:427) |

### New — discovery

| File | Purpose |
|---|---|
| `reports/docs-architect/discovery/CHANGES_2026-04-21_plan-04-list-response-snapshots.md` | this document |

## Top-level shape verification (plan step 4)

Audit of the new snapshots — no "mystery fields" surfaced:

```
admin_contract_list_response   → {items, limit, offset, total}
admin_payout_list_response     → {items, limit, offset, total}
campaign_list_response         → {has_more, page, page_size, placement_requests, total}
campaigns_list_response        → {items, page, pages, total}
contract_list_response         → {items, total}
dispute_list_admin_response    → {items, limit, offset, total}
dispute_list_response          → {items, limit, offset, total}
feedback_list_admin_response   → {items, limit, offset, total}
feedback_list_response         → {items, total}
user_list_admin_response       → {items, limit, offset, total}
```

Two divergent shapes inside `campaigns.py` (`placement_requests` vs
`items`, `page_size` vs `pages`) are real and intentional — both are
now locked, so any silent unification would surface as drift in
review.

## Deliberately skipped

| Endpoint | Reason |
|---|---|
| `GET /api/payouts/` (owner) | returns `list[PayoutResponse]` directly; `payout_response.json` already covers the item contract. Wrapper would be ceremony. |
| `GET /api/admin/audit-logs` | router returns an inline `dict[str, Any]`, not a Pydantic class (admin.py:466–482). Snapshotting is impossible without first promoting it to a `BaseModel`. Tracked separately — a small refactor candidate, **not** part of plan-04. |

The plan listed `AdminAuditLogListResponse` as a candidate but no
such class exists in the codebase (only `AuditLog` ORM model and the
inline dict above). Decision logged here so a future contributor
doesn't re-discover this and add a wrapper "for symmetry" without
realising the endpoint never had one.

## Validation

```bash
UPDATE_SNAPSHOTS=1 poetry run pytest tests/unit/test_contract_schemas.py --no-cov
# → 1 passed, 18 skipped (snapshot-update mode skips the comparison)

poetry run pytest tests/unit/test_contract_schemas.py --no-cov
# → 19 passed (18 schema asserts + 1 duplicate-name guard)

poetry run ruff check tests/unit/test_contract_schemas.py
# → All checks passed!

bash scripts/check_forbidden_patterns.sh
# → 7/7 ok
```

The 8 pre-existing item snapshots were **not** modified by the
regeneration — confirmed via `git status` (only 10 new `??` entries,
no `M` on the existing `*_response.json`).

## Out of scope (tracked separately)

- Promote `/api/admin/audit-logs` to a Pydantic wrapper —
  small refactor, not blocked by drift-guard.
- Variant A migration to openapi-typescript codegen — separate plan.

🔍 Verified against: 9afcca4 (main) | 📅 Created: 2026-04-21
