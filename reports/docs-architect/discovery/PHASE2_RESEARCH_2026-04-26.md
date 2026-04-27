# Phase 2 Research — Consolidation Report

**Goal of Phase 2:** introduce `PlacementTransitionService.transition()` as the
sole entrypoint for `PlacementRequest.status` mutations, with structured
`TransitionMetadata`, a `placement_status_history` audit table, and a
`_sync_status_timestamps()` helper that keeps row-level lifecycle timestamps
consistent.

**This report consolidates three parallel research artefacts:**
- `PHASE2_RESEARCH_AGENT_A_2026-04-26.md` — mutation-point inventory (19 in-scope points + 11 indirect via repo helpers)
- `PHASE2_RESEARCH_AGENT_B_2026-04-26.md` — status → timestamp mapping + backfill estimation
- `PHASE2_RESEARCH_AGENT_C_2026-04-26.md` — existing-metadata defensive scan + Pydantic recommendation

**Mode:** research / planning. No code, no migration, no CLAUDE.md edit. Output
of this report is input to plan-alignment commit § 2.B.0.

**Status:** STOP. Awaiting user review / corrections before § 2.B.0 alignment commit.

---

## 1. Mutation surface — what `transition()` must subsume

**Direct in-scope points:** 19 — 9 direct attribute writes + 11 reach via
`placement_repo.{accept,reject,counter_offer,set_escrow,set_published,update_status}` (repo
out of scope of inventory, listed in §1b of Agent A for completeness).

**By layer:**
- `src/core/services/` — 5 direct + 9 indirect
- `src/api/routers/` — 1 direct (admin disputes resolve) + 2 indirect (campaigns start/cancel)
- `src/tasks/` — 7 direct (5 distinct Celery tasks + 1 bulk normaliser + 1 orphan)
- `src/bot/handlers/` — 7 direct (owner arbitration, advertiser campaigns, placement, admin disputes)

**Mutation types:** 16 single-row ORM, 1 bulk update (cleanup), 0 constructor, 0 setattr, 0 other.

**Bulk candidates:** 1 (`cleanup:archive_old_campaigns`) — but flagged as
semantically broken (rewrites two terminal states into a third — see Tier-1
objection T1-7). Not a true bulk transition.

**Celery tasks mutating status:** 7. Of those, only `dispute:resolve_financial`
needs a non-`None` `actor_user_id` in its signature (admin caller has it).
The other six are scheduler-driven; `actor_user_id=None` is the right default.

→ Full table: see Agent A §1, §1b, §2, §3.

---

## 2. Status → timestamp mapping (synthesised for `_sync_status_timestamps()`)

The state machine has **10 statuses in the ORM model** (the user spec lists 9;
`completed` is missing from the spec but is real and load-bearing). The DB
enum carries an 11th value `ord_blocked` that the model does not declare —
schema drift, not a status (see Tier-1 T1-2).

**Helper mapping** — only the four state-relevant lifecycle timestamps
(`expires_at`, `scheduled_delete_at`, `deleted_at`, `published_at` /
`last_published_at`) plus the financial sentinels (`escrow_transaction_id`,
`tracking_short_code`, `final_price`, `message_id`):

| to_status | set | clear | Notes |
|---|---|---|---|
| `pending_owner` (init) | `expires_at = now()+24h`, `created_at` (server_default) | — | re-entry from advertiser counter sets `expires_at = now()+24h` again |
| `counter_offer` | `expires_at = now()+?h` | — | **3h vs 24h discrepancy** between service and bot — see T1-3 |
| `pending_payment` | `expires_at = now()+24h` | — | bot handlers do this; service path `repo.accept()` does **NOT** — see T1-3 |
| `escrow` | `escrow_transaction_id`, `final_price` (if None), `tracking_short_code` | — | INV-1 CHECK: `status='escrow' ⇒ escrow_transaction_id IS NOT NULL` |
| `published` | `published_at = now()`, `last_published_at = now()`, `scheduled_delete_at = now()+FORMAT_DURATIONS[fmt]`, `message_id`, `sent_count += 1` | — | scheduled_delete_at MUST be cleared on backwards transitions out of `published` (see T1-5) |
| `completed` | `deleted_at = now()` | — | only via `delete_published_post`. `(deleted_at, status=completed)` is the closing pair |
| `failed` | (no canonical column) | `scheduled_delete_at` if prior was `published` | "failed_at" lives in `meta_json["sla_error"]` / `meta_json["escrow_stuck_detected"]` / `updated_at` — heterogeneous; helper does NOT pretend a column exists (see T1-4) |
| `failed_permissions` | (none — value unreachable in current code) | — | enum value never assigned; either delete or wire up (T2-5) |
| `refunded` | (no canonical column) | — | actual event captured on `Transaction.idempotency_key="refund:..."` |
| `cancelled` | `rejection_reason` (if provided) | — | `count_cancellations_in_30_days` reads `updated_at` as de-facto `cancelled_at` — load-bearing for reputation logic |

