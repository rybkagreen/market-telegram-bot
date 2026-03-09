# 📋 ПЛАН ИСПРАВЛЕНИЙ — DATABASE INTEGRITY

**Проект:** Market Telegram Bot (RekHarborBot)  
**Дата:** 2026-03-10  
**На основе аудита:** `docs/audit/reports/DATABASE_INTEGRITY_AUDIT.md`  
**Всего задач:** 7 (1 P0 + 4 P1 + 2 P2)

---

## 🔴 ПРИОРИТЕТ P0 — КРИТИЧЕСКИЕ (НЕДЕЛЯ 1)

### P0.1 — MIG1: Инициализировать Alembic migrations

**Проблема:** Отсутствует папка `alembic/versions/` — нет истории миграций.

**Файлы для создания:**
1. `alembic/` (папка)
2. `alembic/env.py`
3. `alembic/script.py.mako`
4. `alembic/versions/` (папка для миграций)
5. Первая миграция: `alembic/versions/001_initial_schema.py`

**Шаги:**

#### Шаг 1: Инициализация Alembic

```bash
cd /opt/market-telegram-bot

# Создать папку alembic
mkdir -p alembic/versions

# Создать env.py
cat > alembic/env.py << 'EOF'
"""Alembic environment configuration."""

from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context

# Alembic Config
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Add your model's MetaData object here for 'autogenerate' support
from src.db.base import Base
from src.db.models import *  # Import all models
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
EOF

# Создать script.py.mako
cat > alembic/script.py.mako << 'EOF'
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
EOF

# Создать alembic.ini
cat > alembic.ini << 'EOF'
[alembic]
script_location = alembic
prepend_sys_path = .
sqlalchemy.url = postgresql+asyncpg://market_bot:market_bot_pass@localhost:5432/market_bot_db

[post_write_hooks]

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
EOF
```

#### Шаг 2: Создать начальную миграцию

```bash
cd /opt/market-telegram-bot

# Создать начальную миграцию
alembic revision --autogenerate -m "initial_schema"

# Проверить миграцию
alembic current  # Должно показать (empty)
alembic heads    # Должно показать новую миграцию

# Применить миграцию
alembic upgrade head

# Проверить что применена
alembic current  # Должно показать revision
```

#### Шаг 3: Проверка

```bash
# Проверить что все таблицы созданы
docker compose exec postgres psql -U market_bot -d market_bot_db -c "\dt"

# Проверить что alembic_version существует
docker compose exec postgres psql -U market_bot -d market_bot_db -c "SELECT * FROM alembic_version;"
```

**Время:** 4 часа  
**Исполнитель:** belin  
**Проверка:** `alembic current` показывает revision, таблицы в БД существуют

---

## 🟠 ПРИОРИТЕТ P1 — ВАЖНЫЕ (НЕДЕЛЯ 2)

### P1.1 — CC1: Добавить CheckConstraint для users.credits

**Файл:** `src/db/models/user.py`

**Было (строка ~369):**
```python
__table_args__ = (
    UniqueConstraint("telegram_id", name="uq_users_telegram_id"),
)
```

**Стало:**
```python
__table_args__ = (
    UniqueConstraint("telegram_id", name="uq_users_telegram_id"),
    CheckConstraint("credits >= 0", name="ck_users_credits_positive"),
    CheckConstraint("balance >= 0", name="ck_users_balance_positive"),
)
```

**Импорт в начало файла:**
```python
from sqlalchemy import CheckConstraint
```

**Миграция:**
```bash
alembic revision -m "add_check_constraints_users"
```

**Содержимое миграции:**
```python
def upgrade() -> None:
    # Add check constraints to users table
    op.create_check_constraint(
        "ck_users_credits_positive",
        "users",
        "credits >= 0"
    )
    op.create_check_constraint(
        "ck_users_balance_positive",
        "users",
        "balance >= 0"
    )

def downgrade() -> None:
    op.drop_constraint("ck_users_credits_positive", "users", type_="check")
    op.drop_constraint("ck_users_balance_positive", "users", type_="check")
```

**Время:** 1 час  
**Исполнитель:** belin

---

### P1.2 — CC2: Добавить CheckConstraint для campaigns.cost

**Файл:** `src/db/models/campaign.py`

**Было (строка ~298):**
```python
__table_args__ = (
    Index("ix_campaigns_user_status", "user_id", "status"),
    Index("ix_campaigns_scheduled_status", "scheduled_at", "status"),
)
```

**Стало:**
```python
__table_args__ = (
    Index("ix_campaigns_user_status", "user_id", "status"),
    Index("ix_campaigns_scheduled_status", "scheduled_at", "status"),
    CheckConstraint("cost >= 0", name="ck_campaigns_cost_positive"),
)
```

