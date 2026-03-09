# DATABASE INTEGRITY AUDIT REPORT

**Проект:** Market Telegram Bot (RekHarborBot)  
**Дата аудита:** 2026-03-10  
**Аудитор:** Qwen Code  
**Статус:** ✅ ЗАВЕРШЕНО

---

## 📊 ОБЗОР НАЙДЕННЫХ ПРОБЛЕМ

| Категория | Критические | Высокие | Средние | Низкие | Всего |
|-----------|-------------|---------|---------|--------|-------|
| Foreign Keys | 0 | 0 | 1 | - | 1 |
| Unique Constraints | 0 | 0 | 0 | - | 0 |
| Check Constraints | 0 | 3 | - | - | 3 |
| Not Null Constraints | 0 | 2 | 1 | - | 3 |
| Indexes | 0 | 0 | 2 | - | 2 |
| Миграции Alembic | 🔴 1 | - | - | - | 1 |
| **ИТОГО** | **1** | **5** | **4** | - | **10** |

---

## 1. FOREIGN KEY CONSTRAINTS

### 1.1 Все FK с ondelete (✅ ХОРОШО)

| Таблица | Поле | FK Target | ondelete | onupdate | Статус |
|---------|------|-----------|----------|----------|--------|
| **notifications** | user_id | users.id | CASCADE | - | ✅ |
| **channel_ratings** | channel_id | telegram_chats.id | CASCADE | - | ✅ |
| **transactions** | user_id | users.id | CASCADE | - | ✅ |
| **campaigns** | user_id | users.id | CASCADE | - | ✅ |
| **user_badges** | user_id | users.id | CASCADE | - | ✅ |
| **user_badges** | badge_id | badges.id | CASCADE | - | ✅ |
| **badge_progress** | badge_id | badges.id | CASCADE | - | ✅ |
| **mailing_logs** | campaign_id | campaigns.id | CASCADE | - | ✅ |
| **mailing_logs** | chat_id | telegram_chats.id | SET NULL | - | ✅ |
| **crypto_payments** | user_id | users.id | CASCADE | - | ✅ |
| **user_channel_analytics** | user_id | users.id | SET NULL | - | ✅ |
| **chat_snapshots** | chat_id | telegram_chats.id | CASCADE | - | ✅ |
| **payouts** | owner_id | users.id | CASCADE | - | ✅ |
| **payouts** | channel_id | telegram_chats.id | CASCADE | - | ✅ |
| **payouts** | placement_id | mailing_logs.id | CASCADE | - | ✅ |
| **content_flags** | campaign_id | campaigns.id | CASCADE | - | ✅ |
| **content_flags** | reviewed_by | users.id | SET NULL | - | ✅ |
| **channel_mediakits** | chat_id | telegram_chats.id | CASCADE | - | ✅ |
| **channel_mediakits** | owner_id | users.id | CASCADE | - | ✅ |
| **reviews** | reviewer_id | users.id | CASCADE | - | ✅ |
| **reviews** | reviewed_user_id | users.id | CASCADE | - | ✅ |
| **reviews** | chat_id | telegram_chats.id | SET NULL | - | ✅ |
| **reviews** | placement_id | mailing_logs.id | CASCADE | - | ✅ |

**Вывод:** ✅ Все 23 Foreign Key имеют `ondelete` правило.

### 1.2 Проблемы

| ID | Проблема | Критичность | Решение |
|----|----------|-------------|---------|
| FK1 | Нет проблем — все FK имеют ondelete | - | - |

---

## 2. UNIQUE CONSTRAINTS

### 2.1 Все Unique Constraints (✅ ХОРОШО)

| Таблица | Поле(я) | Constraint | Статус |
|---------|---------|------------|--------|
| **users** | telegram_id | unique=True + UniqueConstraint | ✅ |
| **users** | referral_code | unique=True | ✅ |
| **badges** | code | unique=True | ✅ |
| **user_badges** | user_id, badge_id | UniqueConstraint (uq_user_badge) | ✅ |
| **mailing_logs** | campaign_id, chat_telegram_id | UniqueConstraint (uq_mailing_logs_campaign_chat) | ✅ |
| **transactions** | payment_id | unique=True + UniqueConstraint | ✅ |
| **crypto_payments** | invoice_id | unique=True | ✅ |
| **content_flags** | campaign_id | UniqueConstraint (uq_content_flags_campaign_id) | ✅ |
| **channel_mediakits** | chat_id | unique=True | ✅ |
| **reviews** | reviewer_id, placement_id | UniqueConstraint (uq_reviewer_placement) | ✅ |
| **channel_ratings** | channel_id, date | UniqueConstraint (uq_channel_rating_date) | ✅ |
| **categories** | topic, subcategory | UniqueConstraint (uq_topic_subcategory) | ✅ |
| **chat_snapshots** | chat_id, snapshot_date | UniqueConstraint (uq_chat_snapshot_date) | ✅ |
| **telegram_chats** | telegram_id | unique=True | ✅ |
| **telegram_chats** | username | unique=True | ✅ |

**Вывод:** ✅ Все критичные поля имеют unique constraints.

