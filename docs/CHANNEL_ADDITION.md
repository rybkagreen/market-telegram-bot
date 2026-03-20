# Добавление Каналов — Полная Документация

**Версия:** 1.0  
**Дата:** 2026-03-18  
**Статус:** ✅ Завершено

---

## Обзор Функционала

Функционал добавления каналов позволяет владельцам Telegram-каналов добавлять свои каналы в платформу RekHarborBot для последующей монетизации через размещение рекламы.

### Ключевые Возможности

1. **Проверка прав бота** — бот должен быть администратором канала
2. **Валидация канала** — проверка на соответствие правилам платформы
3. **Языковая проверка** — детекция русского языка
4. **AI классификация** — автоматическое определение тематики канала
5. **Визуальная индикация** — понятное отображение прав и статусов

---

## Как Добавить Канал

### Через Mini App

1. Откройте Mini App: **Мои каналы → Добавить канал**
2. Введите username канала (например, `@durov` или `durov`)
3. Нажмите **🔍 Проверить канал**
4. Дождитесь результатов проверки
5. Если канал валиден — нажмите **➕ Добавить канал**

### Требования к Каналу

| Требование | Значение | Блокирует |
|------------|----------|-----------|
| Тип чата | `channel` (канал) | ✅ Да |
| Публичность | Есть username | ✅ Да |
| Подписчики | Минимум 100 | ✅ Да |
| Права бота | Администратор + публикация + удаление + закрепление | ✅ Да |
| Запрещённый контент | Нет ключевых слов (казино, ставки, 18+, и т.д.) | ✅ Да |
| Язык | Преимущественно русский | ❌ Нет (предупреждение) |

---

## Права Бота

### Обязательные Права

Бот должен иметь следующие права в канале:

| Право | Описание | Обязательно |
|-------|----------|-------------|
| **Администратор** | Базовое право для управления | ✅ Да |
| **Публикация сообщений** | Размещение рекламных постов | ✅ Да |
| **Удаление сообщений** | Удаление постов после кампании | ✅ Да |
| **Закрепление сообщений** | Закрепление важных постов | ✅ Да |

### Как Выдать Права

1. Откройте настройки канала → **Администраторы**
2. Нажмите **Добавить администратора**
3. Найдите `@RekHarborBot`
4. Включите права:
   - ✅ Публикация сообщений
   - ✅ Удаление сообщений
   - ✅ Закрепление сообщений
5. Сохраните изменения

### Быстрая Ссылка

Используйте ссылку для быстрого перехода в настройки:
```
https://t.me/{username}?admin
```

---

## Проверка Канала

### Этапы Проверки

```
1. Проверка существования канала
   ↓
2. Проверка типа чата (должен быть channel)
   ↓
3. Проверка прав бота (администратор?)
   ↓
4. Проверка необходимых прав (публикация, удаление, закрепление)
   ↓
5. Проверка на дубликат (не добавлен ранее?)
   ↓
6. Проверка правил платформы (подписчики, запрещённый контент)
   ↓
7. Проверка языка (русский?)
   ↓
8. AI классификация тематики
   ↓
Результат
```

### Результаты Проверки

#### ✅ Канал Валиден

```
✅ Канал можно добавить

Информация о канале:
- Название: Durov's Channel
- Username: @durov
- Подписчики: 500 000
- Тематика: 📁 news

Права бота:
⚙️  Администратор *          ✅
📝  Публикация сообщений *   ✅
🗑️  Удаление сообщений *     ✅
📌  Закрепление сообщений    ✅

[➕ Добавить канал]
```

#### ❌ Недостаточно Прав Бота

```
❌ Недостаточно прав у бота для добавления канала

📋 Как добавить бота как администратора ▼

1. Откройте настройки канала
   Нажмите кнопку ниже или перейдите в канал → Управление

2. Добавьте администратора
   Администраторы → Добавить администратора

3. Найдите бота
   В поиске введите @RekHarborBot

4. Выдайте права
   Включите: Публикация, Удаление, Закрепление сообщений

5. Проверьте права
   Нажмите "Проверить канал" после добавления бота

[🔗 Открыть настройки канала]

Права бота:
⚙️  Администратор *          ✅
📝  Публикация сообщений *   ❌
🗑️  Удаление сообщений *     ❌
📌  Закрепление сообщений    ✅

ℹ️  Все обязательные права (*) должны быть выданы
```

#### ❌ Нарушения Правил Платформы

```
❌ Канал не соответствует правилам платформы:
• Минимум 100 подписчиков (сейчас: 50)
• Запрещённый контент в описании: 'казино'
```