**Импорт в начало файла:**
```python
from sqlalchemy import CheckConstraint
```

**Миграция:**
```bash
alembic revision -m "add_check_constraint_campaigns_cost"
```

**Содержимое миграции:**
```python
def upgrade() -> None:
    op.create_check_constraint(
        "ck_campaigns_cost_positive",
        "campaigns",
        "cost >= 0"
    )

def downgrade() -> None:
    op.drop_constraint("ck_campaigns_cost_positive", "campaigns", type_="check")
```

**Время:** 1 час  
**Исполнитель:** belin

---

### P1.3 — CC3: Добавить CheckConstraint для transactions.amount

**Файл:** `src/db/models/transaction.py`

**Было (строка ~156):**
```python
__table_args__ = (
    UniqueConstraint("payment_id", name="uq_transactions_payment_id"),
    Index("ix_transactions_user_type", "user_id", "type"),
    Index("ix_transactions_created", "created_at"),
)
```

**Стало:**
```python
__table_args__ = (
    UniqueConstraint("payment_id", name="uq_transactions_payment_id"),
    Index("ix_transactions_user_type", "user_id", "type"),
    Index("ix_transactions_created", "created_at"),
    CheckConstraint("amount > 0", name="ck_transactions_amount_positive"),
)
```

**Импорт в начало файла:**
```python
from sqlalchemy import CheckConstraint
```

**Миграция:**
```bash
alembic revision -m "add_check_constraint_transactions_amount"
```

**Содержимое миграции:**
```python
def upgrade() -> None:
    op.create_check_constraint(
        "ck_transactions_amount_positive",
        "transactions",
        "amount > 0"
    )

def downgrade() -> None:
    op.drop_constraint("ck_transactions_amount_positive", "transactions", type_="check")
```

**Время:** 1 час  
**Исполнитель:** belin

---

### P1.4 — NN1-NN2: Изменить nullable=False для cost полей

**Файлы:**
1. `src/db/models/campaign.py` (строка ~257)
2. `src/db/models/mailing_log.py` (строка ~92)

#### campaign.py

**Было:**
```python
cost: Mapped[float] = mapped_column(
    Numeric(10, 2),
    nullable=True,  # ❌
    default=0.0,
)
```

**Стало:**
```python
cost: Mapped[float] = mapped_column(
    Numeric(10, 2),
    nullable=False,  # ✅
    default=0.0,
)
```

#### mailing_log.py

**Было:**
```python
cost: Mapped[int] = mapped_column(
    Integer,
    nullable=True,  # ❌
    default=0,
)
```

**Стало:**
```python
cost: Mapped[int] = mapped_column(
    Integer,
    nullable=False,  # ✅
    default=0,
)
```

**Миграция:**
```bash
alembic revision -m "make_cost_fields_not_nullable"
```

**Содержимое миграции:**
```python
def upgrade() -> None:
    # First update NULL values to 0
    op.execute("UPDATE campaigns SET cost = 0 WHERE cost IS NULL")
    op.execute("UPDATE mailing_logs SET cost = 0 WHERE cost IS NULL")
    
    # Then alter columns to NOT NULL
    op.alter_column("campaigns", "cost",
               existing_type=sa.Numeric(10, 2),
               nullable=False)
    op.alter_column("mailing_logs", "cost",
               existing_type=sa.Integer,
               nullable=False)

def downgrade() -> None:
    op.alter_column("mailing_logs", "cost",
               existing_type=sa.Integer,
               nullable=True)
    op.alter_column("campaigns", "cost",
               existing_type=sa.Numeric(10, 2),
               nullable=True)
```

**Время:** 2 часа  
**Исполнитель:** belin

---

## 🟡 ПРИОРИТЕТ P2 — СРЕДНИЕ (НЕДЕЛЯ 3)

### P2.1 — IX1: Добавить индекс на campaigns.status

**Файл:** `src/db/models/campaign.py` (строка ~177)

**Было:**
```python
status: Mapped[CampaignStatus] = mapped_column(
    Enum(CampaignStatus),
    nullable=False,
    default=CampaignStatus.DRAFT,
)
```

**Стало:**
```python
status: Mapped[CampaignStatus] = mapped_column(
    Enum(CampaignStatus),
    nullable=False,
    default=CampaignStatus.DRAFT,
    index=True,  # ✅ Добавить
)
```

**Миграция:**
```bash
alembic revision -m "add_index_campaigns_status"
```

**Содержимое миграции:**
```python
def upgrade() -> None:
    op.create_index("ix_campaigns_status", "campaigns", ["status"])

def downgrade() -> None:
    op.drop_index("ix_campaigns_status", "campaigns")
```

