# Test Mode Guide для Администраторов

**Версия:** 1.0  
**Дата:** 2026-03-19  
**Статус:** Production Ready

---

## Обзор

Test Mode (Тестовый режим) позволяет администраторам платформы:

1. **Добавлять тестовые каналы** с любым количеством подписчиков (даже < 100)
2. **Создавать тестовые кампании** без оплаты и без влияния на реальную статистику
3. **Тестировать полный функционал** биржи без финансовых операций

---

## Как Добавить Тестовый Канал

### Через Mini App (UI)

1. Откройте Mini App → Владелец → Добавить канал
2. Введите username или chat_id канала
3. Нажмите "🔍 Проверить канал"
4. **Только для админов:** Появится переключатель "🧪 Тестовый канал"
5. Включите тестовый режим
6. Нажмите "➕ Добавить канал"

### Через API

```bash
curl -X POST https://app.rekharbor.ru/api/channels/ \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "test_channel",
    "is_test": true
  }'
```

**Ответ:**
```json
{
  "id": 123,
  "username": "test_channel",
  "is_test": true,
  "member_count": 50
}
```

---

## Как Создать Тестовую Кампанию

### Через Mini App (UI)

1. Откройте Mini App → Рекламодатель → Создать кампанию
2. Выберите канал (включая тестовые)
3. На этапе оплаты **только для админов:** Появится переключатель "🧪 Тестовая кампания"
4. Включите тестовый режим
5. Блок оплаты скроется, появится уведомление
6. Завершите создание кампании

### Через API

```bash
curl -X POST https://app.rekharbor.ru/api/placements/ \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "channel_id": 123,
    "publication_format": "post_24h",
    "ad_text": "Тестовая реклама",
    "proposed_price": "1000",
    "proposed_schedule": "2026-03-20T14:00:00Z",
    "is_test": true,
    "test_label": "Тестирование функционала"
  }'
```

**Ответ:**
```json
{
  "id": 456,
  "status": "test_pending",
  "is_test": true,
  "test_label": "Тестирование функционала",
  "final_price": null
}
```

---

## Ограничения Test Mode

### Что НЕ делают тестовые кампании:

- ❌ **Не списывают средства** с баланса рекламодателя
- ❌ **Не начисляют доход** владельцу канала
- ❌ **Не влияют на статистику** (earnings, spent, publications count)
- ❌ **Не отображаются в публичной статистике** по умолчанию
- ❌ **Не создают реальные платежи** через YooKassa

### Что делают тестовые кампании:

- ✅ **Создают запись в БД** с флагом `is_test=True`
- ✅ **Проходят полный workflow** (accept → publish → complete)
- ✅ **Публикуют посты** в Telegram канале (если бот имеет права)
- ✅ **Записывают статистику** (clicks, reach) — но не влияют на общую
- ✅ **Можно открыть диспут** (для тестирования функционала)

---

## Визуальные Индикаторы

Тестовые элементы помечены специальным бейджем:

```
┌─────────────────────────────────┐
│ 🧪 ТЕСТ                         │
│ Канал: @test_channel            │
│ Подписчики: 50                  │
└─────────────────────────────────┘
```

**Цвет:** Жёлтый/оранжевый (warning)  
**Текст:** "ТЕСТ" или кастомная пометка из `test_label`

---

## API Параметры

### POST /api/channels/

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|--------------|----------|
| `username` | string | — | Username канала |
| `is_test` | boolean | `false` | **Только для админов** |

### POST /api/placements/

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|--------------|----------|
| `channel_id` | integer | — | ID канала |
| `publication_format` | string | `"post_24h"` | Формат публикации |
| `ad_text` | string | — | Текст рекламы |
| `proposed_price` | string | — | Предлагаемая цена |
| `is_test` | boolean | `false` | **Только для админов** |
| `test_label` | string | `null` | Пометка теста (max 64 символа) |

### GET /api/placements/

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|--------------|----------|
| `include_test` | boolean | `false` | **Только для админов** — включить тестовые кампании |

---

## Примеры Использования

### 1. Тестирование Добавления Канала

```bash
# Админ добавляет тестовый канал с 10 подписчиками
curl -X POST https://app.rekharbor.ru/api/channels/ \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -d '{"username": "my_test_channel", "is_test": true}'

# ✅ Успешно (обычных пользователей заблокировало бы MIN_SUBSCRIBERS=100)
```

### 2. Тестирование Полного Воркфлоу Кампании

