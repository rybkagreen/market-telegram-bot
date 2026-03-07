# Проблемы с миграциями Alembic — Отчёт

**Дата:** 2026-03-07  
**Статус:** ✅ **РЕШЕНО** — миграции успешно применены

---

## Решение применено

**Вариант:** A (Исправление существующих миграций)

**Изменения:**
1. ✅ Исправлен `down_revision` в `b377ebf742bf` → `20260307_170000`
2. ✅ Исправлен `down_revision` в `20260307_180000` → `b377ebf742bf`
3. ✅ Добавлена проверка существования индексов перед `drop_index`
4. ✅ Добавлена проверка существования колонки перед `add_column`
5. ✅ Удалена операция `ALTER TYPE campaignstatus` (ENUM не существует)
6. ✅ Удалена конфликтная merge миграция
7. ✅ Очищена таблица `alembic_version` от orphaned записей

**Результат:**
```
$ alembic heads
20260307_180000 (head)

$ alembic current
20260307_180000 (head)
```

**Новые поля в БД:**
- `telegram_chats.max_posts_per_day` (INTEGER, default=2)
- `telegram_chats.approval_mode` (VARCHAR(20), default='auto')
- `mailing_logs.rejection_reason` (VARCHAR(50), nullable)
- `mailing_logs.auto_approve_notified` (BOOLEAN, default=false)

---

---

## Краткое описание

При попытке применить миграции Alembic к базе данных обнаружены проблемы с историей миграций — присутствуют **несколько независимых веток (heads)** которые не объединены в единую цепочку.

---

## Текущее состояние

### Файлы миграций:

```
src/db/migrations/versions/
├── 20260307_170000_add_gamification_fields_and_badge_models.py  (head #1)
├── 20260307_180000_add_channel_settings_and_placement_fields.py (head #2)
└── 20260303_202239_b377ebf742bf_add_notifications_enabled_to_users.py (orphan)
```

### Состояние БД (alembic_version):

```
version_num
-----------------
20260307_170000
```

### Alembic heads:

```
b377ebf742bf (head)
20260307_180000 (head)
```

---

## Проблема #1: Раздвоенная история миграций

### Описание:

Миграция `b377ebf742bf` (от 2026-03-03) имеет `down_revision = "96d841a6c242"`, что создаёт **отдельную ветку** которая не связана с основной цепочкой миграций.

### Ожидаемая цепочка:

```
... → 20260307_160000 → 20260307_170000 → 20260307_180000 (HEAD)
```

### Фактическая ситуация:

```
... → 20260307_160000 → 20260307_170000 (HEAD #1)
                      ↘
                       96d841a6c242 → b377ebf742bf (HEAD #2)
```

### Причина:

Миграция `b377ebf742bf` была создана **до** того как были добавлены миграции `20260307_160000` и `20260307_170000`, но её `down_revision` не был обновлён.

---

## Проблема #2: Миграция пытается удалить несуществующий индекс

### Файл:
`src/db/migrations/versions/20260303_202239_b377ebf742bf_add_notifications_enabled_to_users.py`

### Ошибка:

```sql
ERROR: index "ix_telegram_chats_language" does not exist
```

### Причина:

Миграция содержит `op.drop_index("ix_telegram_chats_language")` но этот индекс **никогда не создавался** в предыдущих миграциях.

### Решение:

Нужно обновить миграцию чтобы она проверяла существование индекса перед удалением:

```python
# Было:
op.drop_index(op.f("ix_telegram_chats_language"), table_name="telegram_chats")

# Стало:
from sqlalchemy import inspect

inspector = inspect(op.get_bind())
has_index = any(
    idx["name"] == "ix_telegram_chats_language"
    for idx in inspector.get_indexes("telegram_chats")
)
if has_index:
    op.drop_index(op.f("ix_telegram_chats_language"), table_name="telegram_chats")
```

---

## Проблема #3: ENUM campaignstatus не существует

### Файл:
`src/db/migrations/versions/20260307_180000_add_channel_settings_and_placement_fields.py`

### Ошибка:

```sql
ERROR: type "campaignstatus" does not exist
```

### Причина:

В модели `Campaign` поле `status` определено как `String(50)` а не как `Enum(CampaignStatus)`. Поэтому ENUM тип `campaignstatus` **не был создан** в БД.

### Решение:

Удалить строку из миграции:

