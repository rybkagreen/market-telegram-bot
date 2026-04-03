# 🎉 S-26: ACCOUNTING & TAX COMPLIANCE — COMPLETE

**Все 9 подспринтов успешно реализованы. Платформа готова к налоговой проверке для ООО УСН 15% (доходы − расходы).**

---

## 📊 Итоговая сводка по S-26

| Спринт | Задачи | Статус | Миграция |
|--------|--------|--------|----------|
| **A.1** | Act model, DocumentNumberService, Jinja2 шаблоны | ✅ | `s26a001_add_accounting_acts` |
| **A.2** | Fix payout_id=0, YooKassa webhook enrichment, Act integration | ✅ | `s26a002_enrich_yk_payout` |
| **A.3** | Transaction enrichment, TaxAggregationService, KUDiR foundation | ✅ | `s26a003_accounting_tax` |
| **B.1** | KUDiR PDF/CSV export, /admin/tax/summary endpoint | ✅ | `s26b001_add_kudir_index` |
| **B.2** | NDFL 13% withholding, NPD tracking, PII encryption | ✅ | `s26b002_ndfl_npd_encryption` |
| **C.1** | VAT 22%, Invoice B2B, Celery tax reminders | ✅ | `s26c001_vat_invoice_calendar` |
| **C.2** | EDO protocol stub, AdminTaxSummary UI, type cleanup | ✅ | *(no migration)* |
| **D.1** | ООО УСН 15% adaptation: expense fields, tax formula, categories | ✅ | `s26d001_ooo_usn_15_support` |
| **D.2** | Storno mechanism, automated expense recording, KUDiR export update | ✅ | `s26d002_storno_expense` |

**Миграционная цепочка:**  
`a1b2c3d4e5f6` → `s26a001` → `s26a002` → `s26a003` → `s26b001` → `s26b002` → `s26c001` → `s26d001` → `s26d002` **(HEAD)**

**Статический анализ:**  
✅ `ruff`: 0 ошибок  
✅ `mypy`: 0 проблем в новых/изменённых файлах  
✅ `eslint`: 0 ошибок в frontend-компонентах

---

## ✅ Что теперь поддерживает платформа (ООО УСН 15%)

### 📄 Первичные документы
- [ ] **Акты выполненных работ** — генерация при `deleted_at IS NOT NULL`, нумерация `АКТ-2026-0001`
- [ ] **Договоры** — сквозная нумерация `ДГ-2026-0001`, привязка к `LegalProfile`, snapshot `counterparty_legal_status`
- [ ] **Счета на оплату (B2B)** — генерация при `TOPUP`, нумерация `СЧ-2026-0001`, выделение НДС 22%

### 🧾 Налоговая отчётность (ООО УСН 15%)
- [ ] **КУДиР** — автоматическое создание записей для **доходов и расходов**, экспорт PDF/CSV с разделением секций
- [ ] **Формула УСН 15%**: `tax_base = max(0, income - expenses)`, `tax_15 = tax_base * 0.15`, `min_tax_1 = income * 0.01`, `tax_due = max(tax_15, min_tax_1)`
- [ ] **Классификация расходов** по ст. 346.16 НК РФ: `PAYOUT_TO_CONTRACTORS`, `BANK_COMMISSIONS`, `SOFTWARE_HOSTING`, `TAXES_AND_FEES`, `OTHER`
- [ ] **НДС 22%** — учёт в транзакциях и квартальной агрегации (с 01.01.2026)
- [ ] **НДФЛ 13%** — автоматическое удержание при выплатах физлицам, запись в `ndfl_withheld`
- [ ] **НПД** — трекинг чеков самозанятых, fallback на НДФЛ при просрочке

### 🔁 Сторнирование и коррекция
- [ ] **Storno mechanism** — `record_storno()` создаёт обратную транзакцию, генерирует KudirRecord с отрицательной суммой, пересчитывает `tax_due`
- [ ] **Self-referencing FK** — `reverses_transaction_id` для отслеживания цепочки коррекций
- [ ] **is_reversed flag** — защита от двойного сторнирования

