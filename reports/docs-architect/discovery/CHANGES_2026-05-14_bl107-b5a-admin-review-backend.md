# CHANGES 2026-05-14 — BL-107 Phase B.5a (Admin review backend)

## Context

Backend half of BL-107 manual evidence path для ФЗ-303 blogger registry
compliance. Built atop Phase B.4 (`03a82fb`) — wires the Pydantic schemas,
admin/owner endpoints, and notification triggers что will be consumed by
the frontend in Phase B.5b.

**What this enables (backend-only):**
- Owner submits Госуслуги application_number through API (POST endpoint).
- Admin reviews queue + verifies/rejects через 4 admin endpoints.
- `BloggerRegistryVerificationMethod.MANUAL_EVIDENCE` reachable via verify endpoint.
- `GateReason.BLOGGER_REGISTRY_PENDING_REVIEW` (Phase B.2) becomes triggerable.
- Owner notified about decisions; admins notified about new submissions.

Frontend UI (web_portal screens + mini_app screen) — deferred к Phase B.5b.

Design ref: `BL-107_DESIGN_2026-05-14.md` @ `38dbc94` § 6 (Admin review).
Probe ref: `BL-107_PROBE_2026-05-14.md` @ `14db543` § 6 (Admin infrastructure).

## Changes

### New file — `src/api/schemas/channel_verification.py`

9 Pydantic models для request/response контрактов:

| Schema | Used by |
|---|---|
| `ChannelVerificationSubmitRequest` | Owner POST /api/channels/{id}/submit-registry-evidence |
| `ChannelVerificationSubmitResponse` | Same — 200 OK response |
| `ChannelVerificationListItem` | List item — admin queue |
| `ChannelVerificationListResponse` | Paginated list wrapper |
| `ChannelVerificationHistoryEntry` | Audit log entry для detail view |
| `ChannelVerificationDetailResponse` | Detail view (channel + owner + history) |
| `ChannelVerificationVerifyRequest` | Admin POST .../verify |
| `ChannelVerificationVerifyResponse` | Verify 200 response |
| `ChannelVerificationRejectRequest` | Admin POST .../reject |
| `ChannelVerificationRejectResponse` | Reject 200 response |

Validation:
- `application_number`: 1-64 chars (required)
- `registry_url`: optional HttpUrl
- `notes`/`internal_notes`: optional, max 1000 chars
- `reason` (reject): required, 1-1000 chars
- `extra="forbid"` config — strict body shape

### Modified — `src/api/routers/channels.py` (owner submit endpoint)

New endpoint appended at end of file:

```
POST /api/channels/{channel_id}/submit-registry-evidence
```

Logic:
1. Fetch channel via `session.get(TelegramChat, channel_id)` — 404 if not found
2. Permission: `channel.owner_id == current_user.id` — 403 otherwise
3. Conflict guard: `not channel.is_blogger_registry_verified` — 409 otherwise
4. Mutate: `application_number` set, `last_blogger_registry_check_at = now`
5. `session.flush()` (caller-owns commit per S-48 Pattern 1)
6. AuditLog: `action="blogger_registry_evidence_submitted"`, `resource_type="telegram_chat"`
7. Trigger admin notification: `notify_admins_evidence_submitted(...)`
8. Return `ChannelVerificationSubmitResponse(status="pending_review", ...)`

New imports: `ChannelVerificationSubmitRequest`, `ChannelVerificationSubmitResponse`.

### Modified — `src/api/routers/admin.py` (4 admin endpoints)

All endpoints под router prefix `/admin` (mounted at `/api/admin/...`):

| Endpoint | Method | Purpose |
|---|---|---|
| `/channel-verifications` | GET | Paginated list (filter `status=pending_review\|verified`, `owner_id`, `limit`, `offset`) |
| `/channel-verifications/{channel_id}` | GET | Detail с audit history |
| `/channel-verifications/{channel_id}/verify` | POST | Admin approves manual evidence |
| `/channel-verifications/{channel_id}/reject` | POST | Admin rejects + reason |

