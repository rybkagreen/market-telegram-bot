# Python 3.14 Upgrade Report

**Date:** 2026-04-10  
**Sprint:** S-29 — Python 3.14 Runtime Upgrade  
**Status:** ✅ COMPLETE — Ready for staging deployment

---

## ✅ Upgrade Execution Summary

| Metric | Before (v4.4) | After (v4.5) |
|--------|---------------|--------------|
| **Runtime** | Python 3.13.7 | **Python 3.14.4** |
| **Container base** | `python:3.13-slim` | **`python:3.14-slim`** |
| **aiogram** | ^3.15.0 (pinned 3.15.x) | **3.27.0** (Python 3.14 support) |
| **pydantic** | ^2.10.5 | **>=2.12,<2.13** (2.12.5) |
| **pydantic-core** | 2.33.2 | **2.41.5** (Python 3.14 wheels) |
| **asyncpg** | ^0.30.0 | **^0.31.0** (0.31.0) |
| **pillow-heif** | ^0.20.0 | **^1.0.0** (1.3.0, prebuilt wheels) |
| **ruff** | ^0.9.3 | **^0.12.0** |
| **mypy** | ^1.14.1 | **^1.17.0** |
| **pytest-asyncio** | ^0.25.2 | **^0.26.0** |

---

## 📦 Dependency Changes (poetry.lock diff summary)

### Upgraded (core runtime)
| Package | Old | New | Reason |
|---------|-----|-----|--------|
| `aiogram` | 3.15.x | 3.27.0 | Python 3.14 + pydantic 2.12 support |
| `pydantic` | 2.10.5 | 2.12.5 | Python 3.14 compatibility |
| `pydantic-core` | 2.33.2 | 2.41.5 | Python 3.14 PyO3 support |
| `asyncpg` | 0.30.0 | 0.31.0 | Python 3.14 wheel available |
| `pillow-heif` | 0.20.0 | 1.3.0 | Python 3.14 prebuilt wheel |
| `celery` | 5.4.x | 5.6.2 | Resolved via lock |
| `sqlalchemy` | 2.0.37 | 2.0.46 | Resolved via lock |
| `fastapi` | 0.115.8 | 0.115.14 | Resolved via lock |

### Upgraded (dev tools)
| Package | Old | New |
|---------|-----|-----|
| `ruff` | 0.9.3 | 0.12.0+ |
| `mypy` | 1.14.1 | 1.17.0+ |
| `pytest-asyncio` | 0.25.2 | 0.26.0+ |

### Unchanged (verified compatible)
- `mistralai` 1.12.4 ✅
- `yookassa` 3.2.0 ✅
- `telethon` 1.36.0 ✅
- `slowapi` 0.1.9 ✅
- `sentry-sdk` 2.55.0 ✅

---

## 🔧 Configuration Updates

### `pyproject.toml`
```diff
-python = "^3.13"
+python = ">=3.14,<3.15"

-aiogram = "^3.15.0"
+aiogram = "3.27.0"

-pydantic = "^2.10.5"
-pydantic-settings = "^2.7.1"
+pydantic = ">=2.12,<2.13"
+pydantic-settings = ">=2.10,<2.13"

-asyncpg = "^0.30.0"
+asyncpg = "^0.31.0"

-pillow-heif = "^0.20.0"
+pillow-heif = "^1.0.0"

-ruff = "^0.9.3"
-mypy = "^1.14.1"
-pytest-asyncio = "^0.25.2"
+ruff = "^0.12.0"
+mypy = "^1.17.0"
+pytest-asyncio = "^0.26.0"

-target-version = "py313"
+target-version = "py314"
+preview = true

-python_version = "3.13"
+python_version = "3.14"
```

### Dockerfiles (all 3: bot, api, worker)
```diff
-FROM python:3.13-slim as builder
+FROM python:3.14-slim as builder

+ADD build dependencies: gcc, python3-dev, libpq-dev, pkg-config
+(required for asyncpg, cryptography, PyMuPDF C-extension compilation)

-COPY --from=builder /usr/local/lib/python3.13/site-packages
+COPY --from=builder /usr/local/lib/python3.14/site-packages
```

---

## 🐛 Python 3.14 Compatibility Fixes Applied

### 1. `asyncio.DefaultEventLoopPolicy` removed (Python 3.14)
**File:** `src/tasks/parser_tasks.py:1329-1332`

```python
# BEFORE:
asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())

# AFTER:
# Removed — default on Linux is already UnixSelectorEventLoopPolicy
```

**Rationale:** `asyncio.DefaultEventLoopPolicy` was removed in Python 3.14. The Linux default is already `_UnixDefaultEventLoopPolicy`, making this call redundant.

### 2. Forward reference quotes no longer needed (PEP 563 / Python 3.14)
**Files:** 97 occurrences across 40+ files

```python
# BEFORE:
async def handler(service: "PlacementRequestService") -> "PlacementResponse":

# AFTER (auto-fixed by ruff UP037):
async def handler(service: PlacementRequestService) -> PlacementResponse:
```

**Rationale:** Python 3.14 makes forward references automatic — string quotes around type annotations are no longer needed.

### 3. `callback.message` null-safety (mypy strict mode)
**File:** `src/bot/handlers/admin/monitoring.py`

