# Phase 2 Research — Agent B
## PlacementStatus → timestamp_field semantics + `placement_status_history` backfill estimation

Working dir: `/opt/market-telegram-bot`
Branch: `feature/fz152-legal-hardening` (research probe; future helper lives on `feature/placement-transition-service`)
Mode: **Research** — no code, no migration, no model edits.

---

## 0. Sources scanned

- `src/db/models/placement_request.py` — single source for ORM fields. There is **no `placement.py`** (only `placement_request.py`). The aliases `Campaign = PlacementRequest` and `CampaignStatus = PlacementStatus` are documented in CLAUDE.md and live in `src/db/models/campaign.py`.
- `src/db/migrations/versions/0001_initial_schema.py` lines 983-1104 — column definitions for `placement_requests`.
- `src/db/repositories/placement_request_repo.py` — repo helpers `accept`, `reject`, `counter_offer`, `set_escrow`, `set_published`, `set_message_id`, `update_status`.
- `src/core/services/publication_service.py` — `publish_placement` (sets `published_at`, `last_published_at`, `scheduled_delete_at` via repo), `delete_published_post` (sets `deleted_at`, transitions to `completed`).
- `src/core/services/placement_request_service.py` — `owner_accept`, `owner_reject`, `owner_counter_offer`, `advertiser_accept_counter`, `advertiser_counter_offer`, `advertiser_cancel`, `process_payment` → `_freeze_escrow_for_payment`, `process_publication_success` (DEPRECATED), `process_publication_failure`, `auto_expire`. Also sets `expires_at` at lines 519, 618.
- `src/tasks/placement_tasks.py` — `_publish_placement_async`, `_retry_failed_publication_async` (line 637 sets escrow back), `_check_escrow_sla_async` (line 892 sets failed), `check_escrow_stuck` (line 1248 sets failed).
- `src/tasks/notification_tasks.py` line 1043 — `auto_approve_placements` flips `pending_owner` → `pending_payment`.
- `src/tasks/cleanup_tasks.py` line 154 — `archive_old_campaigns` re-stamps old `failed/cancelled/refunded` → `failed`.
- `src/tasks/dispute_tasks.py` line 108 — dispute Celery resolution sets `placement.status = new_status` (refunded / published).
- `src/api/routers/disputes.py` line 704 — admin dispute resolution sets `placement.status = new_status`.
- `src/bot/handlers/owner/arbitration.py`, `bot/handlers/advertiser/campaigns.py`, `bot/handlers/placement/placement.py`, `bot/handlers/admin/disputes.py` — bot handler mutation points (already enumerated above).

**Timestamp columns on `PlacementRequest` (model + migration agree):**

| Column | Type | Nullable | Indexed |
|---|---|---|---|
| `created_at` | DateTime(tz=True) | NO (server_default now()) | — (TimestampMixin) |
| `updated_at` | DateTime(tz=True) | NO (onupdate now()) | — |
| `expires_at` | DateTime(tz=True) | YES | YES (`ix_placement_requests_expires_at`) |
| `proposed_schedule` | DateTime(tz=True) | YES | NO |
| `final_schedule` | DateTime(tz=True) | YES | NO |
| `counter_schedule` | DateTime(tz=True) | YES | NO |
| `advertiser_counter_schedule` | DateTime(tz=True) | YES | NO |
| `scheduled_delete_at` | DateTime(tz=True) | YES | YES (`ix_placement_requests_scheduled_delete_at`) |
| `deleted_at` | DateTime(tz=True) | YES | NO |
| `published_at` | DateTime(tz=True) | YES | NO (filtered in `channel_service.py:132`) |
| `last_published_at` | DateTime(tz=True) | YES | NO |

`proposed_schedule`, `final_schedule`, `counter_schedule`, `advertiser_counter_schedule` are **user-input ad scheduling** (when the post is supposed to go live), set by handlers/services synchronously with the corresponding price-related fields, **independent of the status machine**. They are NOT timestamps of state transitions and are out of scope for `_sync_status_timestamps()`.

The four state-relevant lifecycle timestamps are: **`expires_at`**, **`scheduled_delete_at`**, **`deleted_at`**, **`published_at`** (and the lateral metric **`last_published_at`**).

---

## 1. Exhaustive mapping — PlacementStatus → timestamp impact

