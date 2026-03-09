# 📊 КАНАЛЫ И КАТЕГОРИИ — ОТЧЁТ О ПРОБЛЕМАХ

**Дата аудита:** 2026-03-10  
**Объект:** Статистика каналов по категориям и подкатегориям  
**Статус:** 🔴 КРИТИЧЕСКИЕ ПРОБЛЕМЫ

---

## 📊 ОБЩАЯ СТАТИСТИКА

**Всего активных каналов:** 34  
**Каналов с подкатегорией:** 9 (26%)  
**Каналов без подкатегории:** 25 (74%) ⚠️

---

## 🔴 ПРОБЛЕМА 1: Смешение русских и английских названий тем

### Описание
В базе данных каналов используются темы на разных языках, что приводит к некорректной статистике.

### Текущее состояние:
```
| topic (БД каналов) | topic (справочник) | Статус |
|--------------------|--------------------|--------|
| it                 | it                 | ✅ OK  |
| business           | бизнес             | ❌ MISMATCH |
| education          | образование        | ❌ MISMATCH |
| marketing          | маркетинг          | ❌ MISMATCH |
| news               | новости            | ❌ MISMATCH |
| other              | -                  | ❌ NO REF |
| health             | здоровье           | ❌ MISMATCH |
| finance            | финансы            | ❌ MISMATCH |
| crypto             | крипто             | ❌ MISMATCH |
```

### Влияние на статистику:
- Каналы с `topic='business'` не попадают в категорию `бизнес`
- Каналы с `topic='news'` не попадают в категорию `новости`
- Статистика по категориям раздвоена

### Пример:
```sql
-- Каналы в БД
SELECT topic, COUNT(*) FROM telegram_chats GROUP BY topic;

-- Результат:
business  | 3
news      | 4
marketing | 1

-- Справочник topic_categories
SELECT topic, COUNT(*) FROM topic_categories GROUP BY topic;

-- Результат:
бизнес      | 5 подкатегорий
новости     | 0 (нет в справочнике!)
маркетинг   | 5 подкатегорий
```

---

## 🔴 ПРОБЛЕМА 2: 74% каналов без подкатегории

### Каналы без subcategory (25 каналов):

| topic | count | Примеры каналов |
|-------|-------|-----------------|
| **other** | 10 | Movies, Popcorn Today, Free Crypto |
| **news** | 4 | ТАСС, РИА Новости, Холод |
| **it** | 4 | Go, Entertainment, DAILY DVIZH |
| **business** | 3 | Коммерсантъ, ВЕДОМОСТИ, Russian Business |
| **education** | 1 | ПостНаука |
| **Другое** | 1 | Science in telegram |
| **новости** | 1 | Ароматный Мир |
| **финансы** | 1 | FINNEXT |

### Влияние:
- Невозможно фильтровать каналы по подкатегориям
- Статистика показывает "0" по всем подкатегориям
- Пользователи не могут выбрать конкретную специализацию

---

## 🟠 ПРОБЛЕМА 3: Несогласованные subcategory

### Каналы с invalid subcategory:

| Канал | topic | subcategory | Ожидаемая subcategory |
|-------|-------|-------------|----------------------|
| Smm room | marketing | digital | smm / digital (нет в справочнике) |
| Моя Поликлиника | health | medicine | нет в справочнике |

### Проблема:
- `marketing + digital` — нет в справочнике (есть `digital` без topic)
- `health + medicine` — нет в справочнике

---

## 🟠 ПРОБЛЕМА 4: Отсутствие темы "news/новости" в справочнике

**Факт:** В `topic_categories` нет темы `новости` или `news`!

**Каналы受影响:** 5 каналов
- ТАСС
- РИА Новости
- Холод
- FIGMA — Code Review
- Ароматный Мир

---

## 🟡 ПРОБЛЕМА 5: Тема "other" без справочника

**Факт:** 10 каналов помечены как `other` — это "мусорная" категория.

**Каналы:**
- Movies
- Popcorn Today 🍿
- Blum: All Crypto
- rndm.club
- WOOFS ДВИЖ Party+After
- Марат Хуснуллин
- Айбелив Айкенфлаев
- Free Crypto
- Blum Memepad
- Gazgolder club

**Проблема:** Невозможно понять реальную тематику каналов.

---

## 📈 РАСПРЕДЕЛЕНИЕ ПО КАТЕГОРИЯМ (ТЕКУЩЕЕ)

