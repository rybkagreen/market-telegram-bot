# S-40: Tech Debt Audit — Dead Code, Unused Directories, Low-Priority Cleanups

> **Sprint:** S-40 | **Phase:** Research | **Date:** 2026-04-17  
> **Scope:** D-06, D-07, D-10, D-20, PlaceholderScreen, Stubs (FNS, ORD)  
> **Mode:** read_only — no files edited

---

## Stop-and-Report Checks

- **Active callers of "dead" endpoints/tasks:** ✅ None found — all confirmed dead.  
- **Empty dir with `.gitkeep`/`__init__.py`:** ✅ Not present — `reports/monitoring/payloads` is genuinely empty (no hidden files).

---

## D-06: `check_pending_invoices` — Dead Celery Task

### Evidence

**File:** `src/tasks/billing_tasks.py:158–166`

```python
@celery_app.task(name="billing:check_pending_invoices", queue="billing")
def check_pending_invoices() -> dict:
    """DEPRECATED: Removed in v4.5. No-op — safe to delete."""
    return {"deprecated": True, "removed_in": "v4.5"}

async def _check_pending_invoices() -> dict:
    """DEPRECATED: Removed in v4.5."""
    return {"deprecated": True, "removed_in": "v4.5"}
```

**Grep result** (`grep -rn 'check_pending_invoices' src/`):

```
src/tasks/billing_tasks.py:158  @celery_app.task(name="billing:check_pending_invoices", ...)
src/tasks/billing_tasks.py:159  def check_pending_invoices() -> dict:
src/tasks/billing_tasks.py:164  async def _check_pending_invoices() -> dict:
```

Only declarations, zero callers. Not in Celery Beat config (already removed per D-06 context).

### Verdict

| Attribute | Value |
|---|---|
| **safe_to_remove** | ✅ YES |
| **risk** | Zero — no callers, no Beat schedule |
| **scope** | Delete lines 158–166 (`check_pending_invoices` + `_check_pending_invoices`) |
| **note** | Also remove `queue="billing"` reference from `billing_tasks.py` imports if nothing else uses the billing queue after removal |

---

## D-07: `GET /api/billing/invoice/{id}` — Ghost Endpoint

### Evidence

The endpoint is listed in the **module docstring** of `src/api/routers/billing.py:9` but **never implemented**. No `@router.get("/invoice/{id}")` decorator exists anywhere in the file.

The actual endpoint serving this purpose is:

```python
@router.get("/topup/{payment_id}/status", ...)  # billing.py:203
```

Its docstring explicitly states: `Alias для GET /invoice/{invoice_id}`.

**Frontend grep** (`grep -rn 'billing/invoice' mini_app/src/ web_portal/src/`):

```
(no matches)
```

Neither `mini_app` nor `web_portal` ever calls `/billing/invoice/`. No consumers.

### Verdict

| Attribute | Value |
|---|---|
| **safe_to_remove** | ✅ YES (docstring line only) |
| **risk** | Zero — endpoint was never implemented; no consumers |
| **scope** | Remove stale entry from `billing.py:9` docstring |
| **actual_endpoint** | `/api/billing/topup/{payment_id}/status` (active, used) |

---

## D-10: Redis Sync Client in `placement_tasks.py`

### Current state

**File:** `src/tasks/placement_tasks.py:19–38`

```python
from redis import Redis as RedisSync          # line 19 — sync client import
from redis.asyncio import Redis               # line 20 — async client import

# Async Redis для дедупликации задач (D-10 fix)
redis_client = Redis.from_url(...)            # line 36 — defined, NEVER USED
# Sync Redis only for Celery task dedup (runs in sync context)
redis_sync_client = RedisSync.from_url(...)   # line 38 — used in _check_dedup()
```

**Usage of `redis_client` (async):** `grep -n 'redis_client' placement_tasks.py` returns **only line 36** (the definition). The async client is dead code.

**Usage of `redis_sync_client` (sync):**

```python
def _check_dedup(task_name: str, placement_id: int) -> bool:  # line 99
    ...
    if redis_sync_client.exists(task_key):   # line 113
        return True
    redis_sync_client.setex(task_key, ttl, task_key)  # line 116
    return False
```

`_check_dedup` is called from **5 sync Celery task wrappers**: `check_owner_response_sla`, `check_payment_sla`, `check_counter_offer_sla`, `publish_placement`, `check_scheduled_deletions` — but always from the **sync outer wrapper** (not from the `async _...` implementation).