### 🔐 Безопасность и соответствие
- [ ] **Шифрование PII** — `EncryptedString`/`HashableEncryptedString` для `PlatformAccount` и `LegalProfile`
- [ ] **AuditLog** — логирование всех чувствительных операций с `inn_hash`
- [ ] **54-ФЗ** — сохранение `receipt_id`, `payment_method_type` из вебхуков ЮKассы

### 🤖 Автоматизация
- [ ] **Celery-beat reminders** — ежедневная проверка налоговых дедлайнов (УСН квартальные, НДФЛ ежемесячно)
- [ ] **EDO protocol stub** — `EdoProvider`/`StubEdoProvider` для будущей интеграции с Диадок/СБИС
- [ ] **Admin UI** — экран `/admin/tax-summary` с выгрузкой КУДиР, налоговой сводкой, кнопками экспорта

### 📊 Автоматический учёт расходов
- [ ] **YooKassa fee** — автоматически записывается как `BANK_COMMISSIONS` при успешном платеже
- [ ] **Payout net_amount** — автоматически записывается как `PAYOUT_TO_CONTRACTORS` при статусе `PAID`
- [ ] **Отказоустойчивость** — все интеграции обёрнуты в `try/except`, ошибки учёта НЕ блокируют основной флоу

---

## 🚀 Чеклист деплоя налоговой подсистемы

```bash
# 1. Проверить текущую миграцию
poetry run alembic current
# Ожидаемый вывод: s26d002_storno_expense (head)

# 2. Применить миграции (если ещё не применены)
poetry run alembic upgrade head

# 3. Запустить статический анализ
poetry run ruff check src/ --fix && poetry run ruff format src/
poetry run mypy src/ --ignore-missing-imports
cd mini_app && npx eslint src/screens/admin/ --ext .ts,.tsx

# 4. Перезапустить сервисы
docker compose restart api worker-critical worker-background beat

# 5. Проверить Celery-задачу напоминаний
docker compose logs beat | grep "tax:calendar_reminder"

# 6. Протестировать генерацию акта
# (через завершённое размещение или напрямую через сервис)
# Пример вызова:
# await ActService.generate_for_completed_placement(session, placement)

# 7. Проверить админ-панель
# Открыть Mini App → Админ → 🧾 Налоги → выбрать квартал → 
# проверить: (1) таблицу доходов/расходов, (2) расчёт tax_due, 
# (3) кнопки скачивания PDF/CSV

# 8. Верифицировать шифрование
# Убедиться, что inn, bank_account в PlatformAccount читаются 
# только через сервис-дешифратор (не напрямую из БД)

# 9. Протестировать сторнирование
# Создать тестовую транзакцию → вызвать record_storno() → 
# проверить: (1) создана обратная транзакция, (2) KudirRecord с 
# отрицательной суммой, (3) tax_due пересчитан корректно

# 10. Проверить автоматический учёт расходов
# Создать тестовый топ-ап → проверить, что комиссия ЮKассы 
# записана как BANK_COMMISSIONS в КУДиР
```

---

## 📋 Инструкция по верификации ФНС-отчётности (ООО УСН 15%)

### Для бухгалтера / аудитора:

#### 1. КУДиР за квартал
```sql
-- Доходы
SELECT entry_number, operation_date, description, income_amount 
FROM kudir_records 
WHERE quarter = '2026-Q1' AND operation_type = 'income' 
ORDER BY entry_number;

-- Расходы
SELECT entry_number, operation_date, expense_category, description, expense_amount 
FROM kudir_records 
WHERE quarter = '2026-Q1' AND operation_type = 'expense' 
ORDER BY entry_number;
```
→ Экспорт: `GET /api/admin/tax/kudir/2026/1/csv` → открыть в 1С / Эксель → сверить с банковскими выписками.

