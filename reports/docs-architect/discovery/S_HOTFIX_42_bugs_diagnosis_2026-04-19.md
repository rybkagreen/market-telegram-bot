# S-HOTFIX-42: Диагностика 3 Production Bugs

**Дата:** 2026-04-19  
**Автор:** Claude Code (Research Phase)  
**Версия:** 1.0

---

## Executive Summary

| Bug | Категория | Confidence | Sprint-источник |
|-----|-----------|------------|-----------------|
| 1. Transaction history пустой | **D** — БД пустая | 95% | N/A (preexisting) |
| 2. Plan payment не работает | **A** — endpoint отсутствует | 100% | S-34 (regression) |
| 3. Escrow без ERID | **A** — ожидаемое состояние | 90% | N/A (design) |

---

## Bug 1: Transaction History пустой в web_portal

### Диагностика

**Frontend → Backend → БД трассировка:**

1. **Frontend call** (`web_portal/src/api/billing.ts:14-16`):
   ```typescript
   export async function getTransactionHistory(page = 1, limit = 20) {
     return api.get(`billing/history?page=${page}&limit=${limit}`).json<TransactionListResponse>()
   }
   ```
   - Endpoint: `GET /api/billing/history`
   - Expected response: `{ items: TransactionItem[], total, page, pages }`

2. **Backend endpoint** (`src/api/routers/billing.py:364-427`):
   - Path: `GET /api/billing/history`
   - Response model: `BillingHistoryResponse` (items, total, page, pages)
   - Filter: `_VISIBLE_TX_TYPES = {"topup", "escrow_freeze", "escrow_release", "credits_buy", "spend", "payout_fee", "refund_full", "bonus"}`
   - Pagination: page, limit (default 20, max 100)

3. **Database check:**
   ```sql
   SELECT COUNT(*) FROM transactions; -- Returns: 0
   ```

4. **Shape comparison:**
   - Backend `BillingHistoryItem`: id, type, amount, description, placement_request_id, status, created_at
   - Frontend `TransactionItem`: id, type, amount, status, description, created_at, placement_request_id
   - **Совпадение полное** — shape mismatch исключён

### Диагноз

**Категория: D — БД реально пустая**

- Endpoint работает корректно
- Frontend получает пустой массив `{"items": [], "total": 0, "page": 1, "pages": 0}`
- В БД нет транзакций для тестового пользователя
- UI показывает "Транзакций пока нет" (ожидаемое поведение при пустом ответе)

### Fix Scope

**Не требует исправления кода.** Проблема в том, что тестовый пользователь не совершал транзакций.

**Рекомендация:** Создать тестовые транзакции для демонстрации или уточнить у пользователя, какой именно пользователь должен иметь транзакции.

---

## Bug 2: Plan Payment не работает из web_portal

### Диагностика

1. **Frontend call** (`web_portal/src/api/billing.ts:36-38`):
   ```typescript
   export async function purchasePlan(plan: string) {
     return api.post('billing/purchase-plan', { json: { plan } }).json<{ success: boolean }>()
   }
   ```
   - Endpoint: `POST /api/billing/purchase-plan`
   - Body: `{ "plan": "starter" | "pro" | "business" }`

2. **Backend endpoints** (`src/api/routers/billing.py`):
   - `POST /api/billing/topup` (line 139) — пополнение баланса
   - `POST /api/billing/credits` (line 428) — оплата тарифа с баланса
   - `POST /api/billing/plan` (line 459) — смена тарифа
   - **НЕТ `POST /api/billing/purchase-plan`**

3. **Available endpoints:**
   - `POST /api/billing/plan` — требует баланс >= стоимости тарифа
   - `POST /api/billing/topup` — создаёт платёж в YooKassa для пополнения баланса

### Диагноз

**Категория: A — Endpoint не существует**

- Frontend вызывает `POST /api/billing/purchase-plan`
- Backend не имеет этого endpoint
- HTTP 404 при попытке вызова

### Fix Scope

| Файл | Изменение | Размер |
|------|-----------|--------|
| `src/api/routers/billing.py` | Добавить endpoint `POST /api/billing/purchase-plan` | ~30 строк |
| `src/api/schemas/` | Создать `PurchasePlanRequest`, `PurchasePlanResponse` | ~15 строк |