```python
# BEFORE:
issue_id = callback.data.split(":")[2]  # mypy: data could be None

# AFTER:
assert callback.data is not None  # guaranteed by callback router lambda
issue_id = callback.data.split(":")[2]
```

**Rationale:** mypy 1.17 correctly narrows types. The lambda guard `lambda c: c.data and ...` is a runtime filter — mypy doesn't understand lambda guards, so explicit `assert` is required.

### 4. `callback.message` edit_text safety
**File:** `src/bot/handlers/admin/monitoring.py:28-38, 86-92`

```python
# BEFORE:
await callback.message.edit_text(...)  # could be None or InaccessibleMessage

# AFTER:
msg = callback.message
if msg and hasattr(msg, "edit_text"):
    await msg.edit_text(...)
```

**Rationale:** `callback.message` can be `None` (deleted callback) or `InaccessibleMessage` (bot can't access). Added proper guards.

### 5. `FNSValidationError` → dataclass
**File:** `src/core/services/fns_validation_service.py:18-23`

```python
# BEFORE:
class FNSValidationError:
    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message

# AFTER:
@dataclass(frozen=True)
class FNSValidationError:
    field: str
    message: string
```

**Rationale:** ruff preview mode B903 — class could be a dataclass. Frozen dataclass ensures immutability, aligns with AAA standards.

### 6. Dockerfiles: C-extension build dependencies
**Files:** `docker/Dockerfile.bot`, `docker/Dockerfile.api`, `docker/Dockerfile.worker`

Added to builder stage:
```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libpq-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*
```

**Rationale:** asyncpg 0.31, cryptography, and PyMuPDF require compilation on Python 3.14. Python 3.14-slim doesn't include build tools by default.

---

## 🧪 Verification Results

| Tool | Command | Result |
|------|---------|--------|
| **Ruff** | `ruff check src/` | ✅ **0 errors** |
| **Ruff Format** | `ruff format --check src/` | ✅ **263 files formatted** |
| **mypy** | `mypy src/ --python-version 3.14` | ✅ **0 errors, 263 files** |
| **Bandit** | `bandit -r src/ -ll -q` | ✅ **0 High, 1 Medium (pre-existing B108)** |
| **Docker bot** | `docker build -f Dockerfile.bot` | ✅ **Built successfully** |
| **Docker api** | `docker build -f Dockerfile.api` | ✅ **Built successfully** |
| **Docker worker** | `docker build -f Dockerfile.worker` | ✅ **Built successfully** |
| **Runtime verify** | `python -c "import ..."` in container | ✅ **Python 3.14.4 confirmed** |

### Test Suite
- **Pre-existing failures confirmed** (NOT Python 3.14-related):
  - `test_main_menu.py` — imports non-existent `role_select_kb`
  - `test_review_service.py` — uses `current_role` field that doesn't exist in User model
  - `test_escrow_payouts.py` — same `current_role` issue + sqlite migration gap
  - `test_fsm_middlewares.py` — references removed FSM states and missing modules
  - `test_ai_service.py` — module import path issues
  - `test_content_filter.py` — async/await mismatch in test code
  - `test_gamification.py` — missing `classify_subcategory` function, DB connection issues
  - `test_counter_offer_flow.py` — requires PostgreSQL testcontainers
- **Passing tests:** 192+ tests pass — no regressions introduced by the upgrade

---

## ⚠️ Rollback Instructions

If issues arise after deployment:

```bash
# 1. Revert git changes
cd /opt/market-telegram-bot
git reset --hard HEAD~1  # or git checkout <commit-before-upgrade>

# 2. Restore old poetry.lock
git checkout HEAD~1 -- poetry.lock

# 3. Restore old venv
rm -rf .venv
poetry env use python3.13
poetry install

# 4. Rebuild Docker images
docker compose build --no-cache nginx && docker compose up -d nginx
docker compose up -d --build api worker_critical worker_background worker_game bot
```

**Key files modified:**
- `pyproject.toml` (python version, 8 dependency changes)
- `poetry.lock` (regenerated for Python 3.14)
- `docker/Dockerfile.bot`, `docker/Dockerfile.api`, `docker/Dockerfile.worker` (base image + build deps)
- `src/tasks/parser_tasks.py` (removed deprecated asyncio call)
- `src/bot/handlers/admin/monitoring.py` (null-safety guards)
- `src/core/services/fns_validation_service.py` (dataclass conversion)
- 40+ files (UP037 forward reference cleanup)

---

## 🚀 Next Steps

### Immediate (pre-production)
1. **Deploy to staging:** `docker compose up -d --build bot api worker_critical worker_background worker_game`
2. **Run smoke tests:** Verify bot startup, webhook registration, YooKassa integration
3. **Monitor Celery workers:** Check task execution in Flower dashboard
4. **Verify OCR pipeline:** Test document upload → PDF generation → ORC processing

### Deferred (future sprint)
1. **Fix pre-existing test failures:** `current_role` field, missing imports, FSM state mismatches (~93 tests)
2. **Bandit B108:** Replace hardcoded `/tmp` with `tempfile.mkdtemp()` in `webhooks.py:28`
3. **Python 3.15 preparation:** aiogram 3.27 caps at `<3.15` — monitor for aiogram 3.28+ release
4. **Remove `preview = true` from ruff config** once Python 3.14 support is stable (ruff 0.13+)

---

🔍 Verified against: commit `prep/upgrade-v314` | 📅 Updated: 2026-04-10T12:00:00Z
