# План объединения таблиц `chats` и `telegram_chats`

## Результаты анализа

### Текущее состояние

| Таблица | Записей | Статус |
|---------|---------|--------|
| `chats` | 0 | Пустая (production ready) |
| `telegram_chats` | 0 | Пустая (production ready) |
| `mailing_logs` | 0 | Есть FK на `chats.id` |
| `chat_snapshots` | 0 | Есть FK на `telegram_chats.id` |

**Вывод:** Обе таблицы пустые, миграция будет безболезненной.

---

### Поля таблицы `chats` (старая модель для mailing)

| Поле | Тип | Nullable | Описание | Есть в `telegram_chats`? |
|------|-----|----------|----------|-------------------------|
| id | Integer | NO | PK | ✅ Да |
| telegram_id | BigInteger | NO | Telegram ID (unique) | ✅ Да |
| title | String(500) | NO | Заголовок | ✅ Да |
| username | String(255) | YES | Username | ✅ Да |
| description | Text | YES | Описание | ✅ Да |
| member_count | Integer | NO | Участники | ❌ Нет (есть last_subscribers) |
| topic | String(100) | YES | Тематика | ✅ Да |
| is_active | Boolean | NO | Активен для рассылки | ✅ Да |
| is_verified | Boolean | NO | Проверен | ❌ Нет |
| is_scam | Boolean | NO | Scam флаг | ❌ Нет |
| is_fake | Boolean | NO | Fake флаг | ❌ Нет |
| is_broadcast | Boolean | NO | Канал (вещание) | ❌ Нет (есть chat_type) |
| rating | Float | NO | Рейтинг 0-10 | ❌ Нет |
| last_checked | DateTime | YES | Последняя проверка | ✅ Да (last_parsed_at) |
| last_message_date | DateTime | YES | Последнее сообщение | ❌ Нет |
| avg_post_reach | Integer | YES | Средний охват | ❌ Нет (есть last_avg_views) |
| posts_per_day | Float | NO | Постов в день | ❌ Нет (есть last_post_frequency) |
| error_count | Integer | NO | Счётчик ошибок | ❌ Нет (есть parse_error_count) |
| deactivate_reason | String(500) | YES | Причина деактивации | ❌ Нет |
| created_at | DateTime | NO | Создано | ✅ Да |
| updated_at | DateTime | NO | Обновлено | ✅ Да |

---

### Поля таблицы `telegram_chats` (новая модель для аналитики)

| Поле | Тип | Nullable | Описание | Есть в `chats`? |
|------|-----|----------|----------|-----------------|
| id | Integer | NO | PK | ✅ Да |
| username | String(255) | NO | Username (unique) | ✅ Да |
| telegram_id | BigInteger | YES | Telegram ID (unique) | ✅ Да |
| title | String(512) | YES | Заголовок | ✅ Да |
| description | Text | YES | Описание | ✅ Да |
| chat_type | Enum | NO | channel/group/supergroup | ❌ Нет (есть is_broadcast) |
| topic | String(100) | YES | Тематика | ✅ Да |
| is_active | Boolean | NO | Активен | ✅ Да |
| is_public | Boolean | NO | Публичный | ❌ Нет |
| can_post | Boolean | NO | Можно постить | ❌ Нет |
| last_subscribers | Integer | NO | Подписчики | ❌ Нет (есть member_count) |
| last_avg_views | Integer | NO | Средний охват | ❌ Нет (есть avg_post_reach) |
| last_er | Float | NO | Engagement Rate | ❌ Нет |
| last_post_frequency | Float | NO | Частота постов | ❌ Нет (есть posts_per_day) |
| last_parsed_at | DateTime | YES | Последняя проверка | ✅ Да (last_checked) |
| parse_error | Text | YES | Ошибка парсинга | ❌ Нет |
| parse_error_count | Integer | NO | Счётчик ошибок | ❌ Нет (есть error_count) |
| created_at | DateTime | NO | Создано | ✅ Да |
| updated_at | DateTime | NO | Обновлено | ✅ Да |

---

### Поля только в `chats` (нужно перенести в `telegram_chats`)

| Поле | Используется в | Критичность |
|------|----------------|-------------|
| member_count | `mailing_service.select_chats()` — фильтрация по аудитории | 🔴 Высокая |
| is_verified | Нигде не используется напрямую | 🟢 Низкая |
| is_scam | `Chat.is_eligible_for_mailing` property | 🟡 Средняя |
| is_fake | `Chat.is_eligible_for_mailing` property | 🟡 Средняя |
| is_broadcast | Нигде не используется | 🟢 Низкая |
| rating | `mailing_service.select_chats()` — сортировка | 🔴 Высокая |
| last_message_date | Нигде не используется | 🟢 Низкая |
| avg_post_reach | Нигде не используется напрямую | 🟢 Низкая |
| posts_per_day | Нигде не используется | 🟢 Низкая |
| error_count | `Chat.increment_error()`, `Chat.is_eligible_for_mailing` | 🟡 Средняя |
| deactivate_reason | Нигде не используется | 🟢 Низкая |