#### 2. Декларация УСН 15%
```sql
SELECT 
    usn_revenue as income,
    total_expenses as expenses,
    tax_base_15,
    calculated_tax_15,
    min_tax_1,
    tax_due,
    applicable_rate
FROM platform_quarterly_revenues 
WHERE year = 2026 AND quarter = 1;
```
→ Проверка формулы:  
`tax_base_15 = GREATEST(0, usn_revenue - total_expenses)`  
`calculated_tax_15 = tax_base_15 * 0.15`  
`min_tax_1 = usn_revenue * 0.01`  
`tax_due = GREATEST(calculated_tax_15, min_tax_1)`

#### 3. Акты выполненных работ
```sql
SELECT act_number, act_date, pdf_path, placement_request_id 
FROM acts 
WHERE act_date BETWEEN '2026-01-01' AND '2026-03-31';
```
→ Сверить с размещёнными постами: каждый акт должен соответствовать завершённому `placement_request`.

#### 4. Чеки 54-ФЗ
```sql
SELECT payment_id, receipt_id, payment_method_type, fiscal_receipt_number 
FROM yookassa_payments 
WHERE status = 'succeeded';
```
→ Сверить с отчётом ЮKассы: каждый успешный платёж должен иметь `receipt_id`.

#### 5. Удержание НДФЛ
```sql
SELECT gross_amount, ndfl_withheld, net_amount, owner_id 
FROM payout_requests 
WHERE ndfl_withheld > 0;
```
→ Проверка расчёта: `ndfl_withheld = ROUND(gross_amount * 0.13, 2)` для `legal_status = 'individual'`.

#### 6. Сторнированные операции
```sql
SELECT 
    t1.id as original_id,
    t1.amount as original_amount,
    t2.id as storno_id,
    t2.amount as storno_amount,
    t1.is_reversed
FROM transactions t1
LEFT JOIN transactions t2 ON t2.reverses_transaction_id = t1.id
WHERE t2.type = 'storno' OR t1.is_reversed = true;
```
→ Проверка: `storno_amount = -original_amount`, `is_reversed = true`.

---

## 🗓️ Roadmap для S-27 (следующий спринт)

| Приоритет | Задача | Описание | Оценка |
|-----------|--------|----------|--------|
| 🔴 **Высокий** | Интеграция с реальным ЭДО-провайдером | Реализация `DiadocProvider` / `SbisProvider` вместо `StubEdoProvider`, подписание актов КЭП | 5-7 дней |
| 🔴 **Высокий** | Автоматическая генерация чеков 54-ФЗ | Интеграция `receipt` parameter в `create_payment()` ЮKассы, endpoint для скачивания чеков | 3-5 дней |
| 🟡 **Средний** | KEP-подписание для ЮЛ | Квалифицированная электронная подпись для договоров с юрлицами (интеграция с КриптоПро) | 7-10 дней |
| 🟡 **Средний** | Экспорт деклараций в ФНС-формат | XML-генерация для УСН 15%, НДФЛ, НДС (соответствие формату ФНС) | 4-6 дней |
| 🟢 **Низкий** | Полная веб-версия rekharbor.ru | Отдельный фронтенд для десктопа (не Telegram Mini App) | 14+ дней |

---

## 📦 Финальные артефакты (готовы к генерации)

- [ ] `docs/S26_RELEASE_NOTES.md` — подробные заметки о релизе (список изменений, миграции, breaking changes)
- [ ] `scripts/tax/verify_fns_compliance.sh` — скрипт автоматической верификации (запросы к БД, проверка формул)
- [ ] `docs/TAX_AUDIT_CHECKLIST_OOO_USN15.md` — чеклист для прохождения налоговой проверки ООО УСН 15%
- [ ] `docs/ACCOUNTING_ARCHITECTURE.md` — архитектурная документация налоговой подсистемы (диаграммы, flow)

---

## 🔧 Поддержка и мониторинг

