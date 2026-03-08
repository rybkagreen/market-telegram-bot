# UX АУДИТ ОТЧЁТ
## Market Telegram Bot (RekHarborBot)

**Дата аудита:** 8 марта 2026  
**Версия проекта:** 1.0  
**Аудитор:** AI Assistant

---

## СОДЕРЖАНИЕ

1. [Общая информация](#1-общая-информация)
2. [Команды бота](#2-команды-бота)
3. [Пользовательские потоки (28 flows)](#3-пользовательские-потоки-28-flows)
4. [B2B потоки (4 flows)](#4-b2b-потоки-4-flows)
5. [Геймификация потоки (3 flows)](#5-геймификация-потоки-3-flows)
6. [Админ потоки (6 flows)](#6-админ-потоки-6-flows)
7. [Типы уведомлений (19 types)](#7-типы-уведомлений-19-types)
8. [Клавиатуры](#8-клавиатуры)
9. [CallbackData классы](#9-callbackdata-классы)
10. [FSM состояния](#10-fsm-состояния)
11. [ASCII навигационная карта](#11-ascii-навигационная-карта)
12. [Рекомендации](#12-рекомендации)

---

## 1. ОБЩАЯ ИНФОРМАЦИЯ

### 1.1 Описание проекта

Market Telegram Bot (RekHarborBot) — это платформа для размещения рекламы в Telegram-каналах. Бот соединяет рекламодателей с владельцами каналов, автоматизируя процесс размещения, оплаты и публикации рекламных постов.

### 1.2 Основные роли пользователей

| Роль | Описание |
|------|----------|
| **new** | Новый пользователь, ещё не выбравший роль |
| **advertiser** | Рекламодатель, размещающий кампании |
| **owner** | Владелец канала, монетизирующий контент |
| **both** | Пользователь с обеими ролями |
| **admin** | Администратор платформы |

### 1.3 Технологический стек

- **Фреймворк:** Aiogram 3.x
- **База данных:** PostgreSQL + SQLAlchemy
- **Кэш:** Redis
- **Очереди:** Celery
- **AI провайдеры:** Groq, OpenAI, OpenRouter
- **Платежи:** CryptoBot, Telegram Stars

---

## 2. КОМАНДЫ БОТА

### 2.1 Зарегистрированные команды (set_my_commands)

| Команда | Описание | Файл |
|---------|----------|------|
| `/start` | 🏠 Главное меню | `src/bot/handlers/start.py:166` |
| `/app` | 📱 Открыть Mini App | `src/bot/handlers/start.py:553` |
| `/cabinet` | 👤 Личный кабинет | `src/bot/handlers/start.py:397` |
| `/balance` | 💳 Баланс | `src/bot/handlers/start.py:413` |
| `/help` | ℹ️ Помощь | `src/bot/handlers/start.py:368` |

### 2.2 Дополнительные команды

| Команда | Описание | Файл |
|---------|----------|------|
| `/stats` | Публичная статистика | `src/bot/handlers/stats.py:17` |
| `/admin` | Админ панель | `src/bot/handlers/admin.py:66` |
| `/cancel` | Отмена админа | `src/bot/handlers/admin.py:84` |
| `/add_channel` | Добавить канал | `src/bot/handlers/channel_owner.py:61` |
| `/my_channels` | Мои каналы | `src/bot/handlers/channel_owner.py:732` |
| `/models` | AI модели | `src/bot/handlers/models.py:77` |
| `/addchat` | Добавить чат для аналитики | `src/bot/handlers/analytics_chats.py:22` |
| `/b2b` | B2B пакеты | `src/bot/handlers/b2b.py:18` |

---

## 3. ПОЛЬЗОВАТЕЛЬСКИЕ ПОТОКИ (28 FLOWS)

### 3.1 Онбординг и регистрация

#### Flow 1: Онбординг нового пользователя
- **Статус:** ✅ Implemented
- **Триггер:** `/start` (новый пользователь без реферала)
- **CallbackData:** `OnboardingCB` (prefix="onboard")
- **FSM States:** `OnboardingStates.role_selected`
- **Handler:** `src/bot/handlers/start.py:_handle_start`
- **Описание:**
  1. Пользователь видит баннер с приветствием
  2. Предлагается выбрать роль: "📣 Размещать рекламу" или "📺 Зарабатывать на канале"
  3. После выбора роль сохраняется, показывается роль-зависимое меню
- **Сообщения:**
  - "🏄 Добро пожаловать в RekHarborBot!..."
  - "Кем вы хотите быть на платформе?"

#### Flow 2: Возвращающийся пользователь (рекламодатель)
- **Статус:** ✅ Implemented
- **Триггер:** `/start` (существующий пользователь с ролью advertiser)
- **CallbackData:** `MainMenuCB` (prefix="main")
- **Handler:** `src/bot/handlers/start.py:_handle_start`
- **Описание:**
  1. Показывается персонализированное приветствие
  2. Отображается баланс и тариф
  3. Показывается меню рекламодателя
- **Сообщения:**
  - "👋 С возвращением, {first_name}!"
  - "💳 Баланс: {user.credits:,} кр"
  - "📦 Тариф: {plan_value}"

#### Flow 3: Возвращающийся пользователь (владелец)
- **Статус:** ✅ Implemented
- **Триггер:** `/start` (существующий пользователь с ролью owner)
- **CallbackData:** `MainMenuCB` (prefix="main")
- **Handler:** `src/bot/handlers/start.py:_handle_start`
- **Описание:**
  1. Показывается количество каналов
  2. Индикатор новых заявок (если есть)
  3. Показывается меню владельца
- **Сообщения:**
  - "🔔 {pending} новых заявок на размещение!"
  - "📺 Ваших каналов: {channels_count}"

#### Flow 4: Смена роли
- **Статус:** ✅ Implemented
- **Триггер:** `main:change_role`
- **CallbackData:** `MainMenuCB(action="change_role")`, `OnboardingCB`
- **Handler:** `src/bot/handlers/start.py:change_role`
- **Описание:**
  1. Пользователь выбирает новую роль
  2. Прогресс сохраняется
  3. Показывается новое роль-зависимое меню
- **Сообщения:**
  - "🔄 Смена роли"
  - "Ваш прогресс (каналы, кампании, баланс) сохранится."

---

### 3.2 Создание кампании (AI Flow)

#### Flow 5: Создание кампании с AI — выбор стиля
- **Статус:** ✅ Implemented
- **Триггер:** `main:create_campaign_ai` или `campaign_create:start`
- **CallbackData:** `CampaignCreateCB` (prefix="campaign_create")
- **FSM States:** `CampaignCreateState.selecting_style`
- **Handler:** `src/bot/handlers/campaign_create_ai.py:start_campaign_create`
- **Клавиатура:** `get_ai_style_keyboard()`
- **Описание:**
  1. Пользователь выбирает стиль текста (6 вариантов)
  2. Стиль сохраняется в state
  3. Переход к выбору категории
- **Стили:** business, energetic, friendly, creative, professional, emotional

#### Flow 6: Создание кампании с AI — выбор категории
- **Статус:** ✅ Implemented
- **Триггер:** `campaign_create:style_{style}`
- **CallbackData:** `CampaignCreateCB`
- **FSM States:** `CampaignCreateState.selecting_category`, `CampaignCreateState.entering_custom_category`
- **Handler:** `src/bot/handlers/campaign_create_ai.py:style_selected`
- **Клавиатура:** `get_ai_category_keyboard()`
- **Описание:**
  1. Пользователь выбирает категорию (20 вариантов) или вводит свою
  2. Категория сохраняется
  3. Переход к описанию продукта

#### Flow 7: Создание кампании с AI — описание продукта
- **Статус:** ✅ Implemented
- **Триггер:** `campaign_create:category_{category}`
- **CallbackData:** `CampaignCreateCB`
- **FSM States:** `CampaignCreateState.waiting_for_description`
- **Handler:** `src/bot/handlers/campaign_create_ai.py:category_selected`
- **Описание:**
  1. Пользователь вводит описание продукта (мин. 20 символов)
  2. Описание сохраняется
  3. Переход к названию кампании

#### Flow 8: Создание кампании с AI — название кампании
- **Статус:** ✅ Implemented
- **Триггер:** Сообщение в состоянии `waiting_for_description`
- **FSM States:** `CampaignCreateState.waiting_for_campaign_name`
- **Handler:** `src/bot/handlers/campaign_create_ai.py:process_description`
- **Описание:**
  1. Пользователь вводит название кампании (3-100 символов)
  2. Название сохраняется
  3. Запускается AI генерация (3 варианта)

#### Flow 9: Создание кампании с AI — выбор варианта текста
- **Статус:** ✅ Implemented
- **Триггер:** `campaign_create:generate`
- **CallbackData:** `AIVariantCB` (prefix="ai_variant")
- **FSM States:** `CampaignCreateState.selecting_variant`
- **Handler:** `src/bot/handlers/campaign_create_ai.py:process_campaign_name`
- **Клавиатура:** `get_ai_variants_keyboard()`
- **Описание:**
  1. Показываются 3 варианта AI текста
  2. Пользователь выбирает лучший
  3. Переход к редактору

#### Flow 10: Создание кампании с AI — редактор текста
- **Статус:** ✅ Implemented
- **Триггер:** `ai_variant:{index}`
- **CallbackData:** `AIEditCB` (prefix="ai_edit")
- **FSM States:** `CampaignCreateState.editing_text`
- **Handler:** `src/bot/handlers/campaign_create_ai.py:select_variant`
- **Клавиатура:** `get_campaign_editor_keyboard()`
- **Описание:**
  1. Редактирование текста
  2. Добавление URL
  3. Добавление изображения
  4. Подтверждение

#### Flow 11: Создание кампании с AI — добавление URL
- **Статус:** ✅ Implemented
- **Триггер:** `ai_edit:add_url` или сообщение в состоянии `waiting_for_url`
- **FSM States:** `CampaignCreateState.waiting_for_url`
- **Handler:** `src/bot/handlers/campaign_create_ai.py:process_edited_text`, `process_url`
- **Описание:**
  1. Пользователь вводит URL (http://, https://, t.me/)
  2. URL валидируется
  3. Переход к изображению

#### Flow 12: Создание кампании с AI — добавление изображения
- **Статус:** ✅ Implemented
- **Триггер:** `ai_edit:add_image` или фото в состоянии `waiting_for_image`
- **FSM States:** `CampaignCreateState.waiting_for_image`
- **Handler:** `src/bot/handlers/campaign_create_ai.py:process_image`
- **Описание:**
  1. Пользователь отправляет фото
  2. Фото сохраняется (file_id)
  3. Переход к настройкам аудитории

#### Flow 13: Создание кампании с AI — выбор аудитории
- **Статус:** ✅ Implemented
- **Триггер:** `campaign_create:skip_image`
- **CallbackData:** `CampaignCreateCB`
- **FSM States:** `CampaignCreateState.selecting_audience`
- **Handler:** `src/bot/handlers/campaign_create_ai.py:skip_image`
- **Клавиатура:** `get_audience_keyboard()`
- **Описание:**
  1. Выбор тематики аудитории (8 основных + все)
  2. Переход к бюджету

#### Flow 14: Создание кампании с AI — настройка бюджета
- **Статус:** ⚠️ Partial (заглушка)
- **Триггер:** `campaign_create:audience_{audience}`
- **FSM States:** `CampaignCreateState.setting_budget`
- **Handler:** `src/bot/handlers/campaign_create_ai.py:select_audience`, `process_budget`
- **Описание:**
  1. Пользователь вводит бюджет (мин. 100 кредитов)
  2. Бюджет сохраняется
  3. Переход к расписанию
- **Проблема:** Нет интеграции с платёжной системой для проверки баланса

#### Flow 15: Создание кампании с AI — расписание
- **Статус:** ✅ Implemented
- **Триггер:** `campaign_create:setting_budget`
- **CallbackData:** `CampaignCreateCB`
- **FSM States:** `CampaignCreateState.setting_schedule`, `CampaignCreateState.entering_schedule_date`
- **Handler:** `src/bot/handlers/campaign_create_ai.py:process_budget`
- **Клавиатура:** `get_schedule_keyboard()`
- **Описание:**
  1. Выбор времени запуска (сейчас, через 1ч, вечером, завтра, custom)
  2. Дата парсится и конвертируется в UTC
  3. Переход к финальному созданию

#### Flow 16: Создание кампании с AI — финальное создание
- **Статус:** ⚠️ Partial
- **Триггер:** `campaign_create:schedule_*`
- **FSM States:** `CampaignCreateState.confirming`
- **Handler:** `src/bot/handlers/campaign_create_ai.py:schedule_*`, `final_create_campaign`
- **Описание:**
  1. Создание записи кампании в БД
  2. Отправка в очередь Celery
- **Проблема:** Функция `final_create_campaign` обрезана в коде, полная реализация не видна

---

### 3.3 Создание кампании (Manual Flow)

#### Flow 17: Создание кампании вручную — тематика
- **Статус:** ✅ Implemented
- **Триггер:** `main:create_campaign`
- **CallbackData:** `CampaignCB` (prefix="campaign")
- **FSM States:** `CampaignStates.waiting_topic`
- **Handler:** `src/bot/handlers/campaigns.py:start_campaign_wizard`
- **Клавиатура:** `get_topics_kb()`
- **Описание:**
  1. Выбор тематики (9 вариантов)
  2. Переход к заголовку

#### Flow 18: Создание кампании вручную — заголовок
- **Статус:** ✅ Implemented
- **Триггер:** `campaign:topic:{topic}`
- **FSM States:** `CampaignStates.waiting_header`
- **Handler:** `src/bot/handlers/campaigns.py:select_topic`
- **Описание:**
  1. Ввод заголовка (5-255 символов)
  2. Валидация длины
  3. Переход к выбору типа текста

#### Flow 19: Создание кампании вручную — выбор типа текста
- **Статус:** ✅ Implemented
- **Триггер:** Сообщение в состоянии `waiting_header`
- **FSM States:** `CampaignStates.waiting_text`
- **Handler:** `src/bot/handlers/campaigns.py:handle_header_input`
- **Клавиатура:** `get_text_type_kb()`
- **Описание:**
  1. Выбор: вручную или ИИ
  2. Для FREE тарифа ИИ заблокирован

#### Flow 20: Создание кампании вручную — AI генерация текста
- **Статус:** ✅ Implemented
- **Триггер:** `campaign:ai_text`
- **FSM States:** `CampaignStates.waiting_ai_description`
- **Handler:** `src/bot/handlers/campaigns.py:select_ai_text`
- **Описание:**
  1. Ввод описания для ИИ (мин. 10 символов)
  2. Генерация 3 вариантов
  3. Выбор варианта

#### Flow 21: Создание кампании вручную — ручной текст
- **Статус:** ✅ Implemented
- **Триггер:** `campaign:manual_text`
- **FSM States:** `CampaignStates.waiting_text`
- **Handler:** `src/bot/handlers/campaigns.py:handle_text_input`
- **Описание:**
  1. Ввод текста (50-4000 символов)
  2. Content filter проверка
  3. Переход к изображению

#### Flow 22: Создание кампании вручную — изображение
- **Статус:** ✅ Implemented
- **Триггер:** Сообщение в состоянии `waiting_text` или `campaign:image_upload`
- **FSM States:** `CampaignStates.waiting_image`
- **Handler:** `src/bot/handlers/campaigns.py:handle_text_input`, `handle_image_upload`
- **Клавиатура:** `get_image_upload_kb()`
- **Описание:**
  1. Загрузка фото или пропуск
  2. Переход к размеру аудитории

#### Flow 23: Создание кампании вручную — размер аудитории
- **Статус:** ✅ Implemented
- **Триггер:** `campaign:image_skip` или сообщение с фото
- **FSM States:** `CampaignStates.waiting_member_count`
- **Handler:** `src/bot/handlers/campaigns.py:handle_image_upload`, `image_skip`
- **Клавиатура:** `get_member_count_kb()`
- **Описание:**
  1. Выбор диапазона участников чатов
  2. Переход к расписанию

#### Flow 24: Создание кампании вручную — расписание
- **Статус:** ✅ Implemented
- **Триггер:** `campaign:members:{value}`
- **FSM States:** `CampaignStates.waiting_schedule`
- **Handler:** `src/bot/handlers/campaigns.py:select_member_count`
- **Клавиатура:** `get_schedule_kb()`
- **Описание:**
  1. Выбор: сейчас или запланировать
  2. Ввод даты вручную (ГГГГ-ММ-ДД ЧЧ:ММ)
  3. Переход к подтверждению

#### Flow 25: Создание кампании вручную — подтверждение
- **Статус:** ✅ Implemented
- **Триггер:** `campaign:schedule_now` или сообщение с датой
- **FSM States:** `CampaignStates.waiting_confirm`
- **Handler:** `src/bot/handlers/campaigns.py:schedule_now`, `handle_schedule_datetime`
- **Клавиатура:** `get_campaign_confirm_kb()`
- **Описание:**
  1. Показ сводки кампании
  2. Выбор: запустить, изменить, черновик
  3. Запуск кампании

---

### 3.4 Управление каналами

#### Flow 26: Добавление канала
- **Статус:** ✅ Implemented
- **Триггер:** `/add_channel` или `main:add_channel`
- **CallbackData:** `channel_add:*`
- **FSM States:** `AddChannelStates` (waiting_username, waiting_bot_admin_confirmation, waiting_price, waiting_topics, waiting_settings, waiting_confirm)
- **Handler:** `src/bot/handlers/channel_owner.py:cmd_add_channel`
- **Описание:**
  1. Ввод @username канала
  2. Проверка существования канала
  3. Подтверждение что бот добавлен админом
  4. Ввод цены за пост
  5. Выбор тематик (toggle)
  6. Настройки размещения (лимит постов, режим одобрения)
  7. Подтверждение и сохранение в БД

#### Flow 27: Мои каналы
- **Статус:** ✅ Implemented
- **Триггер:** `main:my_channels` или `/my_channels`
- **Handler:** `src/bot/handlers/channel_owner.py:cmd_my_channels`
- **Описание:**
  1. Показ списка каналов пользователя
  2. Для каждого канала: статус, статистика, настройки
  3. Возможность редактирования

#### Flow 28: Заявки на размещение
- **Статус:** ✅ Implemented
- **Триггер:** `main:my_requests`
- **Handler:** `src/bot/handlers/start.py:go_to_my_requests`
- **Описание:**
  1. Показ количества pending заявок
  2. Перенаправление в "Мои каналы" → "Заявки"
  3. Автоматическое одобрение через 24 часа

---

## 4. B2B ПОТОКИ (4 FLOWS)

#### B2B Flow 1: Главное меню B2B
- **Статус:** ✅ Implemented
- **Триггер:** `/b2b` или `main:b2b`
- **Handler:** `src/bot/handlers/b2b.py:cmd_b2b`
- **Описание:**
  1. Показ 6 ниш: IT, Бизнес, Недвижимость, Крипта, Маркетинг, Финансы
  2. Выбор ниши для просмотра пакетов

#### B2B Flow 2: Просмотр пакетов ниши
- **Статус:** ✅ Implemented
- **Триггер:** `b2b_niche:{niche}`
- **Handler:** `src/bot/handlers/b2b.py:show_niche_packages`
- **Описание:**
  1. Загрузка пакетов из `b2b_package_service`
  2. Показ: каналов, охват, мин. ER, цена, скидка
  3. Возврат к выбору ниш

#### B2B Flow 3: Детали пакета
- **Статус:** ❌ Not Implemented
- **Ожидаемый триггер:** `b2b_package:{package_id}`
- **Где реализовать:** `src/bot/handlers/b2b.py`
- **Описание:**
  1. Детальная информация о пакете
  2. Кнопка "Купить пакет"
  3. Интеграция с оплатой

#### B2B Flow 4: Покупка B2B пакета
- **Статус:** ❌ Not Implemented
- **Ожидаемый триггер:** `b2b_buy:{package_id}`
- **Где реализовать:** `src/bot/handlers/b2b.py`
- **Описание:**
  1. Подтверждение покупки
  2. Оплата через CryptoBot/Stars
  3. Активация пакета

---

## 5. ГЕЙМИФИКАЦИЯ ПОТОКИ (3 FLOWS)

#### Gamification Flow 1: Просмотр значков
- **Статус:** ✅ Implemented
- **Триггер:** `cabinet:badges`
- **Handler:** `src/bot/handlers/cabinet.py:show_badges`
- **Сервис:** `badge_service.get_user_badges()`
- **Описание:**
  1. Показ до 10 последних значков
  2. Для каждого: иконка, название, описание, XP, дата
  3. Возврат в кабинет

#### Gamification Flow 2: Прогресс уровня
- **Статус:** ✅ Implemented
- **Триггер:** Открытие кабинета (`main:cabinet`)
- **Handler:** `src/bot/handlers/cabinet.py:show_cabinet`
- **Сервис:** `xp_service.get_user_stats()`
- **Описание:**
  1. Расчёт уровня по XP (7 уровней)
  2. Прогресс-бар XP
  3. Привилегия следующего уровня
  4. Раздельные уровни для advertiser/owner

#### Gamification Flow 3: Реферальная программа
- **Статус:** ✅ Implemented
- **Триггер:** `billing:referral`
- **Handler:** `src/bot/handlers/cabinet.py:referral_callback`
- **Описание:**
  1. Показ реферальной ссылки
  2. Количество приглашённых
  3. Список последних рефералов
  4. Бонус 50₽ за каждого

---

## 6. АДМИН ПОТОКИ (6 FLOWS)

#### Admin Flow 1: Вход в админку
- **Статус:** ✅ Implemented
- **Триггер:** `/admin` или `main:admin_panel`
- **CallbackData:** `AdminCB` (prefix="admin")
- **FSM States:** Нет
- **Handler:** `src/bot/handlers/admin.py:handle_admin_menu`
- **Фильтр:** `AdminFilter()`
- **Клавиатура:** `get_admin_main_kb()`
- **Описание:**
  1. Проверка прав администратора
  2. Показ главного меню админки
  3. 10 разделов: статистика, пользователи, рассылки, ЧС, broadcast, тест кампании, мониторинг, задачи Celery, LLM-классификация

#### Admin Flow 2: Управление пользователями
- **Статус:** ✅ Implemented
- **Триггер:** `admin:users`
- **FSM States:** `AdminBalanceStates`, `AdminBanStates`
- **Handler:** `src/bot/handlers/admin.py:handle_users_list`, `show_users_page`
- **Описание:**
  1. Список пользователей с пагинацией
  2. Детали пользователя
  3. Бан/разбан
  4. Изменение баланса
  5. Переключение уведомлений

#### Admin Flow 3: Broadcast рассылка
- **Статус:** ✅ Implemented
- **Триггер:** `admin:broadcast`
- **FSM States:** `AdminBroadcastStates` (waiting_message, waiting_confirm)
- **Handler:** `src/bot/handlers/admin.py:handle_broadcast_start`
- **Описание:**
  1. Ввод текста рассылки
  2. Предпросмотр
  3. Подтверждение
  4. Отправка всем пользователям

#### Admin Flow 4: Тест кампании (AI)
- **Статус:** ✅ Implemented
- **Триггер:** `admin:test_campaign` → `admin:ai_generate`
- **FSM States:** `AdminAIGenerateStates` (waiting_description, waiting_variants, waiting_topic, waiting_member_count, waiting_schedule, waiting_confirm)
- **Handler:** `src/bot/handlers/admin.py:handle_ai_generate_start`
- **Сервис:** `admin_ai_service.generate_ab_variants()`
- **Описание:**
  1. Ввод описания кампании
  2. AI генерация 3 вариантов
  3. Выбор варианта
  4. Генерация названия
  5. Выбор тематики
  6. Настройка аудитории
  7. Расписание
  8. Бесплатный запуск

#### Admin Flow 5: Чёрный список каналов
- **Статус:** ✅ Implemented
- **Триггер:** `admin:blacklist`
- **Handler:** `src/bot/handlers/admin.py:show_blacklist`, `unblacklist_channel`
- **Клавиатура:** `get_blacklist_kb()`, `get_blacklist_channel_kb()`
- **Описание:**
  1. Список заблокированных каналов с пагинацией
  2. Причина блокировки
  3. Разблокировка канала

#### Admin Flow 6: Здоровье рассылок
- **Статус:** ✅ Implemented
- **Триггер:** `admin:mailing_health`
- **Handler:** `src/bot/handlers/admin.py:show_mailing_health`
- **Клавиатура:** `get_mailing_health_kb()`
- **Описание:**
  1. Статистика активных кампаний
  2. Паузы и баны
  3. Завершено сегодня
  4. Каналы в ЧС

---

## 7. ТИПЫ УВЕДОМЛЕНИЙ (19 TYPES)

| № | Тип уведомления | Триггер | Получатель | Статус |
|---|-----------------|---------|------------|--------|
| 1 | **welcome_new_user** | Первый /start | Новый пользователь | ✅ Implemented |
| 2 | **campaign_created** | Создание кампании | Рекламодатель | ✅ Implemented |
| 3 | **campaign_started** | Запуск кампании | Рекламодатель | ✅ Implemented |
| 4 | **campaign_completed** | Завершение кампании | Рекламодатель | ⚠️ Partial |
| 5 | **campaign_error** | Ошибка кампании | Рекламодатель | ✅ Implemented |
| 6 | **request_received** | Новая заявка | Владелец канала | ✅ Implemented |
| 7 | **request_approved** | Одобрение заявки | Рекламодатель | ✅ Implemented |
| 8 | **request_rejected** | Отклонение заявки | Рекламодатель | ✅ Implemented |
| 9 | **request_auto_approved** | Автоодобрение через 24ч | Обе стороны | ⚠️ Partial |
| 10 | **post_published** | Публикация поста | Обе стороны | ✅ Implemented |
| 11 | **payout_created** | Создание выплаты | Владелец канала | ✅ Implemented |
| 12 | **payout_available** | Доступна выплата ≥500 кр | Владелец канала | ✅ Implemented |
| 13 | **low_balance** | Баланс < 100 кр | Рекламодатель | ⚠️ Partial |
| 14 | **plan_expiring** | Тариф истекает через 3 дня | Все | ❌ Not Implemented |
| 15 | **plan_expired** | Тариф истёк | Все | ❌ Not Implemented |
| 16 | **badge_earned** | Получение значка | Пользователь | ✅ Implemented |
| 17 | **level_up** | Повышение уровня | Пользователь | ⚠️ Partial |
| 18 | **referral_joined** | Реферал зарегистрировался | Реферер | ✅ Implemented |
| 19 | **broadcast** | Админ рассылка | Все пользователи | ✅ Implemented |

---

## 8. КЛАВИАТУРЫ

### 8.1 Основные меню

| Клавиатура | Файл | Описание |
|------------|------|----------|
| `get_main_menu()` | `src/bot/keyboards/main_menu.py` | Главное меню (роль-зависимое) |
| `get_onboarding_kb()` | `src/bot/keyboards/main_menu.py` | Выбор роли для нового пользователя |
| `get_advertiser_menu_kb()` | `src/bot/keyboards/main_menu.py` | Меню рекламодателя |
| `get_owner_menu_kb()` | `src/bot/keyboards/main_menu.py` | Меню владельца канала |
| `get_combined_menu_kb()` | `src/bot/keyboards/main_menu.py` | Комбинированное меню (both) |

### 8.2 Кабинет и биллинг

| Клавиатура | Файл | Описание |
|------------|------|----------|
| `get_cabinet_kb()` | `src/bot/keyboards/cabinet.py` | Личный кабинет |
| `get_notifications_prompt_kb()` | `src/bot/keyboards/cabinet.py` | Включение уведомлений |
| `get_topup_methods_kb()` | `src/bot/keyboards/billing.py` | Методы пополнения |
| `get_packages_kb()` | `src/bot/keyboards/billing.py` | Пакеты кредитов |
| `get_currency_kb()` | `src/bot/keyboards/billing.py` | Выбор криптовалюты |
| `get_plans_kb()` | `src/bot/keyboards/billing.py` | Тарифные планы |
| `get_payment_methods_kb()` | `src/bot/keyboards/billing.py` | Оплата CryptoBot |

### 8.3 Создание кампании

| Клавиатура | Файл | Описание |
|------------|------|----------|
| `get_campaign_step_kb()` | `src/bot/keyboards/campaign.py` | Навигация wizard'а |
| `get_text_type_kb()` | `src/bot/keyboards/campaign.py` | Выбор типа текста |
| `get_topics_kb()` | `src/bot/keyboards/campaign.py` | Тематики (9 шт) |
| `get_member_count_kb()` | `src/bot/keyboards/campaign.py` | Размер аудитории |
| `get_schedule_kb()` | `src/bot/keyboards/campaign.py` | Расписание |
| `get_campaign_confirm_kb()` | `src/bot/keyboards/campaign.py` | Подтверждение кампании |
| `get_image_upload_kb()` | `src/bot/keyboards/campaign.py` | Загрузка изображения |

### 8.4 AI создание кампании

| Клавиатура | Файл | Описание |
|------------|------|----------|
| `get_ai_style_keyboard()` | `src/bot/keyboards/campaign_ai.py` | Выбор стиля AI (6 шт) |
| `get_ai_category_keyboard()` | `src/bot/keyboards/campaign_ai.py` | Категории кампании (20 шт) |
| `get_ai_variants_keyboard()` | `src/bot/keyboards/campaign_ai.py` | Варианты AI текста |
| `get_campaign_editor_keyboard()` | `src/bot/keyboards/campaign_ai.py` | Редактор кампании |
| `get_audience_keyboard()` | `src/bot/keyboards/campaign_ai.py` | Выбор аудитории |
| `get_schedule_keyboard()` | `src/bot/keyboards/campaign_ai.py` | Планирование |

### 8.5 Каналы

| Клавиатура | Файл | Описание |
|------------|------|----------|
| `get_channels_menu_kb()` | `src/bot/keyboards/channels.py` | Меню базы каналов |
| `get_categories_kb()` | `src/bot/keyboards/channels.py` | Категории каналов (12 шт) |
| `get_tariff_filter_kb()` | `src/bot/keyboards/channels.py` | Фильтр по тарифам |
| `get_channel_detail_kb()` | `src/bot/keyboards/channels.py` | Детали канала |
| `get_subcategories_kb()` | `src/bot/keyboards/channels.py` | Подкатегории |
| `get_channels_pagination_kb()` | `src/bot/keyboards/channels.py` | Пагинация каналов |
| `get_channels_list_kb()` | `src/bot/handlers/channel_owner.py` | Список каналов (inline) |
| `get_channel_settings_kb()` | `src/bot/handlers/channel_owner.py` | Настройки канала |

### 8.6 Обратная связь

| Клавиатура | Файл | Описание |
|------------|------|----------|
| `get_feedback_type_kb()` | `src/bot/keyboards/feedback.py` | Тип обратной связи |
| `get_feedback_confirm_kb()` | `src/bot/keyboards/feedback.py` | Подтверждение отправки |

### 8.7 Админка

| Клавиатура | Файл | Описание |
|------------|------|----------|
| `get_admin_main_kb()` | `src/bot/keyboards/admin.py` | Главное меню админки |
| `get_admin_confirm_kb()` | `src/bot/keyboards/admin.py` | Подтверждение действия |
| `get_users_list_kb()` | `src/bot/keyboards/admin.py` | Список пользователей |
| `get_user_actions_kb()` | `src/bot/keyboards/admin.py` | Действия над пользователем |
| `get_back_kb()` | `src/bot/keyboards/admin.py` | Кнопка назад |
| `get_llm_classify_kb()` | `src/bot/keyboards/admin.py` | LLM-классификация |
| `get_mailing_health_kb()` | `src/bot/keyboards/admin.py` | Здоровье рассылок |
| `get_blacklist_kb()` | `src/bot/keyboards/admin.py` | Чёрный список (пагинация) |
| `get_blacklist_channel_kb()` | `src/bot/keyboards/admin.py` | Действия с каналом |

### 8.8 Пагинация

| Клавиатура | Файл | Описание |
|------------|------|----------|
| `get_pagination_kb()` | `src/bot/keyboards/pagination.py` | Универсальная пагинация |

---

## 9. CALLBACKDATA КЛАССЫ

| Класс | Префикс | Файл | Поля |
|-------|---------|------|------|
| `MainMenuCB` | `main` | `src/bot/keyboards/main_menu.py` | action: str, value: str |
| `ModelCB` | `model` | `src/bot/keyboards/main_menu.py` | provider: str |
| `OnboardingCB` | `onboard` | `src/bot/keyboards/main_menu.py` | role: str |
| `CampaignCB` | `campaign` | `src/bot/keyboards/campaign.py` | action: str, value: str |
| `CampaignCreateCB` | `campaign_create` | `src/bot/keyboards/campaign_ai.py` | step: str |
| `AIVariantCB` | `ai_variant` | `src/bot/keyboards/campaign_ai.py` | variant_index: int |
| `AIEditCB` | `ai_edit` | `src/bot/keyboards/campaign_ai.py` | action: str |
| `BillingCB` | `billing` | `src/bot/keyboards/billing.py` | action: str, value: str |
| `CabinetCB` | `cabinet` | `src/bot/keyboards/cabinet.py` | action: str, value: str |
| `FeedbackCB` | `feedback` | `src/bot/keyboards/feedback.py` | action: str, value: str |
| `ChannelsCB` | `channels` | `src/bot/keyboards/channels.py` | action: str, value: str, page: int |
| `AdminCB` | `admin` | `src/bot/keyboards/admin.py` | action: str, value: str |
| `PaginationCB` | `page` | `src/bot/keyboards/pagination.py` | prefix: str, page: int |

---

## 10. FSM СОСТОЯНИЯ

### 10.1 CampaignCreateState (AI создание кампании)
**Файл:** `src/bot/states/campaign_create.py`

| Состояние | Описание |
|-----------|----------|
| `selecting_style` | Выбор стиля текста |
| `selecting_category` | Выбор категории |
| `entering_custom_category` | Ввод своей категории |
| `waiting_for_description` | Ожидание описания продукта |
| `waiting_for_campaign_name` | Ввод названия кампании |
| `selecting_variant` | Выбор варианта текста |
| `editing_text` | Редактирование текста |
| `waiting_for_url` | Добавление URL |
| `waiting_for_image` | Добавление изображения |
| `selecting_audience` | Выбор аудитории |
| `setting_budget` | Настройка бюджета |
| `setting_schedule` | Настройка расписания |
| `entering_schedule_date` | Ввод даты вручную |
| `confirming` | Финальное подтверждение |

### 10.2 CampaignStates (Manual создание кампании)
**Файл:** `src/bot/states/campaign.py`

| Состояние | Описание |
|-----------|----------|
| `waiting_title` | Ожидание названия кампании |
| `waiting_topic` | Ожидание выбора тематики |
| `waiting_header` | Ожидание заголовка |
| `waiting_text` | Ожидание текста (выбор: вручную или ИИ) |
| `waiting_ai_description` | Ожидание описания для ИИ-генерации |
| `waiting_image` | Ожидание изображения (опционально) |
| `waiting_member_count` | Ожидание выбора размера аудитории |
| `waiting_schedule` | Ожидание выбора расписания |
| `waiting_confirm` | Ожидание подтверждения запуска |

### 10.3 FeedbackStates (Обратная связь)
**Файл:** `src/bot/states/feedback.py`

| Состояние | Описание |
|-----------|----------|
| `choosing_type` | Выбор типа: отзыв или баг |
| `waiting_text` | Ввод текста |
| `waiting_confirm` | Подтверждение перед отправкой |

### 10.4 AdminBalanceStates (Админ: баланс)
**Файл:** `src/bot/states/admin.py`

| Состояние | Описание |
|-----------|----------|
| `waiting_user_id` | Ввод telegram_id пользователя |
| `waiting_amount` | Ввод суммы (+ или -) |
| `waiting_reason` | Причина изменения (для лога) |

### 10.5 AdminBanStates (Админ: бан)
**Файл:** `src/bot/states/admin.py`

| Состояние | Описание |
|-----------|----------|
| `waiting_user_id` | Ввод ID пользователя |
| `waiting_reason` | Причина бана |

### 10.6 AdminBroadcastStates (Админ: рассылка)
**Файл:** `src/bot/states/admin.py`

| Состояние | Описание |
|-----------|----------|
| `waiting_message` | Текст рассылки |
| `waiting_confirm` | Подтверждение перед отправкой |

### 10.7 AdminFreeCampaignStates (Админ: бесплатная кампания)
**Файл:** `src/bot/states/admin.py`

| Состояние | Описание |
|-----------|----------|
| `waiting_title` | Название кампании |
| `waiting_text` | Текст кампании |
| `waiting_topic` | Тематика |
| `waiting_member_count` | Лимиты чатов |
| `waiting_schedule` | Расписание |
| `waiting_confirm` | Подтверждение |

### 10.8 AdminAIGenerateStates (Админ: AI генерация)
**Файл:** `src/bot/states/admin.py`

| Состояние | Описание |
|-----------|----------|
| `waiting_description` | Описание для ИИ |
| `waiting_variants` | Выбор варианта |
| `waiting_topic` | Выбор тематики |
| `waiting_member_count` | Лимиты чатов |
| `waiting_schedule` | Расписание |
| `waiting_confirm` | Подтверждение |

### 10.9 AddChannelStates (Добавление канала)
**Файл:** `src/bot/states/channel_owner.py`

| Состояние | Описание |
|-----------|----------|
| `waiting_username` | Ожидание @username канала |
| `waiting_bot_admin_confirmation` | Подтверждение что бот добавлен админом |
| `waiting_price` | Ожидание цены за пост |
| `waiting_topics` | Ожидание выбора тематик |
| `waiting_settings` | Настройки размещения |
| `waiting_confirm` | Подтверждение добавления |

### 10.10 EditChannelStates (Редактирование канала)
**Файл:** `src/bot/states/channel_owner.py`

| Состояние | Описание |
|-----------|----------|
| `waiting_new_price` | Ввод новой цены |
| `choosing_topics` | Выбор тематик |

### 10.11 OnboardingStates (Онбординг)
**Файл:** `src/bot/states/onboarding.py`

| Состояние | Описание |
|-----------|----------|
| `role_selected` | Пользователь выбрал роль |

---

## 11. ASCII НАВИГАЦИОННАЯ КАРТА

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           MARKET TELEGRAM BOT                                │
│                              NAVIGATION MAP                                  │
└─────────────────────────────────────────────────────────────────────────────┘

                                    /start
                                       │
                    ┌──────────────────┼──────────────────┐
                    │                  │                  │
              [Новый пользователь]  [Рекламодатель]   [Владелец]
                    │                  │                  │
                    ▼                  ▼                  ▼
         ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
         │   ОНБОРДИНГ     │  │  МЕНЮ РЕКЛАМО-  │  │  МЕНЮ ВЛАДЕЛЬЦА │
         │                 │  │   ДАТЕЛЯ        │  │                 │
         │ ┌─────────────┐ │  │                 │  │                 │
         │ │Выбор роли:  │ │  │ ┌─────────────┐ │  │ ┌─────────────┐ │
         │ │📣 Реклама   │ │  │ │📣 Создать   │ │  │ │📺 Мои       │ │
         │ │📺 Канал     │ │  │ │  кампанию   │ │  │ │  каналы     │ │
         │ └─────────────┘ │  │ │📋 Мои       │ │  │ │📋 Заявки    │ │
         │                 │  │ │  кампании  │ │  │ │➕ Добавить   │ │
         └────────┬────────┘  │ │📡 Каталог   │ │  │ │  канал      │ │
                  │           │ │  каналов    │ │  │ │💸 Выплаты   │ │
                  ▼           │ │💼 B2B       │ │  │ │📊 Статистика│ │
         ┌─────────────────┐  │ │📊 Статистика│ │  │ │👤 Кабинет   │ │
         │ РОЛЬ-ЗАВИСИМОЕ  │  │ │👤 Кабинет   │ │  │ │💬 Помощь    │ │
         │    МЕНЮ         │  │ │💬 Помощь    │ │  │ │✉️ Обратная  │ │
         │                 │  │ │✉️ Обратная  │ │  │ │  связь      │ │
         │ (см. ниже)      │  │ │  связь      │ │  │ │🔄 Сменить   │ │
         └─────────────────┘  │ │🔄 Сменить   │ │  │ │  роль       │ │
                              │ │  роль       │ │  │ └─────────────┘ │
                              │ └─────────────┘ │  └────────┬────────┘
                              └────────┬────────┘           │
                                       │                    │
                          ┌────────────┴────────────────────┘
                          │
                          ▼
         ┌────────────────────────────────────────────────────────┐
         │                    КОМАНДЫ БОТА                         │
         │                                                         │
         │  /start      🏠 Главное меню                           │
         │  /help       ℹ️ Справка                                 │
         │  /cabinet    👤 Личный кабинет                         │
         │  /balance    💳 Баланс                                 │
         │  /app        📱 Mini App                               │
         │  /stats      📊 Публичная статистика                   │
         │  /admin      🔐 Админ панель                           │
         │  /cancel     ✖ Отмена админа                           │
         │  /add_channel 📺 Добавить канал                        │
         │  /my_channels 📺 Мои каналы                            │
         │  /models     🤖 AI модели                              │
         │  /addchat    📊 Добавить чат для аналитики             │
         │  /b2b        🏢 B2B пакеты                             │
         └────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│                         СОЗДАНИЕ КАМПАНИИ (AI FLOW)                          │
└─────────────────────────────────────────────────────────────────────────────┘

    main:create_campaign_ai
            │
            ▼
    ┌───────────────────┐
    │ Шаг 1: Выбор      │
    │ стиля текста      │◄──── get_ai_style_keyboard()
    │ (6 вариантов)     │
    └─────────┬─────────┘
              │ campaign_create:style_{style}
              ▼
    ┌───────────────────┐
    │ Шаг 2: Выбор      │
    │ категории         │◄──── get_ai_category_keyboard()
    │ (20 + своя)       │
    └─────────┬─────────┘
              │ campaign_create:category_{cat}
              ▼
    ┌───────────────────┐
    │ Шаг 3: Описание   │
    │ продукта          │◄──── Текст (мин. 20 символов)
    └─────────┬─────────┘
              │ Сообщение
              ▼
    ┌───────────────────┐
    │ Шаг 4: Название   │
    │ кампании          │◄──── Текст (3-100 символов)
    └─────────┬─────────┘
              │ Сообщение
              ▼
    ┌───────────────────┐
    │ Шаг 5: AI         │
    │ генерация         │◄──── 3 варианта текста
    │ (3 варианта)      │
    └─────────┬─────────┘
              │ ai_variant:{index}
              ▼
    ┌───────────────────┐
    │ Шаг 6: Редактор   │
    │ текста            │◄──── get_campaign_editor_keyboard()
    │ • Изменить текст  │
    │ • Добавить URL    │
    │ • Добавить фото   │
    └─────────┬─────────┘
              │ ai_edit:confirm
              ▼
    ┌───────────────────┐
    │ Шаг 7: URL        │
    │ (опционально)     │◄──── Текст (http/https/t.me)
    └─────────┬─────────┘
              │ Сообщение или skip
              ▼
    ┌───────────────────┐
    │ Шаг 8: Изображение│
    │ (опционально)     │◄──── Фото или skip
    └─────────┬─────────┘
              │ Сообщение или skip
              ▼
    ┌───────────────────┐
    │ Шаг 9: Аудитория  │
    │ (тематика)        │◄──── get_audience_keyboard()
    └─────────┬─────────┘
              │ campaign_create:audience_{aud}
              ▼
    ┌───────────────────┐
    │ Шаг 10: Бюджет    │
    │ (мин. 100 кр)     │◄──── Текст (число)
    └─────────┬─────────┘
              │ Сообщение
              ▼
    ┌───────────────────┐
    │ Шаг 11: Расписание│
    │ • Сейчас          │◄──── get_schedule_keyboard()
    │ • Через 1ч        │
    │ • Вечером         │
    │ • Завтра          │
    │ • Custom          │
    └─────────┬─────────┘
              │ campaign_create:schedule_*
              ▼
    ┌───────────────────┐
    │ ФИНАЛ: Создание   │
    │ кампании в БД     │
    └───────────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│                       СОЗДАНИЕ КАМПАНИИ (MANUAL FLOW)                        │
└─────────────────────────────────────────────────────────────────────────────┘

    main:create_campaign
            │
            ▼
    ┌───────────────────┐
    │ Шаг 1: Тематика   │◄──── get_topics_kb() (9 шт)
    └─────────┬─────────┘
              │ campaign:topic:{topic}
              ▼
    ┌───────────────────┐
    │ Шаг 2: Заголовок  │◄──── Текст (5-255 символов)
    └─────────┬─────────┘
              │ Сообщение
              ▼
    ┌───────────────────┐
    │ Шаг 3: Тип текста │◄──── get_text_type_kb()
    │ • Вручную         │
    │ • ИИ (+10₽)       │
    └─────────┬─────────┘
              │ campaign:manual_text или ai_text
              ▼
    ┌───────────────────┐         ┌───────────────────┐
    │ РУЧНОЙ ВВОД       │         │ AI ГЕНЕРАЦИЯ      │
    │                   │         │                   │
    │ Текст 50-4000     │         │ Описание (мин.10) │
    │ Content filter    │         │ 3 варианта        │
    └─────────┬─────────┘         └─────────┬─────────┘
              │                             │
              └──────────────┬──────────────┘
                             ▼
    ┌───────────────────┐
    │ Шаг 4: Изображение│◄──── get_image_upload_kb()
    │ • Загрузить фото  │
    │ • Пропустить      │
    └─────────┬─────────┘
              │ Фото или skip
              ▼
    ┌───────────────────┐
    │ Шаг 5: Аудитория  │◄──── get_member_count_kb()
    │ (размер чатов)    │
    └─────────┬─────────┘
              │ campaign:members:{value}
              ▼
    ┌───────────────────┐
    │ Шаг 6: Расписание │◄──── get_schedule_kb()
    │ • Сейчас          │
    │ • Запланировать   │
    └─────────┬─────────┘
              │ campaign:schedule_now или later
              ▼
    ┌───────────────────┐
    │ Шаг 7: Подтвержде-│
    │ ние               │◄──── get_campaign_confirm_kb()
    │ • Запустить       │
    │ • Изменить        │
    │ • Черновик        │
    └─────────┬─────────┘
              │ campaign:confirm_*
              ▼
    ┌───────────────────┐
    │ КАМПАНИЯ СОЗДАНА  │
    └───────────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│                         ДОБАВЛЕНИЕ КАНАЛА                                    │
└─────────────────────────────────────────────────────────────────────────────┘

    /add_channel или main:add_channel
            │
            ▼
    ┌───────────────────┐
    │ Ввод @username    │◄──── Текст (@channel)
    └─────────┬─────────┘
              │ Сообщение
              ▼
    ┌───────────────────┐
    │ Проверка канала  │
    │ (существует?)     │
    └─────────┬─────────┘
              │
              ▼
    ┌───────────────────┐
    │ Добавить бота     │◄──── channel_add:check_admin
    │ админом           │
    │ (инструкция)      │
    └─────────┬─────────┘
              │ channel_add:check_admin
              ▼
    ┌───────────────────┐
    │ Верификация       │
    │ (bot.get_chat_    │
    │ member)           │
    └─────────┬─────────┘
              │
              ▼
    ┌───────────────────┐
    │ Ввод цены за пост │◄──── Текст (число, мин. 50)
    └─────────┬─────────┘
              │ Сообщение
              ▼
    ┌───────────────────┐
    │ Выбор тематик     │◄──── topic_toggle_{code} (toggle)
    │ (multiple choice) │
    └─────────┬─────────┘
              │ topics_done
              ▼
    ┌───────────────────┐
    │ Настройки         │
    │ • Лимит постов/дн │
    │ • Режим одобрения │
    └─────────┬─────────┘
              │ channel_add:settings_done
              ▼
    ┌───────────────────┐
    │ Подтверждение     │◄──── channel_add:confirm
    │ (сводка)          │
    └─────────┬─────────┘
              │
              ▼
    ┌───────────────────┐
    │ КАНАЛ ДОБАВЛЕН    │
    │ (сохранение в БД) │
    └───────────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│                         АДМИН ПАНЕЛЬ                                         │
└─────────────────────────────────────────────────────────────────────────────┘

    /admin или main:admin_panel
            │
            ▼
    ┌─────────────────────────────────────────────────────────────────────┐
    │                    ГЛАВНОЕ МЕНЮ АДМИНКИ                              │
    │                                                                      │
    │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                  │
    │  │ 📊 Статисти-│  │ 👥 Пользова-│  │ 📣 Рассылки │                  │
    │  │ ка          │  │ тели        │  │             │                  │
    │  └─────────────┘  └─────────────┘  └─────────────┘                  │
    │                                                                      │
    │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                  │
    │  │ 🚫 Чёрный   │  │ 📢 Broadcast│  │ 🧪 Тест     │                  │
    │  │ список      │  │             │  │ кампании    │                  │
    │  └─────────────┘  └─────────────┘  └─────────────┘                  │
    │                                                                      │
    │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                  │
    │  │ 🖥 Монито-   │  │ 📋 Задачи   │  │ 🧠 LLM-     │                  │
    │  │ ринг        │  │ Celery      │  │ классифика- │                  │
    │  │             │  │             │  │ ция         │                  │
    │  └─────────────┘  └─────────────┘  └─────────────┘                  │
    └─────────────────────────────────────────────────────────────────────┘
            │
            ├──────────────────────────────────────────────────────────────┐
            │                      │                      │                │
            ▼                      ▼                      ▼                ▼
    ┌─────────────┐        ┌─────────────┐        ┌─────────────┐  ┌─────────────┐
    │ СТАТИСТИКА  │        │ПОЛЬЗОВАТЕЛИ│        │ РАССЫЛКИ    │  │ ЧЁРНЫЙ     │
    │             │        │             │        │             │  │ СПИСОК     │
    │ • Всего     │        │ • Список    │        │ • Активные  │  │            │
    │ • Активные  │        │ • Детали    │        │ • Паузы     │  │ • Список   │
    │ • Забанены  │        │ • Бан       │        │ • Баны      │  │ • Причина  │
    │ • Кампании  │        │ • Баланс    │        │ • ЧС        │  │ • Разблок. │
    └─────────────┘        └─────────────┘        └─────────────┘  └─────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│                         ЛИЧНЫЙ КАБИНЕТ                                       │
└─────────────────────────────────────────────────────────────────────────────┘

    main:cabinet или /cabinet
            │
            ▼
    ┌─────────────────────────────────────────────────────────────────────┐
    │                    ЛИЧНЫЙ КАБИНЕТ                                    │
    │                                                                      │
    │  ━━━━ БАЛАНС ━━━━                                                   │
    │  💳 {credits:,} кредитов                                            │
    │  📦 Тариф: {plan}                                                   │
    │                                                                      │
    │  ━━━━ УРОВЕНЬ ━━━━                                                  │
    │  {level_name}  Уровень {level}                                      │
    │  {xp_bar}                                                           │
    │                                                                      │
    │  ━━━━ ПРОФИЛЬ ━━━━                                                  │
    │  Имя: {full_name}                                                   │
    │  Telegram: @{username}                                              │
    │                                                                      │
    │  ┌─────────────────────────────────────────────────────────────┐    │
    │  │ 💸 Вывести {payout} кр  (только owner)                       │    │
    │  │ 💰 Пополнить баланс                                          │    │
    │  │ 📦 Сменить тариф  (только advertiser)                        │    │
    │  │ 🏅 Мои значки                                                │    │
    │  │ 👥 Реферальная программа                                     │    │
    │  │ 🔔 Уведомления: ВКЛ/ВЫКЛ                                     │    │
    │  │ 🔙 В меню                                                    │    │
    │  └─────────────────────────────────────────────────────────────┘    │
    └─────────────────────────────────────────────────────────────────────┘
```

---

## 12. РЕКОМЕНДАЦИИ

### 12.1 Критические проблемы

| Приоритет | Проблема | Решение |
|-----------|----------|---------|
| **HIGH** | Flow 16 (AI финал) обрезан | Реализовать `final_create_campaign()` полностью |
| **HIGH** | Flow 14 (AI бюджет) без проверки баланса | Интегрировать с billing_service |
| **HIGH** | B2B Flow 3-4 не реализованы | Добавить детали пакета и покупку |
| **MEDIUM** | Уведомления 14-15 (тариф) не реализованы | Добавить Celery задачи для напоминаний |
| **MEDIUM** | Уведомление 13 (low_balance) частично | Добавить триггер при балансе < 100 |

### 12.2 Улучшения UX

1. **Прогресс-бары:** Добавить визуальные индикаторы прогресса для всех wizard'ов
2. **Сохранение черновиков:** Реализовать полное сохранение черновиков кампаний
3. **Предпросмотр:** Улучшить предпросмотр поста с реальным изображением
4. **Валидация:** Добавить более подробные сообщения об ошибках валидации
5. **Навигация:** Унифицировать кнопки "Назад" во всех flow

### 12.3 Технические рекомендации

1. **Типизация:** Добавить type hints во все handler'ы
2. **Логирование:** Увеличить покрытие логами критических путей
3. **Тесты:** Покрыть unit-тестами все 28 flows
4. **Документация:** Обновить README с актуальной навигационной картой

---

## ПРИЛОЖЕНИЕ A: ФАЙЛЫ ПРОЕКТА

### Обработчики (handlers)
```
src/bot/handlers/
├── start.py              # /start, онбординг, главное меню
├── campaigns.py          # Manual создание кампании
├── campaign_create_ai.py # AI создание кампании
├── channel_owner.py      # Добавление/управление каналами
├── cabinet.py            # Личный кабинет, геймификация
├── billing.py            # Пополнение, тарифы, платежи
├── feedback.py           # Обратная связь
├── admin.py              # Админ панель
├── b2b.py                # B2B маркетплейс
├── analytics.py          # Аналитика рекламодателя/владельца
├── channels_db.py        # База каналов
├── help.py               # Помощь
├── models.py             # AI модели
└── ...
```

### Клавиатуры (keyboards)
```
src/bot/keyboards/
├── main_menu.py          # Главные меню (role-dependent)
├── campaign.py           # Manual campaign wizard
├── campaign_ai.py        # AI campaign wizard
├── cabinet.py            # Личный кабинет
├── billing.py            # Биллинг и платежи
├── channels.py           # База каналов
├── feedback.py           # Обратная связь
├── admin.py              # Админ панель
└── pagination.py         # Пагинация
```

### Состояния (states)
```
src/bot/states/
├── campaign_create.py    # AI campaign FSM (14 states)
├── campaign.py           # Manual campaign FSM (9 states)
├── channel_owner.py      # Channel management FSM (6+2 states)
├── feedback.py           # Feedback FSM (3 states)
├── admin.py              # Admin FSM (18 states total)
└── onboarding.py         # Onboarding FSM (1 state)
```

---

**Конец отчёта**