> Reminder: the user task spec lists 9 statuses. The model (`placement_request.py:38-50`) actually defines **10** values: `pending_owner, counter_offer, pending_payment, escrow, published, completed, failed, failed_permissions, refunded, cancelled`. The DB enum (migration line 990-1005) has an **11th value `ord_blocked`** that the model does NOT declare. Both `completed` and `ord_blocked` are flagged in §4 (objections).

### 1.1 `pending_owner` (initial state, also re-entered from advertiser counter)

| Direction | Field | Value source | Where |
|---|---|---|---|
| set | `expires_at` | `now() + 24h` | `PlacementRequestRepository.create_placement` line 79 (initial creation); `placement_request_service.advertiser_counter_offer` line 618 (re-entry from counter_offer); `bot/handlers/advertiser/campaigns.py` lines 294/298 (same logic) |
| set | `created_at` | `now()` server_default | TimestampMixin (only on initial INSERT, **not** on re-entry from `counter_offer`) |
| clear | (none) | — | — |

**Semantic:** `expires_at` — read by `placement_tasks.scan_pending_owner_expired` (line 133) and `placement_request_repo.get_expired` (line 178) to auto-expire stale offers. Read in `placement_request_service.owner_accept` line 361 to reject expired offers.

### 1.2 `counter_offer`

| Direction | Field | Value source | Where |
|---|---|---|---|
| set | `expires_at` | `now() + 3h` (service) **or** `now() + 24h` (bot handler) | `placement_request_service.owner_counter_offer` line 519 sets +3h; `bot/handlers/owner/arbitration.py:503` sets +24h. **DISCREPANCY** — see §2/§4 |
| clear | (none) | — | — |

**Semantic:** `expires_at` — read by `placement_tasks.scan_counter_offer_expired` (line 331) to auto-expire. The 3h vs 24h split is a real bug surface, not a documentation accident.

### 1.3 `pending_payment`

| Direction | Field | Value source | Where |
|---|---|---|---|
| set | `expires_at` | `now() + 24h` | `bot/handlers/owner/arbitration.py:208` (owner accepts); `bot/handlers/advertiser/campaigns.py:203` (advertiser accepts counter). The service path (`PlacementRequestRepository.accept` line 213) does **NOT** update `expires_at` — only sets `final_price`/`final_schedule`. **NON-LOCAL/INCONSISTENT** — see §2 |
| clear | (none) | — | — |

**Semantic:** `expires_at` — read by `placement_tasks.scan_pending_payment_expired` (line 236) for 24h payment SLA. The service-path miss means API-driven counter-acceptance keeps the prior 3h `counter_offer` `expires_at` intact, which clamps the payment window to whatever was left of the counter-offer window. ⚠️ likely bug.

### 1.4 `escrow`

| Direction | Field | Value source | Where |
|---|---|---|---|
| set | `escrow_transaction_id` | `Transaction.id` from `BillingService.freeze_escrow_for_placement` | `placement_request_service._freeze_escrow_for_payment` lines 760-776; INV-1 CHECK constraint |
| set | `final_price` | `placement.proposed_price` if was None | same, line 770-771 |
| set | `tracking_short_code` | `secrets.token_urlsafe(8)[:8]` | `_freeze_escrow_for_payment` lines 779-783; also fallback in `set_message_id` line 320 |
| clear | (none) | — | — |
| ⚠️ unset but logically related | `expires_at` | not cleared after escrow | once paid, `expires_at` is stale — never read for `status=escrow`, but lingers in row. See §2 |

**Semantic:** `escrow_transaction_id` — required by INV-1 CHECK (`placement_escrow_integrity`). `tracking_short_code` — required by `publication_service._build_marked_text` for tracking link. No timestamp is set here; the financial lock has its own timestamp on `Transaction`.

### 1.5 `published`

| Direction | Field | Value source | Where |
|---|---|---|---|
| set | `published_at` | `datetime.now(UTC)` | `publication_service.publish_placement` line 302; mirrored in repo `set_published` line 287 |
| set | `last_published_at` | `datetime.now(UTC)` | `publication_service.publish_placement` line 304 |
| set | `scheduled_delete_at` | `now() + FORMAT_DURATIONS_SECONDS[fmt]` (24h / 48h / 7d) | `publication_service.publish_placement` line 285 → repo `set_message_id` line 318 |
| set | `message_id` | Telegram `Message.message_id` | `publication_service` line 289 |
| set | `sent_count` | `+= 1` | line 303 |
| clear | (none) | — | — |
| ⚠️ unset | `deleted_at` | should be NULL but no defensive clear | — |