---

### Поля только в `telegram_chats` (уже есть, хорошо)

| Поле | Используется в | Критичность |
|------|----------------|-------------|
| chat_type | `ChatAnalyticsRepository` | 🔴 Высокая |
| is_public | Нигде не используется | 🟢 Низкая |
| can_post | `ChatAnalyticsRepository` | 🟡 Средняя |
| last_subscribers | `ChatAnalyticsRepository`, snapshots | 🔴 Высокая |
| last_avg_views | `ChatAnalyticsRepository` | 🔴 Высокая |
| last_er | `ChatAnalyticsRepository` | 🔴 Высокая |
| last_post_frequency | `ChatAnalyticsRepository` | 🟡 Средняя |
| parse_error | `ChatAnalyticsRepository.mark_parse_error()` | 🟡 Средняя |

---

## Зависимости которые нужно обновить

### Foreign Keys

| Таблица | Поле | Ссылается на | Что делать |
|---------|------|--------------|------------|
| `mailing_logs` | `chat_id` | `chats.id` (ON DELETE SET NULL) | Обновить FK на `telegram_chats.id` |
| `chat_snapshots` | `chat_id` | `telegram_chats.id` (ON DELETE CASCADE) | ✅ Уже правильно |

### Модели кода

| Файл | Текущий импорт | После merge |
|------|----------------|-------------|
| `src/db/models/__init__.py` | `from src.db.models.chat import Chat` | Удалить импорт Chat |
| `src/db/models/mailing_log.py` | `from src.db.models.chat import Chat` | `from src.db.models.analytics import TelegramChat` |
| `src/db/repositories/__init__.py` | `from src.db.repositories.chat_repo import ChatRepository` | Удалить |
| `src/db/repositories/chat_repo.py` | `from src.db.models.chat import Chat` | **Удалить файл** |
| `src/db/repositories/log_repo.py` | `from src.db.models.chat import Chat` | `from src.db.models.analytics import TelegramChat` |
| `src/core/services/mailing_service.py` | `from src.db.repositories.chat_repo import ChatRepository` | Использовать `ChatAnalyticsRepository` |
| `src/tasks/parser_tasks.py` | `from src.db.repositories.chat_repo import ChatRepository` | Использовать `ChatAnalyticsRepository` |
| `src/tasks/parser_tasks.py` | `from src.db.repositories.chat_analytics import ChatAnalyticsRepository` | ✅ Оставить |
| `src/utils/telegram/parser.py` | Не проверялось | Проверить импорты |

---

## Выбранная стратегия

### ✅ Вариант A: Расширить `telegram_chats` полями из `chats`, удалить `chats`

**Обоснование:**
1. `telegram_chats` — более новая и продуманная модель
2. Уже используется в `ChatAnalyticsRepository` и парсере
3. `chat_snapshots` уже ссылается на `telegram_chats`
4. Таблицы пустые — миграция без данных
5. `chats` используется только в mailing, но не в аналитике

---

## Рекомендуемый вариант: A

### Что делаем:

1. **Добавляем в `telegram_chats` недостающие поля из `chats`:**
   - `member_count` (Integer, default=0) — для фильтрации в mailing
   - `rating` (Float, default=5.0) — для сортировки в mailing
   - `is_scam` (Boolean, default=False) — для фильтрации
   - `is_fake` (Boolean, default=False) — для фильтрации
   - `error_count` (Integer, default=0) — для деактивации
   - `deactivate_reason` (String, nullable) — для отладки

2. **Обновляем FK в `mailing_logs`:**
   - `chat_id` → `telegram_chats.id` (ON DELETE SET NULL)
   - `chat_telegram_id` → оставляем для истории

3. **Обновляем `ChatAnalyticsRepository`:**
   - Добавить метод `get_active_filtered()` (аналог из `ChatRepository`)
   - Добавить метод `select_chats_for_mailing()` с фильтрами

4. **Удаляем:**
   - `src/db/models/chat.py`
   - `src/db/repositories/chat_repo.py`

5. **Обновляем импорты:**
   - Везде где `Chat` → `TelegramChat`
   - Везде где `ChatRepository` → `ChatAnalyticsRepository`

---

## Шаги миграции (для фазы 2)

### Шаг 1: Alembic миграция