```python
# УДАЛИТЬ:
op.execute("ALTER TYPE campaignstatus ADD VALUE IF NOT EXISTS 'changes_requested'")
```

Статус `changes_requested` будет просто строкой в столбце VARCHAR.

---

## Проблема #4: Merge миграция создаёт конфликт

### Файл:
`src/db/migrations/versions/20260307_202346_5cf77060a1de_merge_b377ebf_into_main_branch.py`

### Ошибка:

```
ERROR: Requested revision b377ebf742bf overlaps with other requested revisions 20260307_170000
```

### Причина:

Alembic merge создал миграцию которая пытается объединить две ветки, но поскольку `b377ebf742bf` уже была применена к БД (через INSERT), alembic видит конфликт.

### Решение:

1. Удалить merge миграцию
2. Вручную исправить `down_revision` в `b377ebf742bf` чтобы указывал на `20260307_170000`
3. Очистить alembic_version и применить заново

---

## План действий

### Вариант A: Исправить существующие миграции (рекомендуется)

1. **Обновить `b377ebf742bf`:**
   ```python
   down_revision: str | None = "20260307_170000"  # Было: "96d841a6c242"
   ```

2. **Исправить drop_index в `b377ebf742bf`:**
   ```python
   # Добавить проверку существования индекса
   ```

3. **Удалить merge миграцию:**
   ```bash
   rm src/db/migrations/versions/*merge_b377ebf*.py
   ```

4. **Очистить БД:**
   ```sql
   DELETE FROM alembic_version WHERE version_num = 'b377ebf742bf';
   ```

5. **Применить миграции:**
   ```bash
   docker compose exec bot alembic upgrade head
   ```

### Вариант B: Создать новую миграцию с нуля

1. Удалить все миграции после `20260307_170000`
2. Создать новую миграцию:
   ```bash
   alembic revision -m "add_all_sprint5_changes"
   ```
3. Вручную прописать все изменения в `upgrade()`
4. Применить миграцию

### Вариант C: Применить изменения вручную через SQL

1. Выполнить SQL напрямую:
   ```sql
   ALTER TABLE telegram_chats ADD COLUMN max_posts_per_day INTEGER DEFAULT 2 NOT NULL;
   ALTER TABLE telegram_chats ADD COLUMN approval_mode VARCHAR(20) DEFAULT 'auto' NOT NULL;
   ALTER TABLE mailing_logs ADD COLUMN rejection_reason VARCHAR(50);
   ALTER TABLE mailing_logs ADD COLUMN auto_approve_notified BOOLEAN DEFAULT FALSE NOT NULL;
   ```
2. Обновить alembic_version:
   ```sql
   INSERT INTO alembic_version (version_num) VALUES ('20260307_180000');
   ```

---

## Файлы которые требуют изменений

| Файл | Изменения |
|------|-----------|
| `src/db/migrations/versions/20260303_202239_b377ebf742bf_add_notifications_enabled_to_users.py` | Обновить `down_revision`, исправить `drop_index` |
| `src/db/migrations/versions/20260307_180000_add_channel_settings_and_placement_fields.py` | Удалить `ALTER TYPE campaignstatus` |
| `src/db/migrations/versions/*merge_b377ebf*.py` | **УДАЛИТЬ** |

---

## Команда для проверки состояния

```bash
# Проверить heads
docker compose exec bot alembic heads

# Проверить текущую версию в БД
docker compose exec postgres psql -U market_bot -d market_bot_db -c "SELECT * FROM alembic_version;"

# Проверить зависимости
docker compose exec bot alembic current --verbose

# Показать дерево миграций
docker compose exec bot alembic history --verbose
```

---

## Примечания

1. **Не применяйте миграции повторно** пока проблема не будет решена — это может привести к повреждению схемы БД.

2. **Сделайте backup БД** перед любыми изменениями:
   ```bash
   docker compose exec postgres pg_dump -U market_bot market_bot_db > backup_$(date +%Y%m%d_%H%M%S).sql
   ```

3. **После исправления** проверьте что все таблицы имеют правильную структуру:
   ```bash
   docker compose exec postgres psql -U market_bot -d market_bot_db -c "\d telegram_chats"
   docker compose exec postgres psql -U market_bot -d market_bot_db -c "\d mailing_logs"
   ```

---

**Статус:** ⏸️ Ожидает решения от разработчика