**Semantic:**
- `published_at` — read by `disputes.py:257-267` for the **48h dispute window** (financial / legal trigger), by `act_service.py:218` for акт rendering, by `ord_tasks.py:57` for ОРД отчёт о публикации, by `bot/handlers/dispute/dispute.py:52` for placement-duration delta. **High financial impact.**
- `last_published_at` — read by `api/routers/campaigns.py:523` for `started_at` field in CampaignResponse. Lower impact, but contract-visible.
- `scheduled_delete_at` — read by `placement_tasks.check_scheduled_deletions` (line 1099) as **trigger** for auto-delete; by `check_escrow_stuck` (line 1190) as 48h-stuck recovery probe; by `check_escrow_stuck` group C (line 1203) as 1h-stuck published probe. **High operational impact.**
- `sent_count` — analytics/aggregation counter (Variant B replacement of MailingLog).

### 1.6 `completed` (model has it; user spec omitted it)

| Direction | Field | Value source | Where |
|---|---|---|---|
| set | `deleted_at` | `datetime.now(UTC)` | `publication_service.delete_published_post` line 388 (set BEFORE status flip) |
| set | `status` | `PlacementStatus.completed` | line 401 (set AFTER `release_escrow` and act generation) |
| clear | (none) | — | — |

**Semantic:**
- `deleted_at` — read by `act_service.py:77` (precondition for акт), `:108` (act_date), `:200` (rendering), `:221` (template field). Read in `bot/handlers/dispute/dispute.py:53,93-95` to compute placement duration & detect early-deletion (`deleted_at < scheduled_delete_at - 5min`). **High legal/financial impact** — акт is the closing legal document for the placement.
- The pair `(deleted_at, status=completed)` together signals "пост отжил свой срок и был удалён ботом штатно". `delete_published_post` is the **only** transition to `completed`.

### 1.7 `failed`

Multiple entry points, semantics differ by entry:

| Entry | Where | Fields touched |
|---|---|---|
| Bot permissions check failed pre-publish | `publication_service.publish_placement` line 221 | `status=failed`; **no timestamp set** |
| Telegram `BadRequest` during send | `publication_service.publish_placement` line 260 | `status=failed`; `failed_count += 1`; **no timestamp** |
| ESCROW SLA exceeded (no message sent) | `placement_tasks._check_escrow_sla_async` line 892 | `status=failed`; `meta_json["sla_error"] = ...`; **no timestamp set on row, only meta** |
| Stuck escrow group B (no `message_id`) | `placement_tasks._check_escrow_stuck_async` line 1248 | `status=failed`; `meta_json["escrow_stuck_detected"]=now().isoformat()`; **timestamp lives in meta_json, not in a column** |
| Publication failure (entry from service) | `placement_request_service.process_publication_failure` line 924-927 | `status=failed` then immediately `→ refunded` line 932 |
| Retry-eligible reset | `placement_tasks._retry_failed_publication_async` line 637 | `status=escrow` (yes — backwards transition) |
| `failed → failed` re-stamp | `cleanup_tasks._archive_old_campaigns_async` line 154 | bulk UPDATE setting status=failed; **no timestamp** |

| Direction | Field | Value source |
|---|---|---|
| set | (no canonical column) | — |
| ⚠️ "failed_at" lives only in `meta_json["sla_error"]` / `meta_json["escrow_stuck_detected"]` / `meta_json["retry_count"]` | non-uniform |

**Semantic:** `failed` does **not** have a dedicated lifecycle timestamp on the row. The `updated_at` from TimestampMixin is the de-facto "failed_at". Anyone searching "когда упал placement?" must today read `updated_at` and trust no other transition happened after — fragile. See §4.

### 1.8 `failed_permissions`

Searched: **no code path** sets `PlacementStatus.failed_permissions` anywhere in `src/`. It is referenced in:
- `bot/handlers/advertiser/campaigns.py:94` — display label
- `bot/keyboards/advertiser/my_campaigns.py:14` — emoji
- `cleanup_tasks.py:70` — bulk-delete target
- `api/routers/placements.py:274` — filter mapping
- `api/routers/admin.py:126` — count grouping

