# P18 Analysis Report — MyPy Deep Dive

**Date:** 2026-03-14  
**Status:** ✅ COMPLETED  
**Purpose:** Collect exact code fragments for surgical fix prompt preparation

---

## Executive Summary

| Metric | Value |
|--------|-------|
| **Total MyPy errors** | 163 |
| **Errors in target 4 files** | 21 |
| **Type:ignore added by P17** | 7 (all invalid syntax) |
| **Critical runtime risks** | 9 |

### Errors by File (Target Files Only)

| File | Errors |
|------|--------|
| `publication_service.py` | 6 |
| `placement_request_service.py` | 15 |
| `payout_service.py` | 0 ✅ |
| `publication_tasks.py` | 0 ✅ |

### Errors by Code Type

| Code | Count | Description |
|------|-------|-------------|
| `[union-attr]` | 70 | Accessing attributes on union types without type guard |
| `[arg-type]` | 52 | Incompatible argument types |
| `[attr-defined]` | 23 | Attribute doesn't exist on type |
| `[return-value]` | 7 | Return type mismatch |
| `[syntax]` | 6 | Invalid type: ignore syntax |

---

## Critical Problems (Target Files)

### publication_service.py (6 errors)

#### Problem 1: ChatMemberOwner Type Guard (Lines 67-69)

**Error:**
```
[union-attr] Item "ChatMemberOwner" of "ChatMemberOwner | ChatMemberAdministrator" 
has no attribute "can_post_messages"
```

**Code Context:**
```python
if isinstance(member, ChatMemberAdministrator | ChatMemberOwner):
    can_post = bool(member.can_post_messages)
    can_delete = bool(member.can_delete_messages)
    can_pin = bool(member.can_pin_messages) if require_pin else True
```

**Risk:** CRITICAL — AttributeError in production when bot checks permissions for channel owner

**Fix Hint:** `ChatMemberOwner` doesn't have `can_post_messages`, `can_delete_messages`, `can_pin_messages` attributes. Need separate handling:
- `ChatMemberAdministrator` — check attributes
- `ChatMemberOwner` — owner always has all permissions, no check needed

---

#### Problem 2: telegram_id Optional Not Guarded (Lines 199, 205)

**Error:**
```
[arg-type] Argument "chat_id" to "unpin_chat_message" of "Bot" has incompatible type "int | None"
```

**Code Context:**
```python
await bot.unpin_chat_message(
    chat_id=channel.telegram_id,  # telegram_id is Optional[int]
    message_id=placement.message_id,
)

await bot.delete_message(channel.telegram_id, placement.message_id)
```

**Risk:** CRITICAL — TypeError if `channel.telegram_id` is None

**Fix Hint:** Add guard before using:
```python
if channel.telegram_id is None:
    raise ValueError(f"Channel {channel.id} has no telegram_id")
```

---

#### Problem 3: PlacementStatus.COMPLETED Doesn't Exist (Line 211)

**Error:**
```
[attr-defined] "type[PlacementStatus]" has no attribute "COMPLETED"
```

**Code Context:**
```python
placement.status = PlacementStatus.COMPLETED
```

**Risk:** CRITICAL — AttributeError in production

**Fix Hint:** Check `PlacementStatus` enum for correct status value (likely `PUBLISHED` or different name)

---

### placement_request_service.py (15 errors)

#### Problem 4: Invalid type: ignore Syntax (Lines 280, 350, 412, 455, 549, 605)

**Error:**
```
[syntax] Invalid "type: ignore" comment
```

**Code Context (Line 280):**
```python
await _notify_owner_accept  # type: ignore[no-untyped-call](result, advertiser, channel)
```

**Risk:** MEDIUM — MyPy can't parse the ignore comment, errors not suppressed

**Fix Hint:** `type: ignore` must be at END of line, not before function arguments:
```python
# WRONG:
await _notify_owner_accept  # type: ignore[no-untyped-call](result, advertiser, channel)

# CORRECT:
await _notify_owner_accept(result, advertiser, channel)  # type: ignore[no-untyped-call]
```

---

#### Problem 5: _notify_* Functions Lack Type Annotations

**Code Context:**
```python
async def _notify_create_request(placement, advertiser, owner, channel):
    """Отправить уведомление о новой заявке."""
    # ... no type annotations ...

async def _notify_owner_accept(placement, advertiser, channel):
    """Отправить уведомление о принятии заявки владельцем."""
    # ... no type annotations ...
```

**Risk:** MEDIUM — All calls to these functions get `[no-untyped-call]` errors

**Fix Options:**
1. Add proper type annotations to all 7 `_notify_*` functions
2. Add module-level `# type: ignore` at top of file
3. Add `# type: ignore[no-untyped-call]` to each call site (with correct syntax)

---

#### Problem 6: return-value Errors (Lines 352, 457, 551, 607, 649, 691, 726)

**Error:**
```
[return-value] Incompatible return value type (got "PlacementRequest | None", expected "PlacementRequest")
```

**Code Context (Line 352):**
```python
advertiser = await self.session.get(User, placement.advertiser_id)
if advertiser and result:
    await _notify_rejected(...)

return result  # result might be None
```

**Risk:** MEDIUM — Function signature says returns `PlacementRequest` but might return `None`

**Fix Hint:** Add None guard:
```python
if result is None:
    raise ValueError(f"PlacementRequest {placement_id} not found")
return result
```

---

## type:ignore Added by P17 (All Invalid)