```bash
# 1. Создать тестовую кампанию
curl -X POST https://app.rekharbor.ru/api/placements/ \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -d '{
    "channel_id": 123,
    "is_test": true,
    "test_label": "QA Testing",
    ...
  }'

# 2. Принять кампанию (владелец)
curl -X POST https://app.rekharbor.ru/api/placements/456/accept \
  -H "Authorization: Bearer <OWNER_TOKEN>"

# 3. Опубликовать (Celery task)
# Автоматически через Celery

# 4. Проверить статистику
curl https://app.rekharbor.ru/api/analytics/owner \
  -H "Authorization: Bearer <OWNER_TOKEN>"
# Тестовые кампании НЕ включены в общую статистику
```

### 3. Просмотр Тестовых Кампаний

```bash
# Без include_test — тестовые скрыты
curl https://app.rekharbor.ru/api/placements/ \
  -H "Authorization: Bearer <ADMIN_TOKEN>"

# С include_test — тестовые включены
curl "https://app.rekharbor.ru/api/placements/?include_test=true" \
  -H "Authorization: Bearer <ADMIN_TOKEN>"
```

---

## Чеклист Тестирования

### Перед Деплоем

- [ ] Миграция применена (`alembic upgrade head`)
- [ ] Backend собран без ошибок
- [ ] Frontend собран без ошибок
- [ ] Все контейнеры запущены

### Функциональное Тестирование

#### Каналы
- [ ] Админ может добавить канал с < 100 подписчиками
- [ ] Не админ НЕ может добавить канал с < 100 подписчиками
- [ ] Тестовый канал помечен бейджем "ТЕСТ"
- [ ] Тестовый канал не влияет на общую статистику

#### Кампании
- [ ] Админ может создать тестовую кампанию без оплаты
- [ ] Не админ НЕ может создать тестовую кампанию
- [ ] Тестовая кампания проходит полный workflow
- [ ] Тестовая кампания не влияет на баланс
- [ ] Тестовая кампания не влияет на earnings/spent

#### UI
- [ ] Toggle "Тестовый канал" виден только админам
- [ ] Toggle "Тестовая кампания" виден только админам
- [ ] TestModeBadge отображается на тестовых элементах
- [ ] Предупреждения показываются при включении тестового режима

#### API
- [ ] `POST /api/channels/?is_test=true` работает для админов
- [ ] `POST /api/placements/?is_test=true` работает для админов
- [ ] `GET /api/placements/?include_test=true` возвращает тестовые
- [ ] Безопасность: не админы не могут создать тестовые

---

## Безопасность

### Проверки на Backend

```python
# is_test может быть установлен только админом
is_test = request.is_test and current_user.is_admin

# Если не админ пытается установить is_test — игнорируется
if not current_user.is_admin and request.is_test:
    logger.warning(f"Non-admin user {current_user.id} tried to set is_test")
```

### Что Защищено

- ✅ **Финансы:** Тестовые кампании не создают реальных платежей
- ✅ **Статистика:** Тестовые данные не влияют на общую статистику
- ✅ **Доступ:** Только `is_admin=True` пользователи могут использовать test mode
- ✅ **Видимость:** Тестовые кампании скрыты по умолчанию

---

## Rollback Plan

Если возникли проблемы:

### 1. Откатить миграцию

```bash
cd /opt/market-telegram-bot
docker compose run --rm bot poetry run alembic downgrade -1
```

### 2. Откатить код

```bash
cd /opt/market-telegram-bot
git checkout <previous-tag> -- src/
docker compose build
docker compose up -d
```

### 3. Удалить тестовые данные (если нужно)

```sql
-- Удалить тестовые каналы
DELETE FROM telegram_chats WHERE is_test = true;

-- Удалить тестовые кампании
DELETE FROM placement_requests WHERE is_test = true;
```

---

## FAQ

### Q: Можно ли использовать test mode для демо клиентам?

**A:** Да! Test mode идеально подходит для демонстрации функционала без реальных платежей.

### Q: Влияют ли тестовые кампании на XP/уровни/рейтинг?

**A:** Нет, тестовые кампании не влияют на геймификацию (XP, levels, reputation).

### Q: Можно ли создать тестовую кампанию на реальном канале?

**A:** Да, можно. Пост будет опубликован в канале, но оплата не произойдёт.

### Q: Как отличить тестовую кампанию от реальной?

**A:** 
- Визуально: бейдж "🧪 ТЕСТ"
- В API: поле `is_test: true`
- В БД: колонка `is_test = true`

---

## Контакты

По вопросам test mode обращайтесь:
- Tech Lead: @tech-lead
- DevOps: @devops-team

---

*Документ обновлён: 2026-03-19*