| Direction | Field | Value source |
|---|---|---|
| set | (none — value is referenced but never assigned in current code) | — |

⚠️ Status exists in enum but transition is **unreachable** in current code. See §4.

### 1.9 `refunded`

| Entry | Where | Behaviour |
|---|---|---|
| Publication failure | `placement_request_service.process_publication_failure` line 932 | `status=refunded` after billing refund |
| Dispute resolution `owner_fault`/`technical` | `dispute_tasks.py:70`, `api/routers/disputes.py:662,685`, `bot/handlers/admin/disputes.py:213,240` | `status=refunded` after `billing_service.refund_escrow(scenario="before_escrow"/"after_confirmation")` |
| Cleanup re-stamp | `cleanup_tasks._archive_old_campaigns_async` | bulk includes `refunded` in selector → re-stamps as `failed` |

| Direction | Field | Value source |
|---|---|---|
| set | (no dedicated column) | — |

**Semantic:** Like `failed`, `refunded` has no row-level timestamp. The actual refund event is captured on `Transaction.idempotency_key = "refund:placement={id}:scenario={s}:..."`, which has its own `created_at`. The placement row only has `updated_at` as proxy.

### 1.10 `cancelled`

| Entry | Where | Fields |
|---|---|---|
| Owner rejects | `bot/handlers/owner/arbitration.py:294` | `status=cancelled`, `rejection_reason=<comment>` |
| Owner-side service reject | `placement_repo.reject` (called by `owner_reject`) line 231 | `status=cancelled`, `rejection_reason` if provided |
| Advertiser cancels | `bot/handlers/placement/placement.py:615` (after refund); `placement_request_service.advertiser_cancel` line 721 (calls `repo.reject` with reason="Cancelled by advertiser") | same |

| Direction | Field | Value source |
|---|---|---|
| set | `rejection_reason` | string from caller |
| set | (no dedicated timestamp column) | `updated_at` only |

**Semantic:** `count_cancellations_in_30_days` (line 292) reads `PlacementRequest.updated_at >= since` filtering by `status==cancelled` — i.e. uses `updated_at` as **de-facto `cancelled_at`** for reputation logic ("3 отмены за 30 дней"). This is **load-bearing**: the moment we add another non-cancellation transition that ends in `updated_at = now()` while status stays `cancelled`, the count goes wrong. Today nothing flips a cancelled row, but `cleanup_tasks.archive_old_campaigns` rewrites `cancelled→failed` while bumping `updated_at`. Out-of-sample but real risk. See §4.

---

## 2. Conflict matrix — fields set in one transition but never cleared in the inverse