**Helper contract for terminal failures (`failed`/`refunded`/`cancelled`/`failed_permissions`):**
mapping returns `(set=[], clear=[scheduled_delete_at if prior==published])`.
`updated_at` from TimestampMixin is the de-facto transition timestamp; the new
`placement_status_history` table becomes the source of truth for "when did
this placement enter status X?".

→ Full per-status detail: Agent B §1.

---

## 3. Conflict matrix — what `transition()` must clear on backwards moves

| Field | Set on | Must clear on | Severity |
|---|---|---|---|
| `expires_at` | `pending_owner`, `counter_offer`, `pending_payment` | not strictly required (state guards filter readers), but `→escrow`/`→published`/`→cancelled` should explicitly null it to avoid resurrected-row time-bombs | low (latent) |
| `scheduled_delete_at` | `→published` | `published → failed` (group A/B/C from `check_escrow_stuck`), `published → refunded` (dispute), any `published → !completed` | **MEDIUM (active)** — `check_scheduled_deletions` selects with no status filter (`placement_tasks.py:1099`), keeps firing `delete_published_post` on stale `failed` rows (idempotent but wastes Celery slots). See T1-5 |
| `published_at`, `last_published_at`, `message_id`, `escrow_transaction_id`, `rejection_reason`, `counter_*` | various | NEVER cleared | append-only event records — describe history, not current state. helper must NOT clear these |

→ Full matrix (9 entries): Agent B §2.

---

## 4. Backfill estimation for `placement_status_history`

**Current row count:** `SELECT count(*) FROM placement_requests` → **0 rows**.
Container `market_bot_postgres`, role `market_bot`, db `market_bot_db`. Empty
pre-launch DB matches CLAUDE.md current rule ("Pre-Production Migration Strategy").

**Verdict:** ship the migration with the table empty. **No `INSERT ... SELECT`
backfill required.** Downtime cost: <1s (table create + indexes).

**Documentation in migration docstring:**
> Pre-launch — no historical placements exist; future placements gain history
> rows via `_sync_status_timestamps()` on every transition. If launch happens
> before this helper merges, fall back to synthetic single-row backfill per
> Agent B §3.3.

**Synthetic-fallback design** (in case launch precedes merge): see Agent B §3.3.
Estimated <5s for any plausible launch volume (<100k rows).

---

## 5. TransitionMetadata — Pydantic schema recommendation

**Closed model, no `extra="allow"`.** Every field is enum / internal PK /
synthetic key / constrained Literal. Zero free-form user input. Zero PII.

```python
class TransitionMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Starter set (from user spec) — all KEEP, none redundant
    task_name: str | None = None              # promoted from Celery on_success log
    error_code: Literal[
        "telegram_bad_request",
        "bot_not_admin",
        "insufficient_permissions",
        "erid_missing",
        "escrow_sla_exceeded",
        "escrow_stuck",
        "ord_register_failed",
        # ... extend per publication_logs.event_type + financial codes
    ] | None = None                           # CONSTRAINED — not free-form str
    gate_attempt: int | None = None           # decoupled from Celery retries
    from_admin_id: int | None = None          # internal users.id, NOT telegram_id
    celery_task_id: str | None = None         # Celery UUID

    # Strong additions
    from_status: PlacementStatus              # required — load-bearing fact
    to_status: PlacementStatus                # required
    trigger: Literal[
        "api", "celery_beat", "celery_signal", "admin_api", "system",
    ]                                         # distinguishes auto-cancel vs admin-cancel
    idempotency_key: str | None = None        # links to Transaction.idempotency_key
    correlation_id: str | None = None         # request-scoped UUID

    # Conditional — depend on Phase 2 storage choice
    placement_id: int | None = None           # only if metadata moves to separate table
    attempted_at: datetime | None = None      # only if separating attempts from successes
```