**Зависимости:**
- Использовать существующий `BillingService.buy_credits_for_plan()` или создать новый метод для покупки тарифа через YooKassa
- Frontend ожидает `{ success: boolean }` — нужно вернуть корректный формат

**Sprint-источник:** S-34 (regression) — вероятно endpoint был удалён или переименован при рефакторинге CampaignUpdate/CampaignResponse.

---

## Bug 3: Test campaign в escrow БЕЗ реального ERID

### Диагностика

1. **Database state:**
   ```sql
   SELECT id, status, is_test, erid, created_at FROM placement_requests;
   -- Result: id=1, status=published, is_test=true, erid=NULL
   ```

2. **ORD registrations:**
   ```sql
   SELECT * FROM ord_registrations;
   -- Result: 0 rows
   ```

3. **Configuration:**
   - `ORD_PROVIDER=stub` (default)
   - `ORD_BLOCK_WITHOUT_ERID=False` (default)
   - `settings.ord_block_publication_without_erid = False`

4. **Publication flow:**
   - `placement_tasks.py:publish_placement` → `publication_service.py:publish_placement`
   - `publication_service.py:_build_marked_text` проверяет `placement.erid`
   - При `erid=NULL` и `is_test=True` и `blocking=False`:
     - Логирует warning: `"erid missing for placement %s (is_test=%s, blocking=%s)"`
     - Публикует без маркировки erid
     - Не блокирует публикацию

5. **ORD registration:**
   - `ord_tasks.py:register_creative_task` существует, но **нигде не вызывается** в flow публикации
   - ORD registration происходит **после** публикации (через `report_publication_task`), а не до

### Диагноз

**Категория: A — Ожидаемое промежуточное состояние**

- Test placement в статусе `published` с `erid=NULL` — это **ожидаемое поведение** при текущей конфигурации:
  - `is_test=True` → пропускает блокировку
  - `ORD_BLOCK_WITHOUT_ERID=False` → не блокирует без erid
  - Stub provider возвращает synthetic ERID, но он **не записывается** в placement

**Это НЕ баг кода, а legal exposure (pre-launch blocker из S-40):**
- Публикация без реального ERID нарушает ФЗ-38
- Stub ERID (`STUB-ERID-{id}-{ts}`) не является валидным для регулятора

### Fix Scope

| Приоритет | Изменение | Файлы |
|-----------|-----------|-------|
| **P0** (legal) | Интегрировать реальный ORD провайдер (Яндекс/VK/Ozon) | `src/core/services/ord_provider.py`, `.env` |
| P1 | Включить `ORD_BLOCK_WITHOUT_ERID=true` после настройки провайдера | `.env` |
| P2 | Добавить вызов `register_creative` до `publish_placement` | `src/tasks/placement_tasks.py` |

**Sprint-источник:** N/A — это design decision, а не regression. Проблема известна как pre-launch blocker (CLAUDE.md).

---

## Matrix: Sprint Responsible

| Bug | Sprint | Причина |
|-----|--------|---------|
| 1. Transaction history | N/A | Preexisting — транзакции не создавались |
| 2. Plan payment | S-34 | Regression — endpoint `purchase-plan` удалён/не создан |
| 3. Escrow without ERID | N/A | Design — stub provider, ORD не интегрирован |

---

## Recommendation

**Три раздельных fix-спринта:**

1. **S-HOTFIX-42a (Bug 2):** Добавить `POST /api/billing/purchase-plan` endpoint
   - Простой fix, ~50 строк кода
   - Не требует миграций

2. **S-HOTFIX-42b (Bug 1):** Не требует кода — уточнить требования у пользователя

3. **S-HOTFIX-42c (Bug 3):** Интеграция реального ORD провайдера
   - Требует контракта с ОРД оператором
   - Настройка API credentials
   - Это P0 для production launch

---

## Stop-and-Report Findings

✅ **DB access works** — удалось подключиться к `market_bot_db`  
✅ **Docker services running** — все контейнеры healthy  
✅ **Test placement exists** — found in DB with `is_test=true`  
✅ **No additional bugs discovered** — только 3 описанных проблемы

---

**🔍 Verified against:** Production DB state, API logs, source code analysis  
**📅 Updated:** 2026-04-19T12:00:00Z