| Field | Set on | Cleared on | Conflict |
|---|---|---|---|
| `expires_at` | `pending_owner` (init/re-entry), `counter_offer`, `pending_payment` | **never explicitly cleared** | After `→escrow`/`→published`/`→cancelled`/`→failed` the value lingers. Most readers (`scan_*_expired`) gate on `status.in_([...])` so stale rows are inert, but `placement_request_service.owner_accept` line 361 reads `expires_at` and rejects if past — a `pending_owner` row re-checked after long delay can be wrongly rejected. Low impact today (state guards filter), but a future "resurrect cancelled placement" feature would silently inherit a 24h-old `expires_at`. |
| `expires_at` (3h vs 24h) | `counter_offer` via service: 3h; `counter_offer` via bot handler: 24h | n/a | **Two transitions to the same status with different timestamp semantics.** `_sync_status_timestamps()` MUST pick one. See §4. |
| `expires_at` set on `pending_payment` | bot handlers refresh to +24h; service path `accept()` does **NOT** | n/a | Same status, two paths, different timestamp. ⚠️ Likely existing bug. See §4. |
| `published_at` | `→published` | not cleared on `→failed` (after dispute → published → refunded) or `→cancelled` (impossible from published, but dispute → refunded reachable) | A placement that was published, then disputed and refunded, will have `published_at` set + `status=refunded`. Dispute window check in `disputes.py:257` uses `published_at IS NOT NULL`, but for already-resolved placements is moot. Akт code (`act_service.py:218`) renders `published_at` as fact regardless of current status — correct. **No real conflict, just a non-locality**: the field describes a historical event, not the current state. `_sync_status_timestamps()` should NOT clear it on backwards transitions. |
| `scheduled_delete_at` | `→published` (via `set_message_id`) | not cleared on `→failed` from `escrow_stuck` group A/B | After `check_escrow_stuck` flips `status=failed`, `scheduled_delete_at` may still point to the future. `check_published_posts_health` filters `status.in_([published, completed])` (line 708) so stale `scheduled_delete_at` on `failed` row is inert. ⚠️ but `check_scheduled_deletions` (line 1099) filters only on `scheduled_delete_at <= now AND scheduled_delete_at IS NOT NULL` — **no status filter**! Re-check at line 1099. If a placement transitions `published → failed` with `scheduled_delete_at` set, this scheduler will keep firing `delete_published_post` against a `failed` row, where the guard at `publication_service.delete_published_post:345` returns "unexpected status" warning + return. Idempotent, but wastes Celery slots and emits warnings. |
| `deleted_at` | `→completed` | not cleared on any backwards transition (none exists from `completed`) | Stable terminal field. No conflict. |
| `last_published_at` | `→published` | never cleared | Mirrors `published_at` for the lateral counter. Same logic as above. |
| `message_id` | set in `set_message_id` (escrow→published) | not cleared on `→failed`/`→completed` | Similar inert-on-status-filter pattern. `check_escrow_stuck` distinguishes group A vs B by `message_id IS NOT NULL` — relies on it persisting. |
| `escrow_transaction_id` | set on `→escrow` | not cleared on `→refunded`/`→failed`/`→cancelled` | Used as financial-event link; must persist for audit. INV-1 CHECK is `status='escrow' OR transaction_id is whatever` — only enforced on the `escrow` side, so other statuses can keep the FK without violation. Correct. |
| `rejection_reason` | set on `→cancelled` (some paths) | never cleared | Terminal, fine. |
| `counter_price` / `counter_schedule` / `counter_comment` / `advertiser_counter_*` | set on `→counter_offer` / advertiser counter-counter | never cleared on `→pending_payment` accept | Once accepted, `final_price`/`final_schedule` are populated from these; the originals linger as audit trail. No conflict, but historical fields. |

**Take-away for `_sync_status_timestamps()`**: most fields are append-only event records. The ONLY ones that are state-coupled and at risk of inconsistency are `expires_at` (multi-status semantics, two-path discrepancy) and `scheduled_delete_at` (active scheduler trigger that should be cleared when leaving `published` for any non-`completed` status). The helper has limited surface; it should NOT be a global "every status has its timestamp column" pattern, because most statuses (`failed`, `refunded`, `cancelled`, `failed_permissions`) **have no such column today**.

---

## 3. Backfill estimation for `placement_status_history`

### 3.1 Current row count

```
SELECT count(*) FROM placement_requests;
 total
-------
     0

SELECT status, count(*) FROM placement_requests GROUP BY status;
 (0 rows)
```

Container `market_bot_postgres`, role `market_bot`, db `market_bot_db`. **Empty pre-launch DB** — no production data exists. CLAUDE.md confirms this: "CURRENT RULE (until first production user): Do NOT create incremental Alembic migrations for model changes — instead: edit `0001_initial_schema.py` directly".

### 3.2 Backfill verdict

**Verdict: trivial — no backfill needed.** The migration adds the `placement_status_history` table empty and that is the correct final state. No `INSERT ... SELECT` is required. Downtime cost: O(table-create) ≈ <1s.

### 3.3 Hypothetical backfill design (if data existed)

If we were post-launch with N rows:

| Final status | `changed_at` (synthetic) | `actor_user_id` (synthetic) | Notes |
|---|---|---|---|
| `pending_owner` | `created_at` | `advertiser_id` | placement just created |
| `counter_offer` | `updated_at` | unknown — could be advertiser or owner | ⚠️ ambiguous |
| `pending_payment` | `updated_at` | unknown — owner or advertiser counter-accept | ⚠️ ambiguous |
| `escrow` | `updated_at` | `advertiser_id` | only advertiser pays |
| `published` | `published_at` | NULL (system / Celery worker) | clean — dedicated column exists |
| `completed` | `deleted_at` | NULL (system / Celery worker) | clean — dedicated column exists |
| `failed` | `meta_json["escrow_stuck_detected"]` if present, else `updated_at` | NULL | ⚠️ heterogeneous source |
| `failed_permissions` | `updated_at` | NULL | unreachable in current code |
| `refunded` | `updated_at` | unknown — admin / advertiser / system | ⚠️ ambiguous (could be linked to `Transaction.idempotency_key="refund:..."` `created_at`) |
| `cancelled` | `updated_at` | `advertiser_id` if `rejection_reason="Cancelled by advertiser"`, else `owner_id` | recoverable from reason text — fragile |