**Why this passes FZ-152:** every field is enum / internal PK / synthetic key.
**Forbidden** (must NOT be added even though they appear in existing logging):
`telegram_id`, `ip_address`, `user_agent`, `phone_number`, `email`, `inn`,
`passport_*`, `bank_account`, `legal_name`, free-form `description`/`comment`,
free-form `rejection_reason`-like text. See Agent C §3 PII table for explicit
FZ-152 reason per field.

**Why this is non-redundant:** every field promotes a fact that today lives
only in unstructured log strings. No duplication of `audit_logs` (keyed by
resource_type/id, not by transition) or `Transaction.meta_json` (financial
domain).

**Caveat — `from_admin_id` overlaps `audit_logs.user_id` for admin paths.**
Decided KEEP because (a) audit_logs requires a join to recover per-placement
history; (b) audit_logs can be incomplete if admin path bypasses sensitive-
prefix middleware. Document the overlap in the model docstring so a future
maintainer doesn't strip the field.

→ Full inventory of existing logging channels (18 entries) + PII boundary
table: Agent C §1, §3.

---

## 6. Celery actor convention

| Task | Signature gains `actor_user_id` | Default value source |
|---|---|---|
| `notifications:auto_approve_placements` | NO — Beat-only | `None` (system actor) |
| `placement:publish_placement` | NO — chain-dispatched from `_schedule_publication_task` | `None` (no human in chain) |
| `placement:retry_failed_publication` | UNCLEAR — no live dispatcher (see T2-1) | TBD when revived |
| `placement:check_escrow_sla` | NO — Beat-only | `None` |
| `placement:check_escrow_stuck` | NO — Beat-only | `None` |
| `placement:delete_published_post` | NO — scheduler-driven | `None` |
| `dispute:resolve_financial` | YES — caller is admin (if revived; see T1-6) | `int` (admin user id from `request.state.user_id`) |
| `cleanup:archive_old_campaigns` | NO — Beat (and likely deletion candidate, see T1-7) | `None` |

**Convention:** request-scoped routers pass `request.state.user_id` into the
task signature; scheduler-dispatched tasks pass `None`. The transition service
records `actor_user_id` into `placement_status_history.actor_user_id`
(nullable). Internal `users.id`, never `telegram_id`.

---

## 7. Возражения и риски — единый приоритизированный список

**Total raised:** 27 across the three agents (A: 10, B: 9, C: 8). Some overlap.
Below: deduplicated, prioritised.

### Tier 1 — BLOCKING before plan-alignment commit § 2.B.0

These must have a written decision (one of: fix in Phase 2 / fix in separate
pre-Phase-2 ticket / accept and document) before `transition()` design is
frozen. Skipping them lets ambiguity leak into the implementation.

**T1-1 — Two parallel mutation APIs cannot coexist with `transition()`** (Agent A O-3)

11 in-scope mutation points reach `placement.status` via `placement_repo.{accept,reject,counter_offer,set_escrow,set_published,update_status}`. These helpers each do `placement.status = X; await session.flush()` — functionally a third copy of "transition logic without invariants". If left in place, any new code importing `PlacementRequestRepository` re-introduces the bypass.

**Decision required:** in the Phase 2 PR, either (a) delete the six repo helpers and rewrite the eleven callers to go through the service, or (b) gut the helpers' bodies into thin `await self._transition_service.transition(...)` calls. The choice affects Phase 2 scope by ~11 service-layer rewrites; cannot be deferred.

**T1-2 — State machine spec mismatch: 9 vs 10 vs 11 statuses** (Agent A O-9 + Agent B §4.1)

- User task spec: 9 statuses
- ORM model (`placement_request.py:38-50`): 10 (adds `completed` — load-bearing, only state where act генерируется и escrow finally released)
- DB enum (migration line 990-1005): 11 (adds `ord_blocked` — neither model nor any code declares it)
- CLAUDE.md state-machine doc: 6 (incomplete)

**Decision required:** authoritative spec for `transition()`'s allow-list. Most likely: ORM model is canonical (10 statuses incl. `completed`), DB enum drops `ord_blocked` (separate migration in Phase 2 or pre-Phase-2 cleanup), CLAUDE.md doc gets updated. Cannot design `transition()` against a moving target.

**T1-3 — `expires_at` multi-semantic + 3h/24h discrepancy (existing bug)** (Agent B §4.2)