Wait — `_check_dedup` IS called from inside `async _...` functions (lines 179, 282, 386, 501, etc.). That is: async code calling a sync Redis operation. This is the original D-10 issue — it was not fully resolved.

### Async Redis availability

`redis.asyncio` is used in **14+ locations** across the project:

| File | Usage |
|---|---|
| `src/api/dependencies.py` | `aioredis.Redis` pool (canonical FastAPI dependency) |
| `src/tasks/notification_tasks.py` | `Redis.from_url(...)` |
| `src/tasks/parser_tasks.py` | `AsyncRedis` (local import) |
| `src/utils/telegram/parser.py` | `Redis.from_url(...)` |
| `src/bot/middlewares/throttling.py` | `Redis` (aiogram FSM) |
| `src/bot/middlewares/fsm_timeout.py` | `Redis` (aiogram FSM) |
| `src/bot/handlers/shared/login_code.py` | `aioredis.from_url(...)` |
| `src/bot/handlers/shared/start.py` | `aioredis.from_url(...)` |
| `src/bot/handlers/advertiser/campaigns.py` | `aioredis.from_url(...)` |
| `src/api/routers/uploads.py` | `aioredis.from_url(...)` |
| `src/api/routers/channels.py` | `aioredis.from_url(...)` |

The module-level `redis_client = Redis.from_url(...)` on line 36 was intended as the D-10 fix but was never wired into `_check_dedup`.

### Proposed fix

Replace `_check_dedup` with an async version that uses `redis.asyncio`:

```python
async def _check_dedup_async(task_name: str, placement_id: int) -> bool:
    task_key = f"placement_task:{task_name}:{placement_id}"
    ttl = DEDUP_TTL.get(task_name, 3600)
    if await redis_client.exists(task_key):
        return True
    await redis_client.setex(task_key, ttl, task_key)
    return False
```

All call sites are already in `async` functions — replace `_check_dedup(...)` → `await _check_dedup_async(...)`.  
Delete `redis_sync_client` and `RedisSync` import.  
The existing `redis_client` (line 36) becomes the sole Redis client for this module.

### Verdict

| Attribute | Value |
|---|---|
| **status** | ⚠️ D-10 NOT fully fixed — async client declared but unused |
| **actual_problem** | Sync Redis calls inside `async` task implementations — blocks event loop |
| **fix_complexity** | Low — `_check_dedup` → `_check_dedup_async` + `await` at 8 call sites |
| **risk** | Low — idempotency logic unchanged, only I/O model changes |

---

## D-20: Empty Directories

**Command:** `find . -type d -empty -not -path './.git/*' -not -path '*/node_modules/*' -not -path '*/venv/*' -not -path '*/__pycache__/*' -not -path '*/.venv/*'`

**Result:**

```
./reports/monitoring/payloads
```

Only **1 empty directory** found in the entire codebase.

| Directory | Status | Action |
|---|---|---|
| `reports/monitoring/payloads` | Empty, no `.gitkeep` | Safe to delete OR add `.gitkeep` if directory structure is intentional. Siblings are `dir_snapshot/` and `error_reports/` which likely hold runtime output. Since this is a `reports/` directory (not source code), and Celery/monitoring tasks may write payload files here at runtime, adding `.gitkeep` is safer than deleting the directory. |

**Note:** No empty directories in `src/`, `mini_app/src/`, or `web_portal/src/`. Source tree is clean.

---

## PlaceholderScreen: `/settings` Route Status

### Current state

**File:** `web_portal/src/App.tsx:81–89, 207`

```tsx
// App.tsx:81
function PlaceholderScreen({ title }: { title: string }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
      <div className="text-6xl mb-4">🚧</div>
      <h2 className="text-2xl font-display font-bold text-text-primary mb-2">{title}</h2>
      <p className="text-text-secondary">Этот экран будет добавлен в следующей итерации.</p>
    </div>
  )
}

// App.tsx:207
{ path: 'settings', element: <PlaceholderScreen title="Настройки" /> },
```

`PlaceholderScreen` is an inline component, not a lazy-loaded import. It's used **only once** in the router: `/settings`.

### Existing Settings-related screens

| Screen | Path | Scope |
|---|---|---|
| `AdminPlatformSettings.tsx` | `web_portal/src/screens/admin/` | Admin-only platform config |
| `OwnChannelSettings.tsx` | `web_portal/src/screens/owner/` | Channel-specific settings (owner) |

Neither is a general **user account settings** screen. No `UserSettings.tsx` or `Settings.tsx` file exists in `web_portal/src/screens/`.

### What `/settings` should contain

Based on the existing user flow, a `/settings` screen would logically house:

