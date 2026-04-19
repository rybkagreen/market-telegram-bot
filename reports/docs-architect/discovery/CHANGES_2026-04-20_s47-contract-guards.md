# S-47 Contract-drift guard — CHANGES

**Branch:** `test/s-47-contract-guards`
**Scope:** snapshot-test critical backend Pydantic response schemas so that any
change to their JSON shape forces an explicit snapshot update in the same PR.
**Risk:** low. Tests only. No runtime / behavior change. No modifications to
`src/`, `mini_app/`, `web_portal/`, or `landing/`.

## Motivation

Prior drift incidents have been silent — field renames or removals merged into
the backend without touching the frontend type. Representative incidents:

- **S-43** — `owner_comment` renamed to `owner_explanation` on the dispute
  schema; web_portal kept reading the old field and rendered blanks.
- **S-48 C1** — `GET /contracts/me` returned 422 because the response model
  shape diverged from what the router declared.
- **S-46 audit** — `UserFeedback.response_text` on the backend vs.
  `admin_response` on the web_portal type for admin feedback threads.

The guard captures a stable JSON-Schema snapshot of each critical response
model. Any diff fails CI with a readable unified-diff and an instruction to
regenerate the snapshot — drift becomes visible in code review.

## Chosen approach: FIX_PLAN_06 §6.1 Variant B

- Python `pytest` test parametrized over the 8 target models.
- `model_json_schema()` serialized to sorted-key, 2-space-indent JSON.
- Snapshots checked into `tests/unit/snapshots/*.json`.
- Update flow: `UPDATE_SNAPSHOTS=1 poetry run pytest tests/unit/test_contract_schemas.py`.

Variant A (OpenAPI → TS codegen) is more robust but requires type-import
refactors across two frontends; deferred to a later sprint. Variant B covers
the same class of drift at a fraction of the scope.

## Files added

| File | Purpose |
|---|---|
| `tests/unit/test_contract_schemas.py` | Parametrized snapshot test — 8 schemas + 1 registry integrity test |
| `tests/unit/snapshots/user_response.json` | 23 fields |
| `tests/unit/snapshots/user_admin_response.json` | 21 fields |
| `tests/unit/snapshots/placement_response.json` | 39 fields |
| `tests/unit/snapshots/payout_response.json` | 12 fields |
| `tests/unit/snapshots/contract_response.json` | 15 fields |
| `tests/unit/snapshots/dispute_response.json` | 17 fields |
| `tests/unit/snapshots/legal_profile_response.json` | 24 fields |
| `tests/unit/snapshots/channel_response.json` | 13 fields |

**Coverage: 8 schemas, 164 fields total, 8 snapshot files.**

## Schemas captured

| Snapshot | Module path | Reason |
|---|---|---|
| `user_response` | `src.api.schemas.user.UserResponse` | Mini App + Web Portal `me` |
| `user_admin_response` | `src.api.schemas.admin.UserAdminResponse` | Admin users list/detail |
| `placement_response` | `src.api.routers.placements.PlacementResponse` | Central advertising entity (S-43 rename site) |
| `payout_response` | `src.api.schemas.payout.PayoutResponse` | Owner payouts + admin approvals (S-48 C-class drift) |
| `contract_response` | `src.api.schemas.legal_profile.ContractResponse` | KEP / rules acceptance flow (S-48 C1) |
| `dispute_response` | `src.api.schemas.dispute.DisputeResponse` | Escrow dispute flow (S-43) |
| `legal_profile_response` | `src.api.schemas.legal_profile.LegalProfileResponse` | IP / legal onboarding |
| `channel_response` | `src.api.schemas.channel.ChannelResponse` | Owner channel inventory |

## Developer workflow

**Expected failure flow** — intentional schema change:

```bash
# 1. developer renames a field in src/api/schemas/<x>.py
# 2. pytest fails with unified diff of the schema snapshot
poetry run pytest tests/unit/test_contract_schemas.py
# → FAILED: Contract drift in PlacementResponse (snapshot: placement_response.json)

# 3. developer updates the snapshot
UPDATE_SNAPSHOTS=1 poetry run pytest tests/unit/test_contract_schemas.py

# 4. commits both the schema change AND the regenerated snapshot
# → reviewer sees the shape diff in the PR and can verify the frontend was updated
```

**Accidental drift flow** — the same FAIL message tells an author unaware of the
shape change exactly what to do; the forced re-commit of the snapshot becomes
the review signal.

## Deferred to next sprint (tracked in FIX_PLAN_06)

- §6.1 Variant A (OpenAPI → TS codegen for `web_portal/src/lib/types/api-generated.ts`)
- §6.2 Playwright E2E smoke pack
- §6.4 Grep-guards for forbidden phantom paths
- §6.5/§6.6 Additional unit / integration coverage for S-45 admin-payouts and
  unified placement PATCH.

## Drift observations — noted for future work (not fixed here)

Per the task instructions, this sprint snapshots **current** schema state.
Known remaining frontend↔backend naming mismatches (see
`memory/project_s39a_schema_gaps.md`) that the snapshot files now lock in:

- `PayoutResponse` exposes `gross_amount` / `fee_amount` / `requisites`, while
  mini_app's `Payout` type still reads `amount` / `fee` / `payment_details`.
- `ChannelResponse` has `is_test` on the backend — confirm web_portal type
  includes it.
- `PlacementResponse` includes `has_dispute`, `dispute_status`, `erid`,
  `tracking_short_code`, `scheduled_delete_at`, `deleted_at`, `clicks_count`,
  `published_reach` — verify web_portal and mini_app types are complete.

The snapshot guard does not fix these; it prevents new divergence from being
introduced silently and flags the existing shape so a future Stage 7 audit
can compare snapshots line-by-line against the TS definitions.

## Validation

```bash
$ poetry run pytest tests/unit/test_contract_schemas.py --no-cov
============================== 9 passed in 0.94s ==============================

$ poetry run ruff check tests/unit/test_contract_schemas.py
All checks passed!
```

Pre-existing 11 ruff errors in `src/` and 119 errors in `tests/` are unchanged
by this sprint (baseline confirmed via `git stash` against main).

🔍 Verified against: ac7cdd1 (main @ start of sprint) | 📅 Updated: 2026-04-20