#### ⚠️ Предупреждение о Языке

```
⚠️ Название канала преимущественно не на русском языке

[Канал можно добавить, предупреждение информативное]
```

---

## API Документация

### POST /api/channels/check

Проверить канал перед добавлением.

**Request:**
```http
POST /api/channels/check
Authorization: Bearer <JWT_TOKEN>
Content-Type: application/json

{
  "username": "durov"
}
```

**Response 200 (Valid):**
```json
{
  "valid": true,
  "channel": {
    "id": 1234567890,
    "title": "Durov's Channel",
    "username": "durov",
    "member_count": 500000
  },
  "bot_permissions": {
    "is_admin": true,
    "post_messages": true,
    "delete_messages": true,
    "pin_messages": true
  },
  "missing_permissions": [],
  "is_already_added": false,
  "rules_valid": true,
  "rules_violations": [],
  "language_valid": true,
  "language_warnings": [],
  "category": "news"
}
```

**Response 400 (Rules Violation):**
```json
{
  "detail": {
    "message": "Канал не соответствует правилам платформы",
    "violations": [
      "Минимум 100 подписчиков (сейчас: 50)",
      "Запрещённый контент в описании: 'казино'"
    ]
  }
}
```

**Response 403 (Bot Not Admin):**
```json
{
  "detail": "Бот не является администратором канала"
}
```

### POST /api/channels/

Добавить канал в платформу.

**Request:**
```http
POST /api/channels/
Authorization: Bearer <JWT_TOKEN>
Content-Type: application/json

{
  "username": "durov"
}
```

**Response 200:**
```json
{
  "id": 1,
  "telegram_id": 1234567890,
  "username": "durov",
  "title": "Durov's Channel",
  "owner_id": 123,
  "member_count": 500000,
  "last_er": 0.0,
  "avg_views": 0,
  "rating": 0.0,
  "category": null,
  "subcategory": null,
  "is_active": true
}
```

### GET /api/channels/

Получить список моих каналов.

**Request:**
```http
GET /api/channels/
Authorization: Bearer <JWT_TOKEN>
```

**Response 200:**
```json
[
  {
    "id": 1,
    "telegram_id": 1234567890,
    "username": "durov",
    "title": "Durov's Channel",
    "owner_id": 123,
    "member_count": 500000,
    "is_active": true
  }
]
```

---

## curl Команды для Тестирования

### Проверка Канала

```bash
# Валидный канал
curl -X POST http://localhost:8001/api/channels/check \
  -H 'Authorization: Bearer <JWT_TOKEN>' \
  -H 'Content-Type: application/json' \
  -d '{"username":"durov"}'

# Канал с нарушениями
curl -X POST http://localhost:8001/api/channels/check \
  -H 'Authorization: Bearer <JWT_TOKEN>' \
  -H 'Content-Type: application/json' \
  -d '{"username":"casino_channel"}'

# Канал где бот не админ
curl -X POST http://localhost:8001/api/channels/check \
  -H 'Authorization: Bearer <JWT_TOKEN>' \
  -H 'Content-Type: application/json' \
  -d '{"username":"some_channel"}'
```

### Добавление Канала

```bash
curl -X POST http://localhost:8001/api/channels/ \
  -H 'Authorization: Bearer <JWT_TOKEN>' \
  -H 'Content-Type: application/json' \
  -d '{"username":"durov"}'
```

### Список Каналов

```bash
curl -X GET http://localhost:8001/api/channels/ \
  -H 'Authorization: Bearer <JWT_TOKEN>'
```

---

## Компоненты UI

### PermissionList

Отображает права бота с визуальной индикацией.

**Файл:** `mini_app/src/components/permissions/PermissionList.tsx`

**Пропсы:**
```typescript
interface PermissionListProps {
  permissions: {
    is_admin: boolean
    post_messages: boolean
    delete_messages: boolean
    pin_messages: boolean
  }
}
```

**Отображение:**
- ✅ Зелёный фон — право выдано
- ❌ Красный фон — право отсутствует
- * Звёздочка — обязательное право

### ChannelInstruction

Пошаговая инструкция по добавлению бота.

**Файл:** `mini_app/src/components/channels/ChannelInstruction.tsx`

**Пропсы:**
```typescript
interface ChannelInstructionProps {
  channelUsername?: string
}
```

**Функционал:**
- Expand/collapse анимация
- 5 шагов инструкции
- Кнопка "Открыть настройки канала"
- Haptic feedback

---

## Валидации

### ChannelRulesChecker

**Файл:** `src/utils/telegram/channel_rules_checker.py`