### 2.2 Проблемы

| ID | Проблема | Критичность | Решение |
|----|----------|-------------|---------|
| UC1 | Нет проблем — все unique constraints на месте | - | - |

---

## 3. CHECK CONSTRAINTS

### 3.1 Отсутствие Check Constraints (⚠️ ПРОБЛЕМА)

**Найдено:** 0 CheckConstraint в моделях  
**Ожидалось:** Ограничения на положительные числа

| Таблица | Поле | Ожидаемый constraint | Статус |
|---------|------|---------------------|--------|
| **users** | credits | credits >= 0 | ⚠️ ОТСУТСТВУЕТ |
| **users** | balance | balance >= 0 | ⚠️ ОТСУТСТВУЕТ |
| **campaigns** | cost | cost >= 0 | ⚠️ ОТСУТСТВУЕТ |
| **transactions** | amount | amount > 0 | ⚠️ ОТСУТСТВУЕТ |
| **payouts** | amount | amount > 0 | ⚠️ ОТСУТСТВУЕТ |
| **crypto_payments** | amount | amount > 0 | ⚠️ ОТСУТСТВУЕТ |

### 3.2 Проблемы

| ID | Проблема | Критичность | Решение |
|----|----------|-------------|---------|
| CC1 | users.credits — нет проверки >= 0 | 🟠 HIGH | Добавить CheckConstraint |
| CC2 | campaigns.cost — нет проверки >= 0 | 🟠 HIGH | Добавить CheckConstraint |
| CC3 | transactions.amount — нет проверки > 0 | 🟠 HIGH | Добавить CheckConstraint |

**Пример решения:**
```python
# src/db/models/user.py
__table_args__ = (
    CheckConstraint("credits >= 0", name="ck_users_credits_positive"),
    CheckConstraint("balance >= 0", name="ck_users_balance_positive"),
)

# src/db/models/campaign.py
__table_args__ = (
    CheckConstraint("cost >= 0", name="ck_campaigns_cost_positive"),
)
```

---

## 4. NOT NULL CONSTRAINTS

### 4.1 Статистика

```
nullable=False: 132 поля
nullable=True:  86 полей
```

### 4.2 Проблемные поля

| Таблица | Поле | Текущий | Ожидание | Проблема |
|---------|------|---------|----------|----------|
| **campaigns** | cost | nullable=True | False | ⚠️ Может быть NULL |
| **campaigns** | scheduled_at | nullable=True | False | ⚠️ Может быть NULL |
| **mailing_logs** | cost | nullable=True | False | ⚠️ Может быть NULL |

### 4.3 Проблемы

| ID | Проблема | Критичность | Решение |
|----|----------|-------------|---------|
| NN1 | campaigns.cost — nullable=True | 🟠 HIGH | Изменить на nullable=False |
| NN2 | mailing_logs.cost — nullable=True | 🟠 HIGH | Изменить на nullable=False |
| NN3 | campaigns.scheduled_at — nullable=True | 🟡 MEDIUM | Оставить nullable (опционально) |

---

## 5. INDEXES

### 5.1 Все индексы (✅ ХОРОШО)

**Одиночные индексы (index=True):** 60+  
**Составные индексы:**

| Таблица | Индекс | Поля | Статус |
|---------|--------|------|--------|
| **transactions** | ix_transactions_user_type | user_id, type | ✅ |
| **transactions** | ix_transactions_created | created_at | ✅ |
| **campaigns** | ix_campaigns_user_status | user_id, status | ✅ |
| **campaigns** | ix_campaigns_scheduled_status | scheduled_at, status | ✅ |
| **mailing_logs** | ix_mailing_logs_status_campaign | status, campaign_id | ✅ |
| **mailing_logs** | ix_mailing_logs_chat_telegram | chat_telegram_id | ✅ |
| **crypto_payments** | ix_crypto_payments_status | status | ✅ |
| **crypto_payments** | ix_crypto_payments_user_status | user_id, status | ✅ |
| **content_flags** | ix_content_flags_decision | decision | ✅ |
| **content_flags** | ix_content_flags_categories | categories (GIN) | ✅ |
| **telegram_chats** | ix_telegram_chats_member_count | member_count | ✅ |
| **telegram_chats** | ix_telegram_chats_rating | rating | ✅ |
| **telegram_chats** | ix_telegram_chats_topic_active | topic, is_active | ✅ |
| **telegram_chats** | ix_telegram_chats_is_active | is_active | ✅ |

### 5.2 Missing Indexes

| Таблица | Поле | Почему нужен | Критичность |
|---------|------|--------------|-------------|
| **campaigns** | status | Частая фильтрация по статусу | 🟡 MEDIUM |
| **payouts** | status | Частая фильтрация по статусу | 🟡 MEDIUM |

### 5.3 Проблемы

| ID | Проблема | Критичность | Решение |
|----|----------|-------------|---------|
| IX1 | campaigns.status — нет индекса | 🟡 MEDIUM | Добавить index=True |
| IX2 | payouts.status — нет индекса | 🟡 MEDIUM | Добавить index=True |