The same column carries different deadlines in different states:
- `pending_owner`: 24h (consistent)
- `counter_offer`: **3h** (service: `placement_request_service.owner_counter_offer:519`) **OR** **24h** (bot handler: `bot/handlers/owner/arbitration.py:503`) — same status, two paths
- `pending_payment`: bot handlers refresh to +24h; service path `repo.accept()` does **NOT** (retains prior `counter_offer` value, clamping the payment window) — likely existing bug

A `_sync_status_timestamps()` helper that simply does `expires_at = now()+24h` whenever entering one of these statuses would silently change negotiation deadline semantics on the service path.

**Decision required:** fix the discrepancy in a separate pre-Phase-2 ticket. Pick 3h or 24h for `counter_offer`, pick consistent +24h for `pending_payment`, then have the helper enforce the chosen rule. Cannot ship the helper while two paths disagree.

**T1-4 — Terminal statuses have no row-level timestamp column** (Agent B §4.3)

`failed`, `failed_permissions`, `refunded`, `cancelled` have NO dedicated column. "When did it fail?" today is recoverable only from `updated_at` (proxy) plus scattered `meta_json` keys (`sla_error`, `escrow_stuck_detected`, `retry_count`).

**Decision required:** confirm the helper does NOT pretend these statuses have row-level timestamps (mapping returns `(set=[], clear=[…])`). The future `placement_status_history` table is the source of truth for per-transition timestamps; freeing us from inventing `failed_at`/`refunded_at`/`cancelled_at` columns. Affects helper contract directly.

**Sub-risk:** `count_cancellations_in_30_days` (`reputation_repo.py:292`) reads `updated_at` as de-facto `cancelled_at`. `cleanup_tasks.archive_old_campaigns` rewrites `cancelled→failed` while bumping `updated_at` — masks rows from the count today (gate by `status==cancelled`). Anyone changing the gate to "any cancellation in last 30d regardless of current status" silently breaks reputation logic. Document the dependency.

**T1-5 — `scheduled_delete_at` keeps firing on non-published rows** (Agent B §4.4)

`placement_tasks.check_scheduled_deletions` (line 1097-1102) selects rows where `scheduled_delete_at <= now AND scheduled_delete_at IS NOT NULL` — **no status filter**. After `check_escrow_stuck` flips a stuck row to `failed` while leaving `scheduled_delete_at` set, this scheduler keeps enqueueing `delete_published_post` against a `failed` row (idempotent guard at the handler returns "unexpected status", but Celery slots wasted, warnings spam logs).

**Decision required:** the helper MUST clear `scheduled_delete_at` when transitioning out of `published` to anything except `completed`. Add it explicitly to the conflict matrix (§3 above). This is an active scheduler bug fixed by the helper's clearing logic.

**T1-6 — `dispute:resolve_financial` Celery task is parallel-impl orphan** (Agent A O-1)

The task at `dispute_tasks.py:18-120` and the synchronous router path at `disputes.py:639-706` (and bot handler at `admin/disputes.py:200-253`) implement the **same** dispute resolution flow. Yet:
1. The task has zero dispatchers (`grep` clean) — cannot fire today.
2. The router path violates S-48 transaction contract (calls `await session.commit()` inline at `disputes.py:706`).
3. The bot handler is a third copy.

**Decision required:** before Phase 2 wraps all three call-sites in `transition()`, decide whether the canonical path is sync or async.
- **If sync:** delete the task and the bot-handler copy, route bot through API. Recommended (admin sees a result page; async opens a window where dispute resolved but `placement.status` not yet updated, → bug reports).
- **If async:** delete inline router/handler bodies, dispatch the task, accept eventual-consistency window for admin users.

Cannot choose during implementation — affects which call-sites get rewritten in the Phase 2 PR.

**T1-7 — `cleanup:archive_old_campaigns` mutates already-terminal rows (existing bug)** (Agent A O-2)

`src/tasks/cleanup_tasks.py:140-156` rewrites `cancelled → failed` and `refunded → failed` for rows older than `months*30` days. That is data-loss-by-overwrite of two distinct terminal states, not archival.

**Decision required:** wrapping this in `bulk_transition()` legitimises a bug. Either (a) delete the task (if intent was "delete old rows" — replace with DELETE), (b) replace `status=` overwrite with separate `is_archived` column flag, or (c) explicitly accept the data-loss semantics and document why. Sprint-level question, not a refactor target.

**T1-8 — `placement_status_history` PRIMARY KEY** (Agent B §4.7)

