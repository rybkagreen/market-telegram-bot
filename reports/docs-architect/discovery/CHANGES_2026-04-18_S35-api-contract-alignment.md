# Changes: S-35 API Contract Alignment
**Date:** 2026-04-18T08:15:22Z
**Author:** Claude Code
**Sprint/Task:** S-35 — Fix web_portal legal/contracts flow (3× P0) + N-05 response alignment + cleanup

## Affected Files

- `web_portal/src/api/legal.ts` — Fixed three broken API calls:
  - `acceptRules()`: was sending empty body; backend `AcceptRulesRequest` requires `{accept_platform_rules: true, accept_privacy_policy: true}`
  - `signContract()`: was sending `{method}`; backend `ContractSignRequest` requires `{signature_method}`
  - `requestKep()`: was calling `contracts/${contractId}/request-kep` with `{email}`; correct path is `contracts/request-kep` with `{contract_id, email}`
- `web_portal/src/components/contracts/KepWarning.tsx` — Replaced inline `api.post(...)` with `apiRequestKep` from `@/api/legal` to eliminate duplicate wrong path/body
- `src/api/routers/channels.py` — `ComparisonChannelItem` schema: renamed `member_count→subscribers`, `er→last_er`; added `topic: str | None`, `rating: float | None`; made `is_best` default to `{}`
- `src/core/services/comparison_service.py` — `ComparisonService.get_channels_for_comparison()`: fixed broken attribute access (`last_avg_views→avg_views`, `last_post_frequency→0.0`, `channel_id→id`); added `selectinload(channel_settings)` to load `price_per_post`; added `topic` and `rating` to output dict; updated `calculate_comparison_metrics()` to use `subscribers`/`last_er`/`id` keys
- `src/api/routers/billing.py` — Removed stale docstring entry `GET /api/billing/invoice/{id}` (endpoint never implemented)
- `tests/unit/test_s35_api_contract_regression.py` — 12 new regression tests for N-08, Extra-1, N-05 schema/service changes

## Business Logic Impact

- **Legal flow now functional in web_portal**: `AcceptRules` (was always 422), `signContract` (was always 422), `requestKep` (was always 404) are now correctly wired to their backend endpoints
- **Channel comparison now returns correct fields**: `mini_app` components consuming `ChannelCompareResponse` will receive `subscribers`, `last_er`, `topic`, `rating` as expected; previously would have received mismatched or missing fields causing silent data loss in UI
- **ComparisonService no longer raises AttributeError**: `chat.price_per_post` was accessing a non-existent attribute (it lives in `ChannelSettings`); now correctly loads via `selectinload`

## API / FSM / DB Contracts

### Changed (backend)
- `POST /api/contracts/accept-rules` — frontend now sends required body `{accept_platform_rules: bool, accept_privacy_policy: bool}` (no schema change on backend)
- `POST /api/contracts/{id}/sign` — frontend now sends `{signature_method: string}` instead of `{method: string}`
- `POST /api/contracts/request-kep` — frontend now uses correct path and sends `{contract_id: int, email: string}` instead of wrong path with `{email: string}`
- `POST /api/channels/compare` → `ComparisonResponse.channels[]` fields renamed: `member_count→subscribers`, `er→last_er`; new fields: `topic`, `rating`; `is_best` now defaults to `{}`

### Skipped (confirmed non-issues)
- N-04 `POST /billing/credits` — endpoint exists, contract matches
- N-06 `POST /legal-profile/scan` — endpoint exists, contract matches
- N-07 `web_portal/src/api/contracts.ts` — file does not exist (research artifact); getMyContracts is correctly in `legal.ts`

## Migration Notes

None — no DB schema changes.

---
🔍 Verified against: 0eb759b | 📅 Updated: 2026-04-18T08:15:22Z