Verify endpoint side-effects (all 6 audit fields populated):
- `is_blogger_registry_verified = True`
- `blogger_registry_verified_at = now`
- `blogger_registry_verification_method = "manual_evidence"`
- `blogger_registry_verified_by_admin_id = admin_user.id`
- `member_count_at_verification = channel.member_count`
- `last_blogger_registry_check_at = now`

Conflict guards:
- Verify: 409 if `application_number IS NULL` OR `is_verified IS True`
- Reject: 409 if `application_number IS NULL`

Reject side-effects:
- `application_number = None` (allows re-submission)
- `last_blogger_registry_check_at = now`

Audit log entries:
- `blogger_registry_verified_by_admin` — admin verifies
- `blogger_registry_rejected_by_admin` — admin rejects

Notifications:
- Verify → `notify_owner_verification_decided(decision="verified")`
- Reject → `notify_owner_verification_decided(decision="rejected", reason=...)`

Pagination: `limit: int = 50, offset: int = 0` с clamp validation (max 200,
clamp on negative offset).

Permission: `AdminUser` Annotated dependency — non-admin → 403 via existing
`get_current_admin_user` (раз mini_app JWT, тоже 403 на audience mismatch).

New imports added к module-level (NOT inside functions) — enables clean
monkeypatch by tests:
- `from src.core.services.notification_service import notify_owner_verification_decided`
- `from src.db.repositories.audit_log_repo import AuditLogRepo`
- `from src.api.schemas.channel_verification import (8 schemas)`

### Modified — `src/core/services/notification_service.py` (2 new helpers)

Module-level functions (NOT class methods — caller-owns session per S-48):

```python
async def notify_admins_evidence_submitted(
    session: AsyncSession,
    channel_id: int,
    owner_user_id: int,
    application_number: str,
) -> int: ...

async def notify_owner_verification_decided(
    session: AsyncSession,
    owner_user_id: int,
    channel_id: int,
    decision: Literal["verified", "rejected"],
    reason: str | None = None,
) -> bool: ...
```

**Delivery pattern picked empirically:** Celery enqueue via `notify_user.delay()`
— consistent с existing pattern (`notify_campaign_started`, `notify_low_balance`,
etc. all use this). Resilient: if Telegram offline, Celery retries; if user
notifications disabled, the `mailing:notify_user` task skips delivery
internally.

`notify_admins_evidence_submitted` fetches admins via existing
`UserRepository.get_all_admins()`. Returns count of admins enqueued (for
test assertions + logging).

`notify_owner_verification_decided` fetches owner via `get_by_id`, formats
message based on decision literal, enqueues notify_user.

Sessions threaded through — no implicit `async_session_factory()` created,
no commits done. Pattern 1 (caller-owns).

### New file — `tests/unit/test_bl107_submit_evidence.py` (7 tests)

| # | Test | Coverage |
|---|---|---|
| 1 | test_submit_evidence_happy_path | 200 OK + channel mutated + audit log + notify triggered с correct kwargs |
| 2 | test_submit_evidence_non_owner_forbidden | Channel owned by другой → 403 |
| 3 | test_submit_evidence_already_verified_conflict | `is_verified=True` → 409 |
| 4 | test_submit_evidence_channel_not_found | `session.get` returns None → 404 |
| 5 | test_submit_evidence_application_number_required | Missing field → 422 |
| 6 | test_submit_evidence_application_number_max_length | 65-char string → 422 |
| 7 | test_submit_evidence_with_registry_url | Valid URL accepted, channel mutated |

Mock pattern: `app.dependency_overrides` for `get_current_user` + `get_db_session`;
`monkeypatch.setattr` для `src.api.routers.channels.AuditLogRepo` and для
`src.core.services.notification_service.notify_admins_evidence_submitted`.

### New file — `tests/unit/test_bl107_admin_channel_verifications.py` (14 tests)

**List endpoint (3):**
- test_list_empty (no submissions)
- test_list_with_items (non-empty + pagination)
- test_list_filter_verified (status=verified accepted)

**Detail endpoint (2):**
- test_detail_returns_history (audit log entries included)
- test_detail_not_found (404)

**Verify endpoint (4):**
- test_verify_happy_path (all 5 audit fields + 200 response)
- test_verify_no_submission_conflict (no application_number → 409)
- test_verify_already_verified_conflict (re-verify → 409)
- test_verify_channel_not_found (404)