**Estimation for 1×INSERT...SELECT** at any plausible launch volume (<100k rows in first year): < 5s on PostgreSQL 16. Backfill-first is feasible if the migration ever runs against populated DB.

**But**: synthetic history is **lossy by definition** — only the *final* status is recoverable. Any prior transitions (`pending_owner → counter_offer → pending_payment → escrow → published`) are collapsed to a single row. If the API endpoint that consumes `placement_status_history` is supposed to return the full timeline, the synthetic row will be a single-entry timeline for every backfilled placement — which downstream consumers must understand. See §4 for a recommendation.

### 3.4 Recommendation

Given empty DB: **ship the table empty**. Do not write a backfill at all. Document in the migration docstring: "Pre-launch — no historical placements exist; future placements gain history rows via `_sync_status_timestamps()` on every transition. Synthetic backfill never required." If launch happens before the helper merges, capture this as a follow-up: a synthetic INSERT with the table above, executed once.

---

## 4. Возражения и риски (Objections and risks)

### 4.1 The 9 vs 10 vs 11 status mismatch ⚠️ block

The user task lists 9 statuses; the model declares 10 (adds `completed`); the DB enum has 11 (adds `ord_blocked`).

- **`completed`** is a real, reachable, financially-load-bearing status — it is the only state where the act of завершения is generated and escrow is finally released. Excluding it from the mapping helper means the helper cannot represent the end-of-life of a successful placement. The plan must include `completed`.
- **`ord_blocked`** exists in the DB enum but the model does not declare it. No code path sets it. It is a **schema drift** — either model needs to add it or the migration needs to drop it. Do not map a status that the model cannot produce.

### 4.2 `expires_at` semantic is multi-valued ⚠️ block

The same column carries different meanings in different states:
- `pending_owner`: 24h to accept
- `counter_offer`: 3h (service path) **or** 24h (bot handler path) — **inconsistent within the same status**
- `pending_payment`: 24h to pay (only on bot handler path; service path leaves prior value)

A `_sync_status_timestamps()` helper that simply does `expires_at = now() + 24h` whenever entering one of these statuses will:
1. Change semantics for `counter_offer` from 3h to 24h on the service path, weakening the negotiation deadline.
2. Mask the bot-vs-service discrepancy by retroactively forcing one branch.

Recommendation: before the helper, **fix the discrepancy** as a separate ticket. Pick 3h or 24h for `counter_offer`, pick consistent +24h for `pending_payment`, then have the helper enforce the chosen rule.

### 4.3 No timestamp column for terminal failures ⚠️ block

`failed`, `failed_permissions`, `refunded`, `cancelled` have NO dedicated column. The "when did it fail/refund/cancel?" answer today comes from `updated_at` (pure proxy) plus scattered `meta_json` keys (`sla_error`, `escrow_stuck_detected`, `retry_count`).

Two consequences:
- `count_cancellations_in_30_days` (line 292) uses `updated_at` as proxy for `cancelled_at`. If the helper bumps `updated_at` on any transition (it will, via `onupdate=func.now()`), reputation logic stays correct only as long as `cancelled` is terminal. `cleanup_tasks.archive_old_campaigns` violates this: it bulk-rewrites `cancelled → failed`, bumping `updated_at`. Today the reputation query gates by `status==cancelled` so the rewrite hides the row from the count — **fine**. But if anyone changes the gate to "any cancellation in last 30d regardless of current status", the rewrite quietly masks the data.
- The future `placement_status_history` table is the right place to put per-transition timestamps, freeing us from inventing `failed_at`/`refunded_at`/`cancelled_at` columns. But until that history is the source of truth, the helper should **not pretend** these statuses have row-level timestamps. Mapping table for these statuses should be `(timestamp_fields_to_set=[], timestamp_fields_to_clear=[])`.

### 4.4 `scheduled_delete_at` keeps firing on non-published rows ⚠️ block

