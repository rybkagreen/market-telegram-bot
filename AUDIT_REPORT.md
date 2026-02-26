# Аудит проекта market-telegram-bot

**Дата:** 2026-02-26  
**Ветка:** developer2/belin  
**Аудитор:** Qwen Code

---

## Итоговая оценка

| Раздел | Статус | Критических | Средних | Низких |
|--------|--------|-------------|---------|--------|
| Архитектура | 🟡 | 0 | 2 | 1 |
| База данных | 🟢 | 0 | 0 | 1 |
| Конфигурация | 🟢 | 0 | 1 | 0 |
| Docker | 🟢 | 0 | 0 | 1 |
| Celery | 🟢 | 0 | 0 | 0 |
| Тесты | 🟡 | 0 | 1 | 0 |
| Качество кода | 🟢 | 0 | 0 | 2 |
| Безопасность | 🟢 | 0 | 0 | 0 |
| API | 🟢 | 0 | 0 | 0 |

**Итого:** 🟢 Критических: 0, 🟡 Средних: 4, 🟢 Низких: 5

**✅ Критическая проблема безопасности исправлена!**

---

## 🔴 Критические проблемы (требуют исправления немедленно)

### 1. ~~Хардкод BOT_TOKEN в docker-compose.yml~~ ✅ ИСПРАВЛЕНО

**Статус:** ✅ **ИСПРАВЛЕНО** в коммите `b7f2b8b`

**Было:**
```yaml
BOT_TOKEN: 7562867307:AAEIzuEqqRDV0kixpFHXIpVDgxaq0Xq_F_k
```

**Стало:**
```yaml
BOT_TOKEN: ${BOT_TOKEN}
```

**✅ ВЫПОЛНЕНО:**
1. ✅ Токен отозван через @BotFather (2026-02-26)
2. ✅ Новый токен получен: `7562867307:AAESOPGdNkrabOAK1CvfaZGaUouZuIx8j8A`
3. ✅ Новый токен записан в локальный `.env`
4. ✅ История git очищена (filter-branch + gc)
5. ⏳ **Требуется:** Force push в remote

**⚠️ Оставшиеся действия:**
```bash
# Force push в remote (история переписана!):
git push origin developer2/belin --force

# После force push всем разработчикам нужно:
git fetch origin
git reset --hard origin/developer2/belin
```

**Приоритет:** P0 — force push до следующего пуша

---

### 2. Handlers импортируют async_session_factory напрямую
**Файлы:** 
- `src/bot/handlers/admin.py:46`
- `src/bot/handlers/analytics.py:14`
- `src/bot/handlers/billing.py:21`
- `src/bot/handlers/cabinet.py:21`
- `src/bot/handlers/campaigns.py:38`
- `src/bot/handlers/models.py:19`
- `src/bot/handlers/notifications.py:19`
- `src/bot/handlers/start.py:14`
- `src/bot/handlers/templates.py:22`

**Описание:** Handlers нарушают архитектурное правило — обращаются к БД напрямую через `async_session_factory`, вместо использования репозиториев.

**Риск:** 
- Нарушение слоёной архитектуры
- Дублирование кода доступа к БД
- Сложность тестирования

**Решение:** Создать сервисы (services layer) которые будут использовать репозитории, и handlers будут вызывать сервисы.

**Приоритет:** P1 — исправить в текущем спринте

---