Re-entry to `pending_owner` from `counter_offer` (advertiser counter-counter, `placement_request_service.advertiser_counter_offer:617`) creates **two `→pending_owner` history rows** for one placement. Correct semantically (ping-pong negotiation), but the helper must NOT key history rows by `(placement_id, status)` UNIQUE — it must allow repeats.

**Decision required:** plan §3 must explicitly state `placement_status_history.id` autoincrement PRIMARY KEY, NOT `(placement_id, status)`. One-line schema decision but easy to miss.

**T1-9 — `process_publication_failure` writes two transitions in sequence** (Agent A O-7 + Agent B §4.6)

`placement_request_service.py:923-933` calls `repo.update_status(failed)` then immediately `repo.update_status(refunded)`. With `placement_status_history`, this produces **two history rows** for one logical event ("publication failed" + "money refunded").

**Decision required:** pick interpretation.
- **(a) Correct two-step:** there really are two transitions; history reflects both. Helper handles both atomically (both rows in same flush).
- **(b) Implementation artifact:** intermediate `failed` is transient; user never observes it. Service should make a single `→refunded` transition.

Affects what the user sees in "history of placement N" and how the helper batches transitions in one method.

### Tier 2 — Should resolve in plan, may defer to implementation if explicitly noted

**T2-1 — `placement:retry_failed_publication` skips escrow re-validation (latent bug)** (Agent A O-4)

Sets `failed → escrow` without restoring `escrow_transaction_id` invariant (INV-1). If escrow was already refunded by `check_escrow_sla`, the row becomes inconsistent.

**Plan resolution:** `transition()` adds INV-1 as precondition for `→escrow`. `retry_failed_publication` is rewritten to detect refunded-case before transition, OR deleted if confirmed dead (no live dispatcher found, see T2-2).

**T2-2 — `placement:retry_failed_publication` likely dead** (Agent A §4 dead-code)

No `.delay`/`.apply_async` call found in `src/`. Either dead, or used only by ops via `celery call ...`.

**Plan resolution:** verify Beat schedule + ops runbook. If neither uses it, delete in same Phase 2 PR. If ops uses it, fix per T2-1.

**T2-3 — Bot handlers skip status preconditions** (Agent A O-6)

`bot/handlers/owner/arbitration.py:289-294` (`reject_request_comment`) and `:492-502` (`_send_counter_offer`) only check `req` existence, not `req.status`. Stale FSM state can blow past preconditions enforced in service path.

**Plan resolution:** `transition()` rejects illegal transitions with explicit error type; handlers surface error to user. Silent state-corruption is current behaviour; the new service is the fix.

**T2-4 — Admin-override status guards need explicit policy** (Agent A O-8)

Six in-scope mutation points write `placement.status = X` without first asserting `placement.status == expected`. `transition()` makes guards trivial — but the question is whether to enforce a single global allow-list per `(from_status, to_status)` or accept admin-override paths (dispute resolution legitimately writes to a published placement).

**Plan resolution:** decide once, document in service header. Two-mode policy reasonable:
- `transition()` enforces strict allow-list for organic transitions
- `transition_admin_override(reason: str, ...)` allows arbitrary `(from, to)` pairs but requires explicit reason in metadata, written to history

**T2-5 — `PlacementStatus.failed_permissions` is unreferenced** (Agent A O-10 + Agent B §4.5)

Referenced by display/filter/cleanup code but never assigned. Either dead enum value or missing transition path (probable: `PublicationService` uses `failed` after `BotNotAdminError`/`InsufficientPermissionsError` where `failed_permissions` was likely intended).

**Plan resolution:** in same PR, either delete the enum value (schema cleanup) or wire `→failed_permissions` for permission-check failures and update the helper mapping.

**T2-6 — `published_at` double-bookkeeping risk** (Agent B §4.8)

After history table lands, `published_at` exists in two places: column + history row. If only the helper writes, they stay in sync. Direct-SQL writes (admin override, data-fixup script) desync.

**Plan resolution:** either (a) document in helper docstring "do not write `placement_requests.published_at` outside `_sync_status_timestamps()`", or (b) make `published_at` a generated column STORED deriving from history (PostgreSQL 12+). Option (b) is more robust but adds migration complexity. Decide before § 2.B.0.

### Tier 3 — Defer to Phase 3 / backlog (out of Phase 2 scope)

**T3-1 — `cleanup:archive_old_campaigns` missing explicit `queue=`** (Agent A O-5)

CLAUDE.md "Rules for new tasks" requires explicit `queue=` in decorator. Predates the rule. Audit-finding for the implementer; small fix-up commit can land alongside Phase 2 if convenient, but not blocking.