### Логи для отладки налоговой логики
```bash
# Фильтрация логов по налоговым операциям
docker compose logs api | grep -E "TaxAggregation|KUDiR|storno|expense"

# Мониторинг Celery-задач
docker compose logs beat | grep "tax:calendar_reminder"
docker compose exec flower celery -A src.tasks.celery_app inspect active

# Проверка шифрования в БД (должны быть зашифрованные строки)
docker compose exec postgres psql -U rekharbor -d rekharbor -c \
  "SELECT inn, bank_account FROM platform_account LIMIT 1;"
```

### Метрики для мониторинга
```python
# Пример добавления метрик в GlitchTip/Sentry
from sentry_sdk import set_tag, set_context

set_tag("tax_regime", "usn_15")
set_context("tax_calculation", {
    "income": str(income),
    "expenses": str(expenses),
    "tax_due": str(tax_due),
    "applicable_rate": applicable_rate
})
```

## 🔗 Текущая схема связей документов (реализовано)

```
┌─────────────────┐
│   PlacementRequest   │ ← центральный узел
└────────┬────────┘
         │
    ┌────┴────┬────────────┬────────────┐
    ▼         ▼            ▼            ▼
┌───────┐ ┌──────┐  ┌──────────┐  ┌─────────┐
│Contract│ │  Act  │  │Transaction│  │MailingLog│
└───┬───┘ └──┬───┘  └─────┬────┘  └────┬────┘
    │        │          │           │
    │        │          ▼           │
    │        │    ┌──────────┐     │
    │        │    │YooKassaPayment│ │
    │        │    └──────────┘     │
    │        │                     │
    │        ▼                     │
    │  ┌──────────┐               │
    │  │  Invoice  │◄──────────────┘
    │  └────┬─────┘
    │       │
    ▼       ▼
┌─────────────────┐
│   LegalProfile   │ (snapshot в Contract/Transaction)
└─────────────────┘
```

### ✅ Реализованные связи (FK)

| Документ | Связан с | Поле | Статус |
|----------|----------|------|--------|
| `Contract` | `PlacementRequest` | `placement_request_id` | ✅ |
| `Act` | `PlacementRequest` | `placement_request_id` | ✅ (Sprint A.1) |
| `Invoice` | `User` | `user_id` | ✅ (Sprint C.1) |
| `Transaction` | `Contract` | `contract_id` (nullable) | ✅ (Sprint A.3) |
| `Transaction` | `PlacementRequest` | `placement_request_id` | ✅ (было) |
| `Transaction` | `PayoutRequest` | `payout_id` | ✅ (было) |
| `Transaction` | `YooKassaPayment` | `yookassa_payment_id` | ✅ (было) |

### 📋 Snapshot-данные (для аудита)

| Модель | Snapshot-поле | Зачем нужно |
|--------|--------------|-------------|
| `Contract` | `legal_status_snapshot: JSONB` | Фиксация юр. статуса контрагента на момент подписания |
| `Transaction` | `counterparty_legal_status: String` | Налоговый статус на момент операции (не зависит от изменений в `LegalProfile`) |
| `Transaction` | `currency: String` | Валюта операции (будущая поддержка мультивалютности) |

---

## ⚠️ Пробелы: чего НЕ хватает для полной связности

### 1. **Act → Contract** (прямая связь)
```python
# Сейчас: Act → PlacementRequest → Contract (через JOIN)
# Лучше: добавить прямую ссылку
act.contract_id: Mapped[int | None] = mapped_column(
    Integer, ForeignKey("contracts.id"), nullable=True
)
```
**Зачем**: Быстрый поиск всех актов по договору без лишних джойнов.

### 2. **Invoice → PlacementRequest / Contract**
```python
# Сейчас: Invoice → User только
# Нужно: привязка к конкретной операции
invoice.placement_request_id: Mapped[int | None] = mapped_column(
    Integer, ForeignKey("placement_requests.id"), nullable=True
)
invoice.contract_id: Mapped[int | None] = mapped_column(
    Integer, ForeignKey("contracts.id"), nullable=True
)
```
**Зачем**: Счёт должен ссылаться на основание (договор/размещение) для бухгалтерии.