`placement_tasks.check_scheduled_deletions` (line 1097-1102) selects rows where `scheduled_delete_at <= now AND scheduled_delete_at IS NOT NULL` — **no status filter**. After `check_escrow_stuck` flips a stuck row to `failed` while leaving `scheduled_delete_at` set, this scheduler will repeatedly enqueue `delete_published_post` against a `failed` row. The handler's status guard makes it idempotent, but the workload is wasted and warnings spam logs.

The helper SHOULD clear `scheduled_delete_at` when transitioning out of `published` to anything except `completed`. Add it to `timestamp_fields_to_clear` for `→failed` (group A/B/C) and any future `published → cancelled`/`refunded` (e.g., dispute path that produces `refunded` after `published`).

### 4.5 `failed_permissions` is unreachable ⚠️ defer (was raise)

The status is referenced by display/filter/cleanup logic but never assigned. Either it's dead code or there's a missing transition path. Not a blocker for the helper (helper will simply have an unused entry), but flag for cleanup ticket.

### 4.6 `process_publication_failure` makes two transitions in sequence (`→failed` then `→refunded`)

Lines 924-933 of `placement_request_service.py` call `placement_repo.update_status(failed)` then immediately `placement_repo.update_status(refunded)`. With `_sync_status_timestamps()` and `placement_status_history` tracking each transition, this will produce **two history rows** for one logical event (publication failure with refund). Two interpretations:

(a) Correct — semantically there are two transitions: "publication failed" then "money refunded". History should reflect both.
(b) Wrong — the intermediate `failed` is a transient implementation artifact that the user never observes.

Plan must pick one. If (b), the service should make a single `→refunded` transition. If (a), the helper needs to handle both transitions atomically (don't drop one because they share a session.flush).

### 4.7 Re-entry to `pending_owner` from `counter_offer` (advertiser counter-counter) is data-lossy

`placement_request_service.advertiser_counter_offer` line 617 sets `status = pending_owner` again. The first `pending_owner` happened at INSERT. This is the second time the placement enters `pending_owner`. With `placement_status_history`, that produces **two rows of `→pending_owner`**, which is the right answer (ping-pong negotiation). But the helper must NOT key history rows by `(placement_id, status)` UNIQUE — it must allow repeats. Plan §3 should explicitly state PRIMARY KEY = `(id)` autoincrement, NOT `(placement_id, status)`.

### 4.8 Migration target column for `published_at` already exists — risk of double-bookkeeping

`published_at` is a real column today. After `placement_status_history` lands, the same fact lives in two places: the column and a history row. If the helper is the only writer, they stay in sync. If any direct-SQL writes happen (admin override, data-fixup script), they desync. Plan should document: "Do not write `placement_requests.published_at` outside `_sync_status_timestamps()`; for ad-hoc data fixes, write the history row and let a recompute view derive the column" — or make `published_at` a generated column (PostgreSQL 12+ supports STORED) deriving from history. Otherwise this is a long-tail data-quality risk.

### 4.9 Possible follow-up improvements (defer; do not block)

- `proposed_schedule` / `final_schedule` / `counter_schedule` / `advertiser_counter_schedule` are named ambiguously; they are *user-input ad scheduling*, not lifecycle timestamps. Renaming could prevent future contributors mistaking them for transition records.
- The `is_test=True` path goes through every state machine transition; tests would benefit from explicit fixture coverage of `is_test=true → completed` to lock in that the helper plays nicely with zero-amount transactions.

---

## 5. Summary

**Statuses mapped:** 10 (the 9 from the user spec + `completed` raised in §4.1; excluding `ord_blocked` which is enum-only schema drift).

**Conflict-matrix entries:** 9 fields with cross-status persistence behaviour (§2). The substantively load-bearing ones are `expires_at` (3 conflicts) and `scheduled_delete_at` (1 active firing on stale state).

**Backfill row count:** 0 rows (empty pre-launch DB). **Verdict: ship the table empty, no backfill required.** Synthetic-fallback design provided in §3.3 in case launch happens before the helper merges.

**Objections:** 9 raised in §4 (4 blocking-grade — model/enum mismatch, `expires_at` multi-semantic, terminal-status no-timestamp, `scheduled_delete_at` unfiltered scheduler; 5 deferable / context).

🔍 Verified against: 016c4c9a5498267905ec28afdd31666a598c1be4 | 📅 Updated: 2026-04-26T00:00:00Z