**Проверки:**
1. Тип чата = `channel`
2. Есть username (публичный)
3. Подписчики >= 100
4. Нет запрещённых ключевых слов

**Запрещённые ключевые слова:**
```python
FORBIDDEN_KEYWORDS = [
    "казино", "ставки", "беттинг", "18+", "порно",
    "насилие", "наркотики", "оружие", "мошенничество",
    "террор", "экстремизм", "азартные игры", "слоты", "букмекер"
]
```

### RussianLangDetector

**Файл:** `src/utils/telegram/russian_lang_detector.py`

**Проверки:**
1. Процент кириллицы в названии >= 50%
2. Описание на русском языке
3. Нет в English blacklist

**Предупреждения (не блокируют):**
- "Название канала преимущественно не на русском языке"
- "Описание канала преимущественно не на русском языке"
- "Канал содержится в чёрном списке англоязычных каналов"

### ChannelService.classify_channel_topic

**Файл:** `src/core/services/channel_service.py`

**AI Классификация:**
- Использует Mistral AI
- 14 допустимых категорий
- Timeout и fallback на `None`
- Не блокирует добавление

**Категории:**
```python
VALID_CATEGORIES = [
    "technology", "business", "education", "entertainment", "news",
    "sports", "lifestyle", "finance", "marketing", "crypto",
    "health", "travel", "food", "other"
]
```

---

## Обработка Ошибок

### Ошибки API

| Код | Сообщение | Действие |
|-----|-----------|----------|
| 400 | Канал не найден | Проверить username |
| 400 | Не является каналом | Выбрать канал, не группу |
| 400 | Канал не соответствует правилам | Исправить нарушения |
| 403 | Бот не администратор | Добавить бота как админа |
| 403 | Не удалось проверить права | Проверить соединение |
| 401 | Требуется авторизация | Войти заново |

### Frontend Обработка

```typescript
const checkMutation = useCheckChannel({
  onSuccess: (data) => {
    if (!data.valid) {
      // Показать нарушения
    } else if (data.is_already_added) {
      // Канал уже добавлен
    } else {
      // Успех
    }
  },
  onError: (error) => {
    // 400 → Канал не найден
    // 403 → Бот не админ
    // 500 → Серверная ошибка
  }
})
```

---

## Развёртывание

### Чеклист

- [ ] BOT_TOKEN настроен в `.env`
- [ ] MISTRAL_API_KEY настроен в `.env`
- [ ] База данных мигрирована
- [ ] Redis запущен
- [ ] Celery worker запущен
- [ ] API запущен
- [ ] Mini App собран (`npm run build`)
- [ ] Frontend развёрнут

### Переменные Окружения

```bash
# Telegram
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz

# Mistral AI
MISTRAL_API_KEY=your_mistral_api_key
AI_MODEL=mistral-medium-latest

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/db

# Redis
REDIS_URL=redis://localhost:6379/0
```

---

## Тестирование

### Сценарии

| № | Сценарий | Ожидаемый Результат |
|---|----------|---------------------|
| 1 | Валидный канал | ✅ Можно добавить |
| 2 | Запрещённый контент | ❌ Заблокировано |
| 3 | < 100 подписчиков | ❌ Заблокировано |
| 4 | Английский язык | ⚠️ Предупреждение |
| 5 | Бот не админ | ❌ Инструкция |
| 6 | Недостаточно прав | ❌ Список прав |
| 7 | Уже добавлен | ❌ Уведомление |
| 8 | Не существует | ❌ Канал не найден |

### Автоматические Тесты

```bash
# Backend
python -m pytest tests/test_channel_addition.py -v

# Frontend
cd mini_app && npm run test
```

---

## Известные Ограничения

1. **Mistral AI:** При недоступности API классификация возвращает `None`
2. **English Blacklist:** Возможны ложные срабатывания
3. **Языковая детекция:** Основана на проценте кириллицы
4. **Минимум подписчиков:** Жёсткое правило 100+

---

## Ссылки

- [Фаза 1: Критические Исправления](../../reports/features/CHANNEL-P1_CRITICAL_FIX.md)
- [Фаза 2: Улучшения UX](../../reports/features/CHANNEL-P2_UX_IMPROVEMENTS.md)
- [Фаза 3: Пост-МВП Улучшения](../../reports/features/CHANNEL-P3_POST_MVP_ENHANCEMENTS.md)
- [Финальный Отчёт](../../reports/features/CHANNEL-ADDITION-FINAL-REPORT.md)

---

*RekHarborBot — Channel Addition Documentation | 2026-03-18*