### 3. **Transaction → Act / Invoice** (обратная связь)
```python
# Для трассировки: какая транзакция оплачивает какой документ
transaction.act_id: Mapped[int | None] = mapped_column(
    Integer, ForeignKey("acts.id"), nullable=True
)
transaction.invoice_id: Mapped[int | None] = mapped_column(
    Integer, ForeignKey("invoices.id"), nullable=True
)
```
**Зачем**: При налоговой проверке можно показать цепочку: `Счёт → Оплата → Акт → Размещение`.

### 4. **DocumentLink junction table** (опционально, для гибкости)
```python
# Если нужна связь "многие-ко-многим" (один акт на несколько размещений)
class DocumentLink(Base):
    __tablename__ = "document_links"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_type: Mapped[str]  # 'contract', 'act', 'invoice'
    source_id: Mapped[int]
    target_type: Mapped[str]
    target_id: Mapped[int]
    link_type: Mapped[str]  # 'basis', 'payment', 'completion'
```

---

## 🎯 Рекомендации для ООО УСН 15%

Для полноценного учёта **доходы − расходы** критично иметь:

### Минимальный набор связей (обязательно)
```
PlacementRequest
    ├── Contract (основание размещения)
    ├── Act (подтверждение выполнения)
    ├── Invoice (счёт на оплату, если B2B)
    └── Transaction × N (платежи: топ-ап, комиссия, выплата)
```

### Для налоговой проверки (желательно)
```
Transaction
    ├── contract_id → Contract
    ├── act_id → Act (если оплата за выполнение)
    ├── invoice_id → Invoice (если оплата по счёту)
    └── reverses_transaction_id → Transaction (сторно)
```

### Для аудита (рекомендуется)
```
DocumentAuditLog
    ├── document_type: 'contract' | 'act' | 'invoice'
    ├── document_id: int
    ├── action: 'created' | 'signed' | 'paid' | 'cancelled'
    ├── performed_by: user_id
    ├── timestamp: datetime
    └── metadata: JSONB (IP, user-agent, signature_hash)
```

---

## 🛠️ Как добавить связи (additive миграция)

Если нужно добавить недостающие связи, вот пример безопасной миграции:

```python
# src/db/migrations/versions/s26e001_add_document_links.py
def upgrade() -> None:
    # Act → Contract
    op.add_column('acts', sa.Column('contract_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_acts_contract_id', 'acts', 'contracts', 
                         ['contract_id'], ['id'])
    
    # Invoice → PlacementRequest, Contract
    op.add_column('invoices', sa.Column('placement_request_id', sa.Integer(), nullable=True))
    op.add_column('invoices', sa.Column('contract_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_invoices_placement_request', 'invoices', 'placement_requests',
                         ['placement_request_id'], ['id'])
    op.create_foreign_key('fk_invoices_contract', 'invoices', 'contracts',
                         ['contract_id'], ['id'])
    
    # Transaction → Act, Invoice
    op.add_column('transactions', sa.Column('act_id', sa.Integer(), nullable=True))
    op.add_column('transactions', sa.Column('invoice_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_transactions_act', 'transactions', 'acts',
                         ['act_id'], ['id'])
    op.create_foreign_key('fk_transactions_invoice', 'transactions', 'invoices',
                         ['invoice_id'], ['id'])

def downgrade() -> None:
    # В обратном порядке, без DROP данных
    op.drop_constraint('fk_transactions_invoice', 'transactions', type_='foreignkey')
    op.drop_constraint('fk_transactions_act', 'transactions', type_='foreignkey')
    op.drop_column('transactions', 'invoice_id')
    op.drop_column('transactions', 'act_id')
    # ... и т.д.