---

## 6. MIGRATIONS ALEMBIC

### 6.1 Статус миграций

**Проблема:** 🔴 **ОТСУТСТВУЕТ ПАПКА alembic/versions/**

```bash
$ ls -la alembic/
ls: cannot access 'alembic/': No such file or directory

$ find . -name "alembic" -type d
./.mypy_cache/3.13/alembic
./.venv/lib/python3.13/site-packages/alembic
```

**Файлы в корне:**
- `alembic.ini` — конфигурация
- `alembic_sync.ini` — синхронная версия

**Вывод:** ❌ Миграции не ведутся или удалены из репозитория.

### 6.2 Проблемы

| ID | Проблема | Критичность | Решение |
|----|----------|-------------|---------|
| MIG1 | Отсутствует папка alembic/versions/ | 🔴 CRITICAL | Инициализировать Alembic |
| MIG2 | Нет истории миграций | 🔴 CRITICAL | Создать начальную миграцию |

---

## 7. РЕКОМЕНДАЦИИ

### Критические (P0) — Исправить немедленно:

- [ ] **MIG1:** Инициализировать Alembic migrations
  ```bash
  cd /opt/market-telegram-bot
  alembic init alembic
  alembic revision --autogenerate -m "initial schema"
  ```

### Важные (P1) — Исправить в течение спринта:

- [ ] **CC1-CC3:** Добавить CheckConstraint для положительных чисел
  ```python
  # users.py
  __table_args__ = (
      CheckConstraint("credits >= 0", name="ck_users_credits_positive"),
      CheckConstraint("balance >= 0", name="ck_users_balance_positive"),
  )
  
  # campaign.py
  __table_args__ = (
      CheckConstraint("cost >= 0", name="ck_campaigns_cost_positive"),
  )
  
  # transaction.py
  __table_args__ = (
      CheckConstraint("amount > 0", name="ck_transactions_amount_positive"),
  )
  ```

- [ ] **NN1-NN2:** Изменить nullable на False для cost полей
  ```python
  # campaign.py
  cost: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
  
  # mailing_log.py
  cost: Mapped[int] = mapped_column(Integer, nullable=False)
  ```

### Средние (P2) — Исправить в следующем спринте:

- [ ] **IX1:** Добавить индекс на campaigns.status
  ```python
  status: Mapped[CampaignStatus] = mapped_column(..., index=True)
  ```

- [ ] **IX2:** Добавить индекс на payouts.status
  ```python
  status: Mapped[PayoutStatus] = mapped_column(..., index=True)
  ```

---

## 8. ПОЛОЖИТЕЛЬНЫЕ НАХОДКИ ✅

### Что реализовано правильно:

1. **Все Foreign Keys имеют ondelete:**
   - 23 FK с `ondelete="CASCADE"` или `ondelete="SET NULL"`
   - Нет FK без правил удаления

2. **Unique constraints на критичных полях:**
   - `users.telegram_id` — unique ✅
   - `users.referral_code` — unique ✅
   - `badges.code` — unique ✅
   - `transactions.payment_id` — unique ✅
   - `crypto_payments.invoice_id` — unique ✅

3. **Хорошая индексация:**
   - 60+ полей с `index=True`
   - 14 составных индексов
   - GIN индекс для массивов (content_flags.categories)

4. **Правильные FK правила:**
   - CASCADE для зависимых записей (campaigns → mailing_logs)
   - SET NULL для опциональных связей (mailing_logs → telegram_chats)

---

## 9. ИТОГОВАЯ ОЦЕНКА РИСКОВ

| Категория | Текущий риск | После исправления P0+P1 |
|-----------|--------------|------------------------|
| Foreign Keys | 🟢 Низкий | 🟢 Низкий |
| Unique Constraints | 🟢 Низкий | 🟢 Низкий |
| Check Constraints | 🟠 Средний | 🟢 Низкий |
| Not Null Constraints | 🟡 Низкий | 🟢 Низкий |
| Indexes | 🟡 Низкий | 🟢 Низкий |
| Миграции | 🔴 Критический | 🟢 Низкий |

**Общий риск:** 🟠 **СРЕДНИЙ** → После исправлений P0+P1: 🟢 **НИЗКИЙ**

---

## 10. ПЛАН ДЕЙСТВИЙ

### Неделя 1 (P0):
1. Инициализировать Alembic
2. Создать начальную миграцию
3. Применить миграцию к production

### Неделя 2 (P1):
1. Добавить CheckConstraint для credits/balance
2. Добавить CheckConstraint для cost/amount
3. Изменить nullable=False для cost полей

### Неделя 3 (P2):
1. Добавить индекс на campaigns.status
2. Добавить индекс на payouts.status
3. Создать миграции для всех изменений

---

**АУДИТ ЗАВЕРШЁН:** 2026-03-10  
**СЛЕДУЮЩИЙ АУДИТ:** После применения миграций

---

**ИСПОЛНИТЕЛЬ:** Qwen Code  
**ФАЙЛ ОТЧЁТА:** `docs/audit/reports/DATABASE_INTEGRITY_AUDIT.md`