- Notification preferences
- Language / timezone
- Account deletion
- Security (change linked Telegram, 2FA)
- Privacy settings

### Verdict

| Attribute | Value |
|---|---|
| **status** | ⚠️ Placeholder — no implementation planned/started |
| **safe_to_leave** | ✅ YES — renders a visible "under construction" screen, no runtime errors |
| **replacement_trigger** | When user account settings scope is defined in a sprint |
| **cleanup** | When a real `Settings.tsx` screen is added, remove `PlaceholderScreen` component from `App.tsx` (it's only used once — can be deleted inline) |

---

## Stubs: FNS Validation and ORD Provider

### FNS Validation Service (`fns_validation_service.py`)

**File:** `src/core/services/fns_validation_service.py`

Two functions return a hardcoded `status="format_validated"` with a `# TODO: check via FNS API` comment:

| Line | Function | TODO |
|---|---|---|
| 174 | `validate_legal_entity()` | `status="format_validated",  # TODO: check via FNS API` |
| 218 | `validate_individual_entrepreneur()` | `status="format_validated",  # TODO: check via FNS API` |

**Current behaviour:** Validates INN/OGRN/OGRNIP checksum only (algorithm-based). Does not call `npchk.nalog.ru` or any FNS API. Returns `is_valid=True` for any correctly-formatted number regardless of whether the entity actually exists.

**Risk of current state:** Low pre-production (checksum validation catches typos). Higher post-production — adversarial users could submit valid-checksum but nonexistent INNs.

**Trigger for replacement:**
- When real FNS API access (`npchk.nalog.ru` or equivalent) is obtained
- When legal compliance sprint requires actual entity verification
- When first commercial contract must be validated against the registry

**Integration point:** Both functions return `FNSValidationResult`. The `status` field is the integration hook — replace `"format_validated"` with `"active"` / `"liquidated"` etc. from the real API response.

---

### StubOrdProvider (`stub_ord_provider.py`)

**File:** `src/core/services/stub_ord_provider.py`

All 5 methods return synthetic values and log `logger.warning("ORD stub: реальный провайдер не настроен ...")`:

| Method | Stub return |
|---|---|
| `register_advertiser` | `"STUB-ADV-{user_id}"` |
| `register_platform` | `"STUB-PLATFORM-{channel_id}"` |
| `register_contract` | `"STUB-CONTRACT-{placement_request_id}"` |
| `register_creative` | `"STUB-ERID-{placement_request_id}-{timestamp}"` |
| `report_publication` | `True` |
| `get_status` | `"stub"` |

**Current activation condition:** Default when `ORD_PROVIDER` env var is not set. Setting `ORD_PROVIDER=yandex|vk|ozon` + `ORD_API_KEY` + `ORD_API_URL` activates a real provider.

**Blocking behaviour:** `ORD_BLOCK_WITHOUT_ERID=true` would block publication for placements without a real ERID. Currently defaults to `false` — publications proceed with synthetic ERIDs.

**Risk of current state:** Legal exposure under ФЗ-38 if `ORD_BLOCK_WITHOUT_ERID=false` is used in production. The `publish_placement` task (placement_tasks.py:505–566) checks ERID validity but accepts `"registered"` / `"token_received"` status — which the stub can produce.

**Trigger for replacement:**
- Before any paid placement reaches `published` status in production
- Required: ORD provider contract (Яндекс/VK/Ozon) + API credentials
- After replacement: set `ORD_BLOCK_WITHOUT_ERID=true` in production `.env`

---

## Summary Table

| Item | Safe to remove? | Effort | Priority |
|---|---|---|---|
| D-06: `check_pending_invoices` | ✅ YES — no callers, no Beat | XS (delete 9 lines) | Low |
| D-07: `/billing/invoice/{id}` | ✅ YES — stale docstring only | XS (delete 1 docstring line) | Low |
| D-10: Sync Redis in `_check_dedup` | ⚠️ Needs fix, not removal | S (~15 lines, 8 call sites) | Medium |
| D-20: `reports/monitoring/payloads` | ✅ Yes / add `.gitkeep` | XS | Low |
| PlaceholderScreen `/settings` | Leave until implemented | M (new screen) | Low |
| FNS stub | Leave — checksum is sufficient pre-prod | L (FNS API integration) | Post-launch |
| ORD stub | Leave — but set `ORD_BLOCK_WITHOUT_ERID=true` before prod | L (ORD contract) | Pre-launch blocker |

---

🔍 Verified against: 117b203 | 📅 Updated: 2026-04-17T00:00:00Z