| File | Line | Code | Issue |
|------|------|------|-------|
| placement_request_service.py | 220 | `await _notify_create_request(...)  # type: ignore[no-untyped-call]` | ✅ Correct syntax |
| placement_request_service.py | 280 | `await _notify_owner_accept  # type: ignore...(args)` | ❌ type: ignore before args |
| placement_request_service.py | 350 | `await _notify_rejected  # type: ignore...(args)` | ❌ type: ignore before args |
| placement_request_service.py | 412 | `await _notify_counter_offer  # type: ignore...(args)` | ❌ type: ignore before args |
| placement_request_service.py | 455 | `await _notify_counter_accepted  # type: ignore...(args)` | ❌ type: ignore before args |
| placement_request_service.py | 549 | `await _notify_cancelled  # type: ignore...(args)` | ❌ type: ignore before args |
| placement_request_service.py | 605 | `await _notify_payment_received  # type: ignore...(args)` | ❌ type: ignore before args |

**Summary:** 6 of 7 type: ignore comments have invalid syntax — placed before function arguments instead of at end of line.

---

## _notify_* Function Signatures

| Function | Signature | Args | Return |
|----------|-----------|------|--------|
| `_notify_create_request` | `async def _notify_create_request(placement, advertiser, owner, channel):` | 4 | None (not annotated) |
| `_notify_owner_accept` | `async def _notify_owner_accept(placement, advertiser, channel):` | 3 | None (not annotated) |
| `_notify_counter_offer` | `async def _notify_counter_offer(placement, advertiser, channel):` | 3 | None (not annotated) |
| `_notify_counter_accepted` | `async def _notify_counter_accepted(placement, advertiser, owner, channel):` | 4 | None (not annotated) |
| `_notify_payment_received` | `async def _notify_payment_received(placement, advertiser, owner, channel):` | 4 | None (not annotated) |
| `_notify_rejected` | `async def _notify_rejected(placement, advertiser, channel):` | 3 | None (not annotated) |
| `_notify_cancelled` | `async def _notify_cancelled(placement, advertiser, owner, channel, reputation_delta=0.0):` | 5 | None (not annotated) |

**Issue:** None of these functions have type annotations — all parameters and return types are untyped.

---

## ChatMember Usage Analysis

### File: `src/core/services/publication_service.py`

**Function:** `check_bot_permissions()`

**Current Code:**
```python
member = await bot.get_chat_member(chat_id, bot.id)

if isinstance(member, ChatMemberAdministrator | ChatMemberOwner):
    can_post = bool(member.can_post_messages)
    can_delete = bool(member.can_delete_messages)
    can_pin = bool(member.can_pin_messages) if require_pin else True
```

**Issue:** `ChatMemberOwner` doesn't have `can_post_messages`, `can_delete_messages`, `can_pin_messages` attributes. These attributes only exist on `ChatMemberAdministrator`.

**Correct Approach:**
```python
if isinstance(member, ChatMemberOwner):
    # Owner always has all permissions
    can_post = True
    can_delete = True
    can_pin = True
elif isinstance(member, ChatMemberAdministrator):
    can_post = bool(member.can_post_messages)
    can_delete = bool(member.can_delete_messages)
    can_pin = bool(member.can_pin_messages) if require_pin else True
else:
    raise InsufficientPermissionsError(...)
```

---

## Current Imports

### publication_service.py
```python
import logging
from contextlib import suppress
from datetime import UTC, datetime, timedelta

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import ChatMemberAdministrator, ChatMemberOwner
from sqlalchemy.ext.asyncio import AsyncSession

from src.constants.payments import FORMAT_DURATIONS_SECONDS
from src.core.exceptions import BotNotAdminError, InsufficientPermissionsError, PostDeletionError
from src.core.services.billing_service import BillingService
from src.db.models.placement_request import PlacementRequest, PlacementStatus
from src.db.repositories.placement_request_repo import PlacementRequestRepo
```

### placement_request_service.py
```python
import logging
import re
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.analytics import TelegramChat
from src.db.models.placement_request import PlacementRequest, PlacementStatus
from src.db.models.user import User
from src.db.repositories.channel_settings_repo import ChannelSettingsRepo
from src.db.repositories.placement_request_repo import PlacementRequestRepo
from src.db.repositories.reputation_repo import ReputationRepo

if TYPE_CHECKING:
    from src.core.services.billing_service import BillingService

logger = logging.getLogger(__name__)
```

---

## Critical Fixes Needed (Priority Order)

### Priority 1: Runtime Errors (Will Crash in Production)

1. **publication_service.py:67-69** — ChatMemberOwner type guard incorrect
2. **publication_service.py:199,205** — telegram_id Optional not guarded
3. **publication_service.py:211** — PlacementStatus.COMPLETED doesn't exist

### Priority 2: MyPy Syntax Errors (Prevent Type Checking)

4. **placement_request_service.py:280,350,412,455,549,605** — Invalid type: ignore syntax
5. **placement_request_service.py** — _notify_* functions need type annotations
6. **placement_request_service.py:352,457,551,607,649,691,726** — return-value errors

---

## Notes

- Most errors (142 of 163) are in files OUTSIDE the 4 target files
- `payout_service.py` and `publication_tasks.py` are clean (0 errors)
- The 6 errors in `publication_service.py` are all CRITICAL runtime risks
- The 15 errors in `placement_request_service.py` are mostly syntax errors from P17's type: ignore attempts
- 6 of 7 type: ignore comments added by P17 have invalid syntax

---

**This report is ready for use in preparing a surgical fix prompt.**