```python
# migration file
def upgrade():
    # 1. Добавить поля в telegram_chats
    op.add_column('telegram_chats', sa.Column('member_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('telegram_chats', sa.Column('rating', sa.Float(), nullable=False, server_default='5.0'))
    op.add_column('telegram_chats', sa.Column('is_scam', sa.Boolean(), nullable=False, server_default=False))
    op.add_column('telegram_chats', sa.Column('is_fake', sa.Boolean(), nullable=False, server_default=False))
    op.add_column('telegram_chats', sa.Column('error_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('telegram_chats', sa.Column('deactivate_reason', sa.String(500), nullable=True))
    
    # 2. Создать индексы для mailing
    op.create_index('ix_telegram_chats_member_count', 'telegram_chats', ['member_count'])
    op.create_index('ix_telegram_chats_rating', 'telegram_chats', ['rating'])
    op.create_index('ix_telegram_chats_topic_active', 'telegram_chats', ['topic', 'is_active'])
    
    # 3. Обновить FK в mailing_logs
    op.drop_constraint('mailing_logs_chat_id_fkey', 'mailing_logs', type_='foreignkey')
    op.create_foreign_key(
        'mailing_logs_chat_id_fkey',
        'mailing_logs', 'telegram_chats',
        ['chat_id'], ['id'],
        ondelete='SET NULL'
    )
    
    # 4. Удалить таблицу chats
    op.drop_table('chats')

def downgrade():
    # 1. Создать chats обратно
    op.create_table('chats', ...)
    
    # 2. Вернуть FK в mailing_logs
    op.drop_constraint('mailing_logs_chat_id_fkey', 'mailing_logs', type_='foreignkey')
    op.create_foreign_key('mailing_logs_chat_id_fkey', 'mailing_logs', 'chats', ['chat_id'], ['id'], ondelete='SET NULL')
    
    # 3. Удалить добавленные поля из telegram_chats
    op.drop_column('telegram_chats', 'deactivate_reason')
    op.drop_column('telegram_chats', 'error_count')
    op.drop_column('telegram_chats', 'is_fake')
    op.drop_column('telegram_chats', 'is_scam')
    op.drop_column('telegram_chats', 'rating')
    op.drop_column('telegram_chats', 'member_count')
```

---

### Шаг 2: Обновить модели

**Удалить:**
- `src/db/models/chat.py`

**Обновить:**
- `src/db/models/__init__.py` — удалить `from src.db.models.chat import Chat`
- `src/db/models/mailing_log.py` — заменить `from src.db.models.chat import Chat` на `from src.db.models.analytics import TelegramChat`

**Обновить `src/db/models/analytics.py`:**
- Добавить новые поля в `TelegramChat`
- Добавить property `is_eligible_for_mailing`
- Добавить методы `increment_error()`, `mark_checked()`

---

### Шаг 3: Обновить репозитории

**Удалить:**
- `src/db/repositories/chat_repo.py`
- Обновить `src/db/repositories/__init__.py` — удалить импорт `ChatRepository`

**Обновить `src/db/repositories/chat_analytics.py`:**
- Добавить метод `get_active_filtered()` (фильтры для mailing)
- Добавить метод `select_chats_for_mailing()` (выборка для кампании)

**Обновить `src/db/repositories/log_repo.py`:**
- Заменить `from src.db.models.chat import Chat` на `from src.db.models.analytics import TelegramChat`
- Обновить запросы с `Chat.telegram_id` на `TelegramChat.telegram_id`

---

### Шаг 4: Обновить код

| Файл | Изменения |
|------|-----------|
| `src/core/services/mailing_service.py` | Заменить `ChatRepository` на `ChatAnalyticsRepository` |
| `src/tasks/parser_tasks.py` | Заменить `ChatRepository` на `ChatAnalyticsRepository`, удалить импорт `ChatData` |
| `src/utils/telegram/parser.py` | Проверить импорты |
| `src/utils/telegram/topic_classifier.py` | Проверить импорты |

---

## Оценка риска

| Параметр | Значение |
|----------|----------|
| Затронуто таблиц с данными | 2 (`chats`, `mailing_logs`) |
| Затронуто файлов кода | 9 |
| Требует даунтайма | ❌ Нет (таблицы пустые) |
| Откат возможен | ✅ Да (через `alembic downgrade`) |
| Влияние на production | 🟢 Минимальное (таблицы пустые) |

---

## Что НЕ меняем в этой задаче

- ✅ `chat_snapshots` — остаётся, уже ссылается на `telegram_chats`
- ✅ `ChatAnalyticsRepository` — расширяем методами для mailing
- ✅ `ChatType` enum — остаётся
- ✅ `chat_telegram_id` в `mailing_logs` — остаётся для истории

---

## Финальный чеклист перед выполнением

- [ ] Таблицы пустые (проверить `SELECT COUNT(*)`)
- [ ] Нет активных кампаний в статусе `running`
- [ ] Есть backup БД (на всякий случай)
- [ ] Все тесты проходят (`make test`)
- [ ] Ruff и mypy проходят (`make lint`)

---

## После выполнения

1. Закоммитить миграцию
2. Обновить документацию
3. Запустить `alembic upgrade head`
4. Проверить что парсер и mailing работают
5. Запустить тесты