**T3-2 — `audit_logs.ip_address` / `user_agent` retention** (Agent C O-2)

PII (FZ-152), retained indefinitely (no purge job). Phase 3 backlog: define rolling-purge policy.

**T3-3 — Sentry breadcrumb leak** (Agent C O-3)

`auth.py` WARN-level logs include `user_id` + `ip` → cross Sentry breadcrumb bar. Phase 3: review `before_send` hook to scrub.

**T3-4 — `placement_requests.rejection_reason` is free-form text** (Agent C O-4 / F-3)

Free-form Russian text typed by owners — definitely PII-risk. Stays in column; Phase 2's `metadata_json` must NOT duplicate. Phase 3: FZ-152 retention review for `rejection_reason`.

**T3-5 — `Transaction.description` free-form drift** (Agent C O-5)

Same anti-pattern Phase 2 is asked to avoid for `metadata_json`. Phase 3: review whether to migrate to enum.

### Tier 4 — Confirmed / informational (no action needed)

- **C-O-1:** `audit_logs.user_id` and `target_user_id` are internal user PKs, not telegram IDs — confirmed safe.
- **C-O-6:** unstructured log f-strings as anti-pattern — justifies Phase 2's structured `metadata_json` direction.
- **C-O-7:** `from_admin_id` duplicates `audit_logs.user_id` — decided KEEP with documented overlap.
- **C-O-8:** `telegram_id` PII boundary — confirmed; metadata uses internal `user_id` only.

---

## 8. Вопросы для подтверждения § 2.B.0 (минимальные)

After Tier-1 decisions are made, the following must land in the `docs(phase-2): align plan with PF.X / O.Y decisions` commit:

1. **Final state-machine spec** (T1-2 outcome) — list of statuses for `transition()`'s allow-list.
2. **Repo-helper disposition** (T1-1 outcome) — delete or thin-wrap.
3. **`expires_at` semantics** (T1-3 outcome) — 3h or 24h for `counter_offer`; +24h for `pending_payment`.
4. **Helper conflict-matrix decisions** (§3 + T1-5) — what to clear when.
5. **`TransitionMetadata` schema** (§5) — frozen field list + Literal enums for `error_code` and `trigger`.
6. **Bulk-list** — only `cleanup:archive_old_campaigns` is currently bulk; T1-7 may eliminate it. If so, `bulk_transition()` is not part of Phase 2 scope.
7. **Lint-scope** — forbidden-pattern guard for `placement.status =` outside `PlacementTransitionService` (similar to the ESLint rule for portal API imports).
8. **Celery actor convention** (§6) — propagation rules.
9. **Legacy backfill spec** (§4) — empty-DB ship-as-empty + synthetic-fallback design captured in migration docstring.
10. **`placement_status_history` PRIMARY KEY** (T1-8) — autoincrement `id`, NOT `(placement_id, status)`.
11. **Dispute path: sync or async** (T1-6) — affects which mutation points get rewritten.
12. **Two-step vs single transition for publication failure** (T1-9).

---

## 9. Что НЕ делается в Phase 2 (явный non-scope)

- **No retention policy for `audit_logs.ip_address`/`user_agent`** (T3-2 — Phase 3).
- **No `Sentry before_send` hook update** (T3-3 — Phase 3).
- **No FZ-152 retention review for `rejection_reason`/`Transaction.description`** (T3-4, T3-5 — Phase 3).
- **No fix for `auth.py` PII log leak** (Agent C O-3 — Phase 3).
- **`bulk_transition()` may not exist** if T1-7 deletes `archive_old_campaigns`. If retained, it's a thin wrapper for documented bulk semantics, not a general bulk API.

---

## 10. Sources

- `reports/docs-architect/discovery/PHASE2_RESEARCH_AGENT_A_2026-04-26.md` — mutation inventory + Celery enumeration + 10 objections
- `reports/docs-architect/discovery/PHASE2_RESEARCH_AGENT_B_2026-04-26.md` — timestamp mapping + conflict matrix + backfill estimation + 9 objections
- `reports/docs-architect/discovery/PHASE2_RESEARCH_AGENT_C_2026-04-26.md` — existing-metadata inventory + Pydantic schema recommendation + 8 objections / boundary checks

---

🔍 Verified against: 016c4c9a5498267905ec28afdd31666a598c1be4 | 📅 Updated: 2026-04-26T08:35:00Z