**Reject endpoint (3):**
- test_reject_happy_path (application_number reset, audit log, owner notified)
- test_reject_no_submission_conflict (nothing to reject → 409)
- test_reject_reason_required (empty body → 422)

**Permission (2):**
- test_non_admin_forbidden_list (real `get_current_admin_user` runs, 403)
- test_non_admin_forbidden_verify (same)

Mock pattern: similar to submit-evidence; non-admin test overrides
`get_current_user_from_web_portal` (upstream dep), letting real
`get_current_admin_user` raise 403.

## Verification

- `make typecheck`: 0/304 ✅ (+1 new file = 304)
- `make lint`: 7 baseline preserved ✅ (1 new I001 auto-fixed in admin.py during cleanup)
- `make format`: 426 files clean ✅ (2 files reformatted during cleanup)
- `alembic check`: drift-free ✅ (Phase B.5a не touches schema)
- BL-107 focused suite (B.1+B.2+B.3+B.4+B.5a): **113/113** ✅
  - test_bl107_submit_evidence: 7/7
  - test_bl107_admin_channel_verifications: 14/14
  - test_bl107_channel_add_g19_integration: 9/9
  - test_bl107_trustchannelbot_helper: 11/11
  - test_bl107_g19_gate: 22/22
  - test_bl107_schema_regression: 15/15
  - test_legal_compliance_service: 31/31
  - test_bot_channel_owner: 4/4
- Full unit suite: **696 + 91 (API) = 787 passing** ✅

## Untouched (deferred к subsequent phases)

- **Phase B.5b** — Frontend UI: 2 web_portal screens (admin review queue + detail)
  + 1 mini_app screen (owner submission form) — consumes endpoints from this phase.
- **Phase B.6** — Celery periodic task для re-verification (uses
  `settings.rkn_periodic_check_enabled`).
- **Phase B.7** — O.7 carve-out: bot handler `is_test` FSM step + admin
  permission parity.
- **Phase B.8** — BL-002 mock infrastructure.
- **Phase B.9** — E2E tests + Playwright spec unblock.
- DB schema / migrations (Phase B.1 done).
- Gate framework (Phase B.2 stable).
- Telegram helpers (Phase B.3 stable).
- Channel-add hookup (Phase B.4 stable).

## Decisions echoed (from Phase A2 design + empirical refinement)

- **Q6**: AuditLog `action` is free-form `String(64)`, NOT an enum — confirmed
  empirically. Used lowercase strings:
  `blogger_registry_evidence_submitted`,
  `blogger_registry_verified_by_admin`,
  `blogger_registry_rejected_by_admin` (snake_case per Phase B.4 precedent).
- **Q7**: Pagination convention — `limit/offset` (matches existing admin endpoints
  like `/admin/users`), not `page/limit`.
- **Q8**: Notification delivery — Celery enqueue for both admin + owner. Same
  pattern as all existing `NotificationService` methods. No new Celery task
  needed — uses existing `mailing:notify_user`.
- **Q9**: Channel owner permission — inline `if channel.owner_id != current_user.id`
  (no shared dependency exists; matches existing `delete_channel`,
  `update_category`, `get_mediakit_pdf` patterns).
- **Q10**: Error pattern — `HTTPException` direct (matches existing endpoints).
  No custom `ForbiddenError`/`NotFoundError`/`ConflictError` infrastructure exists.

## Phase B.5b dependencies surfaced

Frontend will consume these stable endpoints:
- `POST /api/channels/{id}/submit-registry-evidence` (owner — mini_app)
- `GET /api/admin/channel-verifications` (admin queue — web_portal)
- `GET /api/admin/channel-verifications/{id}` (detail — web_portal)
- `POST /api/admin/channel-verifications/{id}/verify` (web_portal action)
- `POST /api/admin/channel-verifications/{id}/reject` (web_portal action)

API contracts are locked в this phase via Pydantic schemas + tests; B.5b
frontend can be built confidently against documented shapes.

🔍 Verified against: branch HEAD pre-commit | 📅 Created: 2026-05-14