**Время:** 1 час  
**Исполнитель:** belin

---

### P2.2 — IX2: Добавить индекс на payouts.status

**Файл:** `src/db/models/payout.py` (строка ~97)

**Было:**
```python
status: Mapped[PayoutStatus] = mapped_column(
    Enum(PayoutStatus),
    nullable=False,
    default=PayoutStatus.PENDING,
)
```

**Стало:**
```python
status: Mapped[PayoutStatus] = mapped_column(
    Enum(PayoutStatus),
    nullable=False,
    default=PayoutStatus.PENDING,
    index=True,  # ✅ Добавить
)
```

**Миграция:**
```bash
alembic revision -m "add_index_payouts_status"
```

**Содержимое миграции:**
```python
def upgrade() -> None:
    op.create_index("ix_payouts_status", "payouts", ["status"])

def downgrade() -> None:
    op.drop_index("ix_payouts_status", "payouts")
```

**Время:** 1 час  
**Исполнитель:** belin

---

## 📊 ГРАФИК ВЫПОЛНЕНИЯ

| Неделя | Задачи | Исполнитель | Часы |
|--------|--------|-------------|------|
| **Неделя 1 (P0)** | P0.1 | belin | 4 |
| **Неделя 2 (P1)** | P1.1, P1.2, P1.3, P1.4 | belin | 5 |
| **Неделя 3 (P2)** | P2.1, P2.2 | belin | 2 |
| **ИТОГО** | **7 задач** | | **11 часов** |

---

## ✅ КРИТЕРИИ ПРИЁМКИ

### Для каждой задачи:

1. **Код изменён** согласно спецификации
2. **Миграция создана** и протестирована
3. **Миграция применена** к test БД
4. **Ruff + MyPy** проверки проходят
5. **Git commit** с описанием
6. **PR создан** и approved

### Финальная проверка:

```bash
# Проверить Alembic
alembic current          # Должна быть последняя revision
alembic history          # Показать всю историю

# Проверить constraints в БД
docker compose exec postgres psql -U market_bot -d market_bot_db -c "
    SELECT conname, contype FROM pg_constraint 
    WHERE conname LIKE 'ck_%' 
    ORDER BY conname;
"

# Проверить индексы
docker compose exec postgres psql -U market_bot -d market_bot_db -c "
    SELECT indexname, tablename FROM pg_indexes 
    WHERE tablename IN ('campaigns', 'payouts') 
    AND indexname LIKE 'ix_%'
    ORDER BY tablename, indexname;
"

# Запустить тесты
make test

# Проверить линтеры
make lint
```

---

## 📝 ШАБЛОН GIT COMMIT

```bash
git commit -m "feat(db): add CheckConstraint for users.credits and balance

P1.1 — CC1: Отсутствие проверки на положительные значения

Проблема:
- credits и balance могли быть отрицательными
- Нет защиты на уровне БД

Изменения:
- src/db/models/user.py: добавить CheckConstraint
- alembic/versions/002_add_check_constraints_users.py

Результат:
- ✅ credits >= 0 гарантировано БД
- ✅ balance >= 0 гарантировано БД
- ✅ Ruff check: All checks passed
- ✅ MyPy: Success

Fixes: docs/audit/FIX_PLAN.md P1.1"
```

---

## 📋 ЧЕКЛИСТ ЗАДАЧ

- [ ] **P0.1** Инициализировать Alembic
- [ ] **P0.1** Создать начальную миграцию
- [ ] **P0.1** Применить миграцию
- [ ] **P1.1** Добавить CheckConstraint для users.credits
- [ ] **P1.1** Добавить CheckConstraint для users.balance
- [ ] **P1.2** Добавить CheckConstraint для campaigns.cost
- [ ] **P1.3** Добавить CheckConstraint для transactions.amount
- [ ] **P1.4** Изменить campaigns.cost на nullable=False
- [ ] **P1.4** Изменить mailing_logs.cost на nullable=False
- [ ] **P2.1** Добавить индекс на campaigns.status
- [ ] **P2.2** Добавить индекс на payouts.status
- [ ] **Все** Применить все миграции
- [ ] **Все** Запустить тесты
- [ ] **Все** Запустить линтеры

---

**ПЛАН УТВЕРЖДЁН:** 2026-03-10  
**СЛЕДУЮЩИЙ АУДИТ:** После выполнения всех исправлений

---

**ИСПОЛНИТЕЛЬ:** Qwen Code  
**ФАЙЛ ПЛАНА:** `docs/audit/FIX_PLAN_DATABASE.md`