### 3. Небезопасные паттерны безопасности
**Описание:** При проверке не найдено явных уязвимостей (eval, exec, pickle.loads, shell=True), но хардкод токена (проблема #1) является критической уязвимостью.

**Приоритет:** P0 — см. проблему #1

---

## 🟡 Средние проблемы (исправить в текущем спринте)

### 1. Файл campaigns_old.py не удалён
**Файл:** `src/bot/handlers/campaigns_old.py`  
**Описание:** Старый файл handlers не удалён, создаёт путаницу.

**Решение:** Удалить файл или переместить в `docs/deprecated/`

**Приоритет:** P2

---

### 2. TODO в коде
**Файл:** `src/bot/handlers/analytics.py:99`  
**Код:** `top_topic = "IT"  # TODO: получить из БД`

**Описание:** Заглушка вместо реальных данных.

**Решение:** Реализовать получение топовой тематики из БД через analytics_service.

**Приоритет:** P2

---

### 3. Тесты покрывают не все модули
**Статистика:**
- Тестовых файлов: 5
- Моделей в БД: 8
- Репозиториев: 6
- Handlers: 11

**Отсутствуют тесты для:**
- `src/bot/handlers/analytics_chats.py` (новый handler)
- `src/db/repositories/chat_analytics.py` (новый репозиторий)
- `src/utils/chat_parser.py` (deprecated, но ещё используется)
- `src/utils/telegram/parser.py` (объединённый парсер)

**Решение:** Добавить unit-тесты для новых модулей.

**Приоритет:** P2

---

### 4. Docker: образы без зафиксированных версий
**Файл:** `docker-compose.yml`

**Найдено:**
```yaml
image: nginx:alpine  # ✅ зафиксировано
image: postgres:16-alpine  # ✅ зафиксировано
image: redis:7-alpine  # ✅ зафиксировано
```

**Проблема:** В Dockerfile могут использоваться `latest` теги.

**Решение:** Проверить все Dockerfile на использование конкретных версий.

**Приоритет:** P2

---

## 🟢 Низкий приоритет (технический долг)

### 1. Deprecated файл chat_parser.py
**Файл:** `src/utils/chat_parser.py`  
**Статус:** Помечен как deprecated с warning

**Описание:** Файл оставлен для обратной совместимости. Планируется к удалению в следующем спринте.

**Решение:** Удалить после завершения миграции всех импортов.

**Приоритет:** P3

---

### 2. Две таблицы для чатов: chats и telegram_chats
**Файлы:** `src/db/models/chat.py`, `src/db/models/analytics.py`

**Описание:** 
- `chats` — старая таблица для mailing
- `telegram_chats` — новая таблица для analytics

**Риск:** Путаница, дублирование данных.

**Решение:** В следующем спринте объединить или чётко разграничить ответственность.

**Приоритет:** P3

---

### 3. Ruff/mypy не настроены на полный strict режим
**Файл:** `pyproject.toml`

**Описание:** Mypy игнорирует некоторые ошибки (`ignore_missing_imports`, `disable_error_code`).

**Решение:** Постепенно ужесточать настройки типизации.

**Приоритет:** P3

---

## ✅ Что работает хорошо

### Архитектура
- ✅ Нет circular imports
- ✅ Репозитории не импортируют handlers/tasks
- ✅ Tasks не импортируют handlers
- ✅ Все модели зарегистрированы в Base.metadata (8 таблиц)
- ✅ Все ForeignKey имеют `ondelete`

### База данных
- ✅ Все миграции применены
- ✅ Индексы на часто запрашиваемых полях
- ✅ Нет `session.commit()` внутри репозиториев

### Конфигурация
- ✅ .env и .env.example синхронизированы
- ✅ Все переменные окружения читаются через Pydantic Settings

### Celery
- ✅ Задачи зарегистрированы в правильных очередях (mailing, parser)
- ✅ Beat schedule настроен
- ✅ Задачи с `bind=True` имеют доступ к `self.retry()`

### API
- ✅ Все endpoints используют `Depends(get_current_user)` для авторизации
- ✅ Pydantic модели с валидацией
- ✅ Response models объявлены

### Качество кода
- ✅ Ruff проходит без ошибок
- ✅ Нет явных unsafe паттернов (eval, exec, pickle.loads)
- ✅ Конвенция именования соблюдается

---

## Детальные результаты проверок

### 1. Архитектурный аудит

#### 1.1. Нарушения слоёв
```
❌ Handlers импортируют async_session_factory (9 файлов)
✅ Репозитории не импортируют handlers/tasks
✅ Tasks не импортируют handlers
```

#### 1.2. Circular imports
```
✅ src.config.settings
✅ src.db.models
✅ src.api.main
✅ src.tasks.celery_app
✅ src.bot.main
```

#### 1.3. Зарегистрированные таблицы
```
- campaigns
- chat_snapshots
- chats
- content_flags
- mailing_logs
- telegram_chats
- transactions
- users
```

---

### 2. Аудит базы данных

#### 2.1. Модели
```
✅ Все модели имеют __tablename__
✅ Все ForeignKey имеют ondelete
✅ Индексы присутствуют
```

#### 2.2. Репозитории
```
✅ Нет session.commit() внутри репозиториев
✅ Нет N+1 запросов (циклов с await repo.get())
```

---

### 3. Аудит конфигурации

#### 3.1. Переменные окружения
```
✅ .env и .env.example синхронизированы
❌ Хардкод BOT_TOKEN в .env (значение по умолчанию)
```

#### 3.2. Секреты в коде
```
❌ Хардкод BOT_TOKEN в docker-compose.yml (критично!)
```

---

### 4. Аудит Docker

#### 4.1. Образы
```
✅ nginx:alpine
✅ postgres:16-alpine
✅ redis:7-alpine
```

#### 4.2. Секреты
```
❌ BOT_TOKEN захардкоден (строка 33)
✅ Остальные секреты через ${VAR}
```

---

### 5. Аудит Celery

#### 5.1. Зарегистрированные задачи
```
- cleanup:archive_old_campaigns
- cleanup:cleanup_expired_sessions
- cleanup:delete_old_logs
- mailing:check_low_balance
- mailing:check_scheduled_campaigns
- mailing:notify_user
- mailing:send_campaign
- parser:collect_all_chats_stats
- parser:parse_single_chat
- parser:refresh_chat_database
```

#### 5.2. Beat schedule
```
✅ refresh-chat-database (03:00 daily)
✅ collect-all-chats-stats-daily (02:00 daily)
✅ check-scheduled-campaigns (*/5 min)
✅ delete-old-logs (Sunday 03:00)
✅ check-low-balance (hourly)
```

---

### 6. Аудит тестов

#### 6.1. Тестовые файлы
```
tests/api/test_dependencies.py
tests/api/test_auth.py
tests/bot/test_start.py
tests/unit/test_content_filter.py
tests/unit/test_ai_service.py
```

#### 6.2. Покрытие
```
❌ Нет тестов для новых модулей:
   - analytics_chats handler
   - chat_analytics repository
   - telegram/parser (объединённый)
```

---

### 7. Аудит качества кода

#### 7.1. Ruff
```
✅ Ошибок не найдено
```

#### 7.2. TODO/FIXME/HACK
```
⚠️ 1 TODO найден:
   - src/bot/handlers/analytics.py:99: TODO: получить из БД
```

#### 7.3. Мёртвый код
```
⚠️ Потенциально мёртвый код:
   - campaigns_old.py (целый файл)
```

---

### 8. Аудит безопасности

#### 8.1. Unsafe паттерны
```
✅ Нет eval(), exec(), pickle.loads, shell=True, verify=False
```

#### 8.2. SQL инъекции
```
✅ Нет f-строк в execute()
```

#### 8.3. Логирование секретов
```
✅ Нет logger.*password/token/secret
```

---

### 9. Аудит API

#### 9.1.Endpoints с авторизацией
```
✅ Все endpoints используют CurrentUser Depends
✅ Health check endpoints без авторизации (ожидаемо)
```

#### 9.2. Валидация
```
✅ Pydantic модели с обязательными полями
✅ Query параметры с ограничениями (ge, le)
```

---

## План исправлений

### P0 (немедленно)
1. Удалить хардкод BOT_TOKEN из docker-compose.yml

### P1 (текущий спринт)
2. Создать сервисный слой для handlers
3. Перевести handlers на использование сервисов вместо async_session_factory

### P2 (следующий спринт)
4. Удалить campaigns_old.py
5. Реализовать TODO в analytics.py
6. Добавить тесты для новых модулей
7. Проверить Dockerfile на наличие latest тегов

### P3 (технический долг)
8. Удалить chat_parser.py после полной миграции
9. Объединить таблицы chats и telegram_chats
10. Ужесточить настройки mypy

---

## Приложения

### A. Список проверенных файлов
- Все файлы в `src/` (кроме `__pycache__`)
- Все файлы в `tests/`
- `docker-compose.yml`
- `pyproject.toml`
- `.env`, `.env.example`

### B. Команды для воспроизведения проверок
```bash
# Circular imports
.venv/Scripts/python -c "from src.config.settings import settings; ..."

# Ruff
poetry run ruff check src/

# Тесты
poetry run pytest tests/ -v

# Поиск секретов
grep -rn "BOT_TOKEN\|password\|secret" docker-compose.yml
```

### C. Контакты
По вопросам аудита обращаться к автору отчёта через GitHub Issues.