```
it              ████████████████████ 11 каналов (32%)
  └─ programming ████████ 4
  └─ devops      ██████ 3
  └─ (empty)     ████ 4

other           ██████████████████ 10 каналов (29%)
  └─ (empty)     ██████████████████ 10

news            ████████ 4 канала (12%)
  └─ (empty)     ████████ 4

business        ██████ 3 канала (9%)
  └─ (empty)     ██████ 3

marketing       ██ 1 канал (3%)
  └─ digital     ██ 1

health          ██ 1 канал (3%)
  └─ medicine    ██ 1

education       ██ 1 канал (3%)
  └─ (empty)     ██ 1

Другое          ██ 1 канал (3%)
  └─ (empty)     ██ 1

новости         ██ 1 канал (3%)
  └─ (empty)     ██ 1

финансы         ██ 1 канал (3%)
  └─ (empty)     ██ 1
```

---

## 🎯 РЕКОМЕНДАЦИИ

### P0 — Критические (срочно):

1. **Унифицировать названия тем**
   - Привести все `topic` к русскому языку (как в справочнике)
   - Маппинг:
     - `business` → `бизнес`
     - `education` → `образование`
     - `marketing` → `маркетинг`
     - `news` → `новости`
     - `health` → `здоровье`
     - `finance` → `финансы`
     - `crypto` → `крипто`

2. **Добавить тему "новости" в справочник**
   - Создать подкатегории: `media`, `politics`, `economy`, `society`

3. **Заполнить подкатегории для 25 каналов**
   - Провести ручную классификацию
   - Или использовать LLM для авто-классификации

### P1 — Важные (в течение спринта):

4. **Исправить invalid subcategory**
   - `marketing + digital` → `маркетинг + digital`
   - `health + medicine` → добавить в справочник

5. **Разобрать "other" категорию**
   - Переклассифицировать 10 каналов
   - Удалить тему `other` из использования

### P2 — Средние (следующий спринт):

6. **Добавить валидацию при создании/обновлении канала**
   - Проверка existence topic+subcategory в справочнике
   - Запрет на пустую subcategory

7. **Создать админ-интерфейс для классификации**
   - Ручное редактирование topic/subcategory
   - Массовое обновление

---

## 📋 SQL ДЛЯ ИСПРАВЛЕНИЯ

### 1. Обновить topic на русский язык:

```sql
-- business → бизнес
UPDATE telegram_chats SET topic = 'бизнес' WHERE topic = 'business';

-- education → образование
UPDATE telegram_chats SET topic = 'образование' WHERE topic = 'education';

-- marketing → маркетинг
UPDATE telegram_chats SET topic = 'маркетинг' WHERE topic = 'marketing';

-- news → новости
UPDATE telegram_chats SET topic = 'новости' WHERE topic = 'news';

-- health → здоровье
UPDATE telegram_chats SET topic = 'здоровье' WHERE topic = 'health';

-- finance → финансы
UPDATE telegram_chats SET topic = 'финансы' WHERE topic = 'finance';

-- crypto → крипто
UPDATE telegram_chats SET topic = 'крипто' WHERE topic = 'crypto';
```

### 2. Добавить тему "новости" в справочник:

```sql
INSERT INTO topic_categories (topic, subcategory, display_name_ru, is_active, sort_order)
VALUES 
  ('новости', 'media', 'СМИ и журналистика', true, 1),
  ('новости', 'politics', 'Политика', true, 2),
  ('новости', 'economy', 'Экономика', true, 3),
  ('новости', 'society', 'Общество', true, 4),
  ('новости', 'world', 'Мировые новости', true, 5);
```

### 3. Обновить подкатегории для каналов:

```sql
-- Пример для news каналов
UPDATE telegram_chats SET subcategory = 'media' 
WHERE topic = 'новости' AND (subcategory IS NULL OR subcategory = '');

-- Пример для business каналов
UPDATE telegram_chats SET subcategory = 'media' 
WHERE topic = 'бизнес' AND username IN ('kommersant', 'vedomosti', 'tass_agency');
```

---

## 📊 ОЖИДАЕМЫЙ РЕЗУЛЬТАТ ПОСЛЕ ИСПРАВЛЕНИЯ

```
ит                11 каналов
  └─ programming   4
  └─ devops        3
  └─ ai_ml         0
  └─ data          0
  └─ gamedev       0
  └─ mobile_dev    0
  └─ security      0
  └─ web_dev       0

новости           5 каналов
  └─ media         5

бизнес            4 канала
  └─ media         3
  └─ startup       1

маркетинг         2 канала
  └─ smm           1
  └─ digital       1

другие            8 каналов
  └─ (разные)      8
```

---

**АУДИТ ЗАВЕРШЁН:** 2026-03-10  
**СТАТУС:** 🔴 ТРЕБУЕТСЯ СРОЧНОЕ ИСПРАВЛЕНИЕ
