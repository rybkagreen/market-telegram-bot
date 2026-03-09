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

## 11.3 PRD VS РЕАЛИЗАЦИЯ

### 11.3.1 Таблица сравнения функций

| Функция по PRD | Статус по PRD | Статус в коде | Расхождение | Приоритет |
|----------------|---------------|---------------|-------------|-----------|
| Эскроу при запуске кампании | ✅ В PRD | ❌ Заглушка | Методы `freeze_campaign_funds()` и `release_escrow_funds()` не реализованы | 🔴 P0 |
| Предпросмотр поста (шаг 6 визарда) | ✅ В PRD | ✅ Реализовано | `preview_post` callback работает | ✅ OK |
| Умное выбор времени публикации | ❌ В PRD | ❌ Не реализовано | Не планировалось | ✅ OK |
| A/B тестирование | ✅ В PRD | ❌ Не реализовано | Нет модели CampaignVariant, handler, Celery задачи | 🔴 P1 |
| Детектор накрутки | ❌ В PRD | ❌ Не реализовано | Не планировалось | ✅ OK |
| Сравнение каналов | ❌ В PRD | ❌ Не реализовано | Не планировалось | ✅ OK |
| Медиакит канала | ❌ В PRD | ❌ Не реализовано | Не планировалось | ✅ OK |
| Автоодобрение заявок (24ч) | ✅ В PRD | ❌ Не реализовано | Нет Celery задачи `auto_approve_placement` | 🔴 P1 |
| Напоминание о заявке (20ч) | ✅ В PRD | ❌ Не реализовано | Нет Celery задачи `notify_pending_placement_reminder` | 🟡 P2 |
| Возврат средств | ✅ В PRD | ❌ Заглушка | Метод `refund_campaign()` не реализован | 🔴 P0 |
| PDF отчёт | ✅ В PRD | ⚠️ Заглушка | Handler `download_report` возвращает "🚧 Функция в разработке" | 🟡 P2 |
| История выплат | ✅ В PRD | ❌ Не реализовано | Handler `ch_payouts:{channel_id}` не найден | 🟡 P1 |
| Проверка баланса перед запуском | ✅ В PRD | ⚠️ Частично | В Flow 14 есть заглушка, нет интеграции с billing_service | 🟡 P1 |

### 11.3.2 Эскроу-механика (P0 БЛОКЕР)

**По PRD:**
> При запуске кампании средства замораживаются на эскроу-счёте. После публикации поста 80% переводится владельцу, 20% — платформе.

**По коду:**
```python
# billing_service.py — заглушка:
async def freeze_campaign_funds(campaign_id: int) -> bool:
    """Заморозить средства кампании на эскроу."""
    # TODO: Реализовать
    return False

async def release_escrow_funds(placement_id: int) -> bool:
    """Освободить средства эскроу после публикации."""
    # TODO: Реализовать
    return False
```

**Проблема:** В `confirm_launch()` (campaigns.py:830) **нет вызова** `freeze_campaign_funds()`. Средства не замораживаются.

**Где должно быть:**
```python
# campaigns.py:830-900 — confirm_launch
async def confirm_launch(callback: CallbackQuery, state: FSMContext) -> None:
    # ... проверки ...
    
    # ✅ ДОЛЖНО БЫТЬ:
    frozen = await billing_service.freeze_campaign_funds(campaign.id)
    if not frozen:
        await callback.answer("❌ Ошибка заморозки средств", show_alert=True)
        return
    
    # Запуск рассылки
    await send_campaign.delay(campaign.id)
```

### 11.3.3 A/B тестирование (P1 БЛОКЕР)

**По PRD:**
> Рекламодатель создаёт 2 варианта текста. Бот отправляет каждый вариант 50% аудитории. Через 24 часа сравнивается CTR и определяется победитель.

**По коду:**
- ❌ Нет модели `CampaignVariant`
- ❌ Нет handler для создания вариантов
- ❌ Нет Celery задачи для сравнения результатов
- ❌ Нет уведомления о результате

**Где должно быть:**
```python
# campaign_create_ai.py — после выбора варианта:
@router.callback_query(AIEditCB.filter(F.action == "create_ab_test"))
async def create_ab_test(callback: CallbackQuery) -> None:
    """Создать A/B тест с двумя вариантами."""
    # TODO: Реализовать
    # 1. Сгенерировать второй вариант
    # 2. Сохранить оба варианта
    # 3. Разделить аудиторию 50/50
    # 4. Запустить рассылку
```

---

## 12. ДОПОЛНИТЕЛЬНЫЕ FLOW (УСТРАНЕНИЕ ПРОБЕЛОВ)

### 12.1 Пропущенные flow (3.7-3.10, 3.13-3.15, 3.18, 3.20-3.27)

#### Flow 3.7: Детальная страница кампании
**Статус:** ❌ НЕ РЕАЛИЗОВАНО

**Точка входа:**
- Команда: `/campaigns` → `cabinet.py:show_campaigns_list`
- Callback: `main:my_campaigns` → выбор кампании из списка

**Файл:** `src/bot/handlers/cabinet.py:406-540`

**Описание:**
В текущей реализации **отдельной детальной страницы кампании нет**. Список кампаний показывается в `show_campaigns_list()`, но переход на детальную страницу не реализован.

**Что отображается в списке:**
```python
text += (
    f"{emoji} <b>{campaign.title}</b>\n"
    f"   Статус: {status_value}  |  Прогресс: {progress:.0f}%\n"
    f"   Создана: {created}\n"
    f"   Отправлено: {campaign.sent_count}/{campaign.total_chats}\n\n"
)
```

**Кнопки по статусам (НЕ РЕАЛИЗОВАНЫ):**
- Черновик: [редактировать] [удалить] [запустить] — ❌ Нет
- В очереди: [отменить] — ❌ Нет
- Активная: [пауза] [отменить] — ❌ Нет
- Завершённая: [аналитика] [дублировать] — ⚠️ Только аналитика через `main:ai_campaign_analytics`
- Ошибка: [что показывается] — ❌ Нет
- Заблокирована: [что показывается, как оспорить] — ❌ Нет

**Где должна быть реализована:**
```python
# Требуется добавить:
@router.callback_query(CampaignCB.filter(F.action == "detail"))
async def show_campaign_detail(callback: CallbackQuery, callback_data: CampaignCB) -> None:
    """Показать детальную страницу кампании."""
    # TODO: Реализовать
```

---

#### Flow 3.8: Управление активной кампанией
**Статус:** ❌ НЕ РЕАЛИЗОВАНО

**Требуемые функции:**
1. Поставить на паузу → что происходит в БД и Celery
2. Снять с паузы
3. Отменить оставшиеся публикации
4. Отображение прогресса (N из M каналов)

**По коду:**
В `src/bot/handlers/campaigns.py` есть только `confirm_launch()` для запуска. Функции паузы/отмены **отсутствуют**.

**Где должно быть:**
```python
# Требуется добавить:
@router.callback_query(CampaignCB.filter(F.action == "pause"))
async def pause_campaign(callback: CallbackQuery) -> None:
    """Поставить кампанию на паузу."""
    # TODO: Реализовать

@router.callback_query(CampaignCB.filter(F.action == "resume"))
async def resume_campaign(callback: CallbackQuery) -> None:
    """Снять кампанию с паузы."""
    # TODO: Реализовать

@router.callback_query(CampaignCB.filter(F.action == "cancel"))
async def cancel_campaign(callback: CallbackQuery) -> None:
    """Отменить кампанию."""
    # TODO: Реализовать
```

**Проблема:** В `campaigns.py:960` есть `CampaignCB.filter(F.action == "cancel")`, но это отмена визарда создания, не активной кампании.

---

#### Flow 3.9: Аналитика кампании
**Статус:** ⚠️ ЧАСТИЧНО (только AI-аналитика)

**Точка входа:**
- Callback: `main:ai_campaign_analytics` → `campaign_analytics.py:show_ai_campaign_analytics`
- Файл: `src/bot/handlers/campaign_analytics.py:32-263`

**Что реализовано:**
1. Список кампаний для выбора (`show_campaign_list_kb`)
2. AI-анализ кампании (`analyze_campaign`)
3. Метрики: охват, ER, CTR, ROI, CPM — ⚠️ Заглушки

**Код анализа:**
```python
# campaign_analytics.py:134-262
@router.callback_query(CampaignAICB.filter(F.action == "analyze"))
async def analyze_campaign(callback: CallbackQuery, callback_data: CampaignAICB) -> None:
    """AI-анализ кампании."""
    campaign_id = int(callback_data.campaign_id)
    
    # Получаем кампанию
    async with async_session_factory() as session:
        campaign = await session.get(Campaign, campaign_id)
        
    # Запрашиваем AI анализ
    analysis = await ai_service.analyze_campaign(campaign)
    
    text = f"📊 <b>AI-анализ кампании</b>\n\n{analysis}"
```

**Что НЕ реализовано:**
- ❌ PDF-отчёт: `notifications.py:145` — заглушка `await callback.answer("🚧 Функция в разработке")`
- ❌ A/B сравнение: нет handler
- ❌ Детальные метрики по каждому каналу: нет

---

#### Flow 3.10: Дублирование кампании
**Статус:** ❌ НЕ РЕАЛИЗОВАНО

**Где должно быть:**
- Кнопка "Дублировать" на детальной странице кампании (Flow 3.7)
- Handler для копирования данных кампании

**Требуемый код:**
```python
@router.callback_query(CampaignCB.filter(F.action == "duplicate"))
async def duplicate_campaign(callback: CallbackQuery) -> None:
    """Дублировать кампанию."""
    # TODO: Реализовать
    # Копировать: title, topic, header, text, filters
    # Не копировать: status, sent_count, created_at
```

---

#### Flow 3.13: История транзакций
**Статус:** ✅ РЕАЛИЗОВАНО (только пополнения)

**Точка входа:**
- Команда: `/balance` → `billing.py:show_balance`
- Callback: `billing:history` → `billing.py:show_history`

**Файл:** `src/bot/handlers/billing.py:548-588`

**Что реализовано:**
```python
@router.callback_query(BillingCB.filter(F.action == "history"))
async def show_history(callback: CallbackQuery) -> None:
    """История пополнений кредитов."""
    async with async_session_factory() as session:
        from sqlalchemy import select
        
        from src.db.models.crypto_payment import CryptoPayment
        
        # Получаем последние 10 платежей
        stmt = (
            select(CryptoPayment)
            .where(CryptoPayment.user_id == user.id)
            .order_by(CryptoPayment.created_at.desc())
            .limit(10)
        )
        result = await session.execute(stmt)
        payments = list(result.scalars().all())
```

**Что отображается:**
- Дата
- Сумма в кредитах
- Валюта (USDT/TON/BTC/ETH/LTC)
- Статус (pending/paid/failed)

**Чего нет:**
- ❌ Пагинация (только последние 10)
- ❌ История расходов (списания за кампании)
- ❌ История выплат (для владельцев)

---

#### Flow 3.14: Просмотр текущего тарифа
**Статус:** ⚠️ ЧАСТИЧНО (отображается в кабинете)

**Где отображается:**
1. `/start` — в приветствии: `📦 Тариф: {plan_value}`
2. `/cabinet` — в кабинете: `📦 Тариф: {plan_value}`
3. `/balance` — в балансе: `Тариф: {plan_value}`

**Файл:** `src/bot/handlers/cabinet.py:199-260`

**Что показывается:**
- Название тарифа (FREE/STARTER/PRO/BUSINESS)
- Дата окончания (если есть): `до {plan_expires_at.strftime('%d.%m')} ({days_left} дней)`
- Осталось кампаний: `Осталось кампаний: {remaining_campaigns} из {plan_limit}` — ⚠️ Заглушка

**Чего нет:**
- ❌ Отдельной страницы тарифа
- ❌ Детального описания лимитов тарифа
- ❌ Истории смены тарифов

---

#### Flow 3.15: Смена тарифа
**Статус:** ⚠️ ЧАСТИЧНО (только выбор, оплата не работает)

**Точка входа:**
- Callback: `billing:plans` → `billing.py:show_plans`
- Выбор тарифа: `billing:plan` → `billing.py:plan_selected`

**Файл:** `src/bot/handlers/billing.py:476-547`

**Что реализовано:**
```python
@router.callback_query(BillingCB.filter(F.action == "plan"))
async def plan_selected(callback: CallbackQuery, callback_data: BillingCB) -> None:
    """Выбрать и активировать тариф (списывает кредиты)."""
    plan = callback_data.value
    
    # Проверяем баланс
    if user.credits < plan_price:
        await callback.answer("❌ Недостаточно кредитов", show_alert=True)
        return
    
    # TODO: Списать кредиты и активировать тариф
```

**Проблема:** В коде **заглушка** — функция активации тарифа не реализована.

---

#### Flow 3.18: Настройки канала
**Статус:** ⚠️ ЧАСТИЧНО (кнопки есть, handler нет)

**Точка входа:**
- Callback: `ch_settings:{channel_id}` → `channel_owner.py:show_channel_settings`

**Файл:** `src/bot/handlers/channel_owner.py:855-877`

**Что можно менять:**
```python
keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="💰 Изменить цену", callback_data=f"ch_edit_price:{channel_id}")],
    [InlineKeyboardButton(text="🏷 Изменить тематики", callback_data=f"ch_edit_topics:{channel_id}")],
    [InlineKeyboardButton(text="◀️ Назад", callback_data=f"channel_menu:{channel_id}")],
])
```

**Реализованные handler:**
- ❌ `ch_edit_price:{channel_id}` — НЕ НАЙДЕН
- ❌ `ch_edit_topics:{channel_id}` — НЕ НАЙДЕН
- ✅ `ch_settings:` — показывает меню настроек

**Проблема:** Кнопки есть, handler для редактирования **не реализованы**.

---

#### Flow 3.20: Аналитика канала
**Статус:** ⚠️ ЧАСТИЧНО (только для владельца в analytics.py)

**Точка входа:**
- Callback: `owner_analytics:channel:{channel_id}` → `analytics.py`

**Файл:** `src/bot/handlers/analytics.py:175-280`

**Что реализовано:**
```python
@router.callback_query(F.data.startswith("owner_analytics:channel:"))
async def show_channel_analytics(callback: CallbackQuery) -> None:
    """Показать аналитику канала."""
    channel_id = int((callback.data or "").split(":")[2])
    
    # Получаем канал
    async with async_session_factory() as session:
        channel = await session.get(TelegramChat, channel_id)
        
    text = (
        f"📊 <b>Аналитика канала</b>\n\n"
        f"📡 @{channel.username}\n"
        f"👥 Подписчиков: {channel.member_count:,}\n"
        f"📈 ER: {channel.er:.2f}%\n"
        f"⭐ Рейтинг: {channel.rating:.1f}\n"
    )
```

**Чего нет:**
- ❌ Динамика подписчиков (график)
- ❌ История размещений
- ❌ История выплат
- ❌ Средняя оценка от рекламодателей

---

#### Flow 3.24: Каталог каналов + фильтры
**Статус:** ✅ РЕАЛИЗОВАНО

**Точка входа:**
- Команда: `/channels`
- Callback: `main:channels_db` → `channels_db.py:show_channels_menu`

**Файл:** `src/bot/handlers/channels_db.py:1-536`

**Доступные фильтры:**
1. **Категории:** `channels:category` → выбор из 10 категорий
2. **Подкатегории:** `channels:subcategories` → выбор из подкатегорий
3. **Тариф:** `channels:tariff` → фильтр по доступности на тарифе
4. **ER:** `channels:filter_er` → минимальный ER
5. **Рейтинг:** `channels:filter_rating` → минимальный рейтинг
6. **Fraud:** `channels:filter_fraud` → исключить fraud-каналы

**Клавиатуры:**
- `get_categories_kb()` — категории
- `get_tariff_filter_kb()` — фильтр по тарифу
- `get_channels_menu_kb()` — главное меню

**Пагинация:** ✅ Реализована через `PaginationCB`

**Проблема:** Фильтры применяются **последовательно**, не одновременно. Нельзя выбрать "IT + ER > 5% + рейтинг > 70".

---

#### Flow 3.25: Детальная страница канала
**Статус:** ❌ НЕ РЕАЛИЗОВАНО

**Где должна быть:**
- Кнопка "Подробнее" в каталоге каналов
- Handler для отображения детальной информации

**Требуемый код:**
```python
@router.callback_query(ChannelsCB.filter(F.action == "channel_detail"))
async def show_channel_detail(callback: CallbackQuery, callback_data: ChannelsCB) -> None:
    """Показать детальную страницу канала."""
    channel_id = int(callback_data.value)
    
    # Получить канал из БД
    # Показать: описание, метрики, последние посты, историю рейтинга, отзывы
    # Кнопки: "Добавить в кампанию", "Сравнить", "Запросить медиакит"
    
    # TODO: Реализовать
```

---

#### Flow 3.26: Отзыв о канале
**Статус:** ⚠️ ЧАСТИЧНО (только в campaigns.py)

**Точка входа:**
- Автоматически после завершения кампании
- Callback: `review_request:{campaign_id}` → `campaigns.py:show_review_request`

**Файл:** `src/bot/handlers/campaigns.py:1013-1092`

**Что реализовано:**
```python
@router.callback_query(F.data.startswith("review_request:"))
async def show_review_request(callback: CallbackQuery) -> None:
    """Запросить отзыв о канале."""
    campaign_id = int((callback.data or "").split(":")[1])
    
    text = (
        f"📋 <b>Оцените канал</b>\n\n"
        f"Кампания: {campaign.title}\n"
        f"Канал: @{channel.username}\n\n"
        f"Оцените по параметрам:\n"
        f"• Соответствие тематике\n"
        f"• Качество аудитории\n"
        f"• Скорость размещения\n\n"
        f"По звёздам (1-5):"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐⭐⭐⭐⭐", callback_data=f"review_submit:{campaign_id}:5")],
        [InlineKeyboardButton(text="⭐⭐⭐⭐", callback_data=f"review_submit:{campaign_id}:4")],
        # ... 1-5 звёзд
        [InlineKeyboardButton(text="⏭ Пропустить", callback_data="review_skip")],
    ])
```

**Что НЕ реализовано:**
- ❌ Текстовый комментарий (опционально)
- ❌ Сохранение отзыва в БД
- ❌ Отображение отзывов в детальной странице канала

---

#### Flow 3.27: Отзыв владельца о рекламодателе
**Статус:** ❌ НЕ РЕАЛИЗОВАНО

**Где должен быть:**
- Автоматически после завершения размещения
- Handler для запроса и сохранения отзыва

**Требуемый код:**
```python
@router.callback_query(F.data.startswith("review_owner_request:"))
async def show_owner_review_request(callback: CallbackQuery) -> None:
    """Запросить отзыв владельца о рекламодателе."""
    # TODO: Реализовать
    # Аналогично Flow 3.26, но для владельца
```

---

### 12.2 Flow 3.19: Заявки на размещение (детализация)

**Статус:** ✅ РЕАЛИЗОВАНО

**Точка входа:**
- Callback: `main:my_requests` → `start.py:go_to_my_requests`
- Callback: `ch_requests:{channel_id}` → `channel_owner.py:show_channel_requests`

**Файл:** `src/bot/handlers/channel_owner.py:900-1150`

**Точный текст уведомления:**
```python
card_text = (
    f"📋 <b>Заявка #{placement.id}</b>  •  @{placement.chat.username if placement.chat else 'канал'}\n"
    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    f"<b>ТЕКСТ ПОСТА:</b>\n\n"
    f"{campaign.text[:500]}{'...' if len(campaign.text) > 500 else ''}\n\n"
)

if campaign.url:
    card_text += f"🔗 Ссылка: {campaign.url}\n"

if campaign.image_file_id:
    card_text += "🖼 Медиа: изображение прикреплено\n"

card_text += (
    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    f"📅 Желаемое время: {placement.scheduled_at.strftime('%d.%m.%Y %H:%M') if placement.scheduled_at else 'Как можно скорее'}\n"
    f"⏱ Заявка истекает через: {hours_left} ч {mins_left} мин\n"
    f"💰 Ваша выплата: {payout_amount} кр (80% от {placement.cost} кр)\n"
    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    f"ℹ️ Рекламодатель: {advertiser_campaigns_count} кампаний"
)
```

**Кнопки:**
```python
keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve_placement:{placement_id}")],
    [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_placement_reason:{placement_id}")],
    [InlineKeyboardButton(text="✏️ Запросить правки", callback_data=f"request_changes_placement:{placement_id}")],
    [InlineKeyboardButton(text="🔙 Назад", callback_data=f"ch_requests:{placement.chat_id if placement.chat else 0}")],
])
```

**FSM для причины отклонения:**
```python
# ❌ НЕ РЕАЛИЗОВАНО
# Требуется добавить:
class RejectPlacementStates(StatesGroup):
    waiting_reason = State()

@router.callback_query(F.data.startswith("reject_placement_reason:"))
async def reject_placement_reason(callback: CallbackQuery, state: FSMContext) -> None:
    """Запросить причину отклонения."""
    await state.set_state(RejectPlacementStates.waiting_reason)
    await callback.message.answer("Введите причину отклонения:")
```

**Автоодобрение через 24 часа:**
```python
# ❌ НЕ РЕАЛИЗОВАНО
# Требуется Celery задача:
@celery_app.task(bind=True, max_retries=3)
def auto_approve_placement(self, placement_id: int) -> None:
    """Автоодобрение заявки через 24 часа."""
    # TODO: Реализовать
    # 1. Проверить, не было ли решения владельца
    # 2. Если нет → одобрить автоматически
    # 3. Перевести в QUEUED
```

---

### 12.3 Flow 3.21: Запрос выплаты

**Статус:** ❌ НЕ РЕАЛИЗОВАНО

**Точка входа:**
- Callback: `main:payouts` → `start.py:go_to_payouts`
- Callback: `ch_payouts:{channel_id}` → ❌ НЕ НАЙДЕН

**Файл:** `src/bot/handlers/start.py:645-668`

**Текущая реализация:**
```python
@router.callback_query(MainMenuCB.filter(F.action == "payouts"))
async def go_to_payouts(callback: CallbackQuery) -> None:
    """Показать экран выплат владельца."""
    text = (
        "💸 <b>Выплаты</b>\n\n"
        "Управление выплатами доступно в разделе «Мои каналы».\n\n"
        "Выплаты автоматически создаются после публикации "
        "рекламного поста в вашем канале.\n"
        "80% от стоимости размещения поступает вам, "
        "20% — комиссия платформы."
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="📺 Мои каналы", callback_data=MainMenuCB(action="my_channels"))
    builder.button(text="🔙 В меню", callback_data=MainMenuCB(action="main_menu"))
    builder.adjust(1, 1)
    
    await safe_callback_edit(callback, text, reply_markup=builder.as_markup())
```

**Проблема:** Это **информационный экран**, не функциональный. Нет:
- ❌ Кнопки "Запросить выплату"
- ❌ Выбора метода (USDT/TON)
- ❌ Ввода адреса кошелька
- ❌ Истории выплат

**Где должна быть реализация:**
```python
# Требуется добавить:
@router.callback_query(F.data.startswith("ch_payouts:"))
async def show_channel_payouts(callback: CallbackQuery) -> None:
    """Показать выплаты канала."""
    # TODO: Реализовать
    # 1. Получить доступную сумму (payout_repo.get_available_payout_amount)
    # 2. Показать кнопки: "Запросить выплату", "История"
    
@router.callback_query(F.data.startswith("request_payout:"))
async def request_payout(callback: CallbackQuery, state: FSMContext) -> None:
    """Запросить выплату."""
    # TODO: Реализовать FSM
    # 1. Выбор метода: USDT / TON
    # 2. Ввод адреса кошелька
    # 3. Подтверждение
    # 4. Создание Payout
```

---

### 12.4 Flow 3.11 vs 3.12: Пополнение баланса (CryptoBot vs Stars)

**Статус:** ⚠️ ЧАСТИЧНО (оба реализованы, но есть баги)

#### Flow 3.11: CryptoBot

**Точка входа:**
- Callback: `billing:topup_crypto` → `billing.py:show_crypto_packages`

**Файл:** `src/bot/handlers/billing.py:131-363`

**Курс конвертации:**
```python
# settings.py
credits_per_usdt: int = Field(90, alias="CREDITS_PER_USDT")
credits_per_ton: int = Field(400, alias="CREDITS_PER_TON")
credits_per_btc: int = Field(9_000_000, alias="CREDITS_PER_BTC")
credits_per_eth: int = Field(300_000, alias="CREDITS_PER_ETH")
credits_per_ltc: int = Field(7_000, alias="CREDITS_PER_LTC")
```

**Баг (HTTP 400):**
В `cryptobot_service.py` есть проблема с созданием инвойса:
```python
# cryptobot_service.py:78-95
async def create_invoice(self, currency: str, amount: float, ...) -> CryptoPayment:
    try:
        invoice = await self.client.createInvoice(
            currency=currency,
            amount=amount,
            payload=payload_str,
            description=description,
        )
    except Exception as e:
        # ❌ Ловит все ошибки, не логирует детали
        # ❌ Возвращает заглушку вместо обработки
        logger.error(f"CryptoBot error: {e}")
        raise
```

**Проблема:** При создании инвойса CryptoBot возвращает HTTP 400, если:
- `amount` < минимального (0.001 USDT)
- `payload` > 100 символов
- Токен невалидный

#### Flow 3.12: Telegram Stars

**Точка входа:**
- Callback: `billing:topup_stars` → `billing.py:show_stars_packages`

**Файл:** `src/bot/handlers/billing.py:364-475`

**Курс конвертации:**
```python
# settings.py
credits_per_star: int = Field(2, alias="CREDITS_PER_STAR")
```

**Обработка платежа:**
```python
@router.message(F.successful_payment)
async def stars_payment_success(message: Message) -> None:
    """Обработать успешный Stars платёж."""
    # ✅ Реализовано
    # 1. Получить сумму из successful_payment
    # 2. Конвертировать в кредиты
    # 3. Зачислить на баланс
    # 4. Создать Transaction
```

**Различия:**
| Параметр | CryptoBot | Stars |
|----------|-----------|-------|
| Минимум | ~0.001 USDT (90 кр) | 50 Stars (100 кр) |
| Комиссия | ~1% | ~30% (Telegram) |
| Обработка | Webhook (Celery) | Instant (handler) |
| Статусы | pending/paid/failed | paid/failed |

---

## 13. ДОПОЛНИТЕЛЬНЫЕ РАЗДЕЛЫ

### 13.1 Пропущенные типы уведомлений

|Тип|Статус|Где должно быть|
|---|------|---------------|
|Напоминание об ожидающей заявке (за 4 часа)|❌ НЕ РЕАЛИЗОВАНО|`notifications.py` + Celery Beat|
|Кампания завершена + ссылка на отчёт|⚠️ ЧАСТИЧНО|`notifications.py:format_campaign_done`|
|Возврат средств за несостоявшееся размещение|❌ НЕ РЕАЛИЗОВАНО|`billing_service.py`|
|A/B результат готов (через 24 ч)|❌ НЕ РЕАЛИЗОВАНО|`notifications.py` + Celery|
|Еженедельный дайджест (advertiser)|✅ РЕАЛИЗОВАНО|`notification_tasks.py:send_weekly_digest`|
|Еженедельный дайджест (owner)|✅ РЕАЛИЗОВАНО|`notification_tasks.py:send_weekly_digest`|

---

### 13.2 FSM тупики (Dead-ends)

**Анализ FSM матрицы из раздела 10:**

#### CampaignCreateState (AI wizard)

|Состояние|Кнопка "Назад"|Кнопка "Отмена"|Статус|
|---------|-------------|---------------|------|
|`selecting_style`|❌ Нет|❌ Нет|🔴 ТУПИК|
|`selecting_category`|✅ Есть (`back_to_style`)|❌ Нет|⚠️ Частично|
|`entering_custom_category`|✅ Есть (`back_to_category`)|❌ Нет|⚠️ Частично|
|`waiting_for_description`|❌ Нет|❌ Нет|🔴 ТУПИК|
|`waiting_for_campaign_name`|❌ Нет|❌ Нет|🔴 ТУПИК|
|`selecting_variant`|✅ Есть (`back_to_category`)|❌ Нет|⚠️ Частично|
|`editing_text`|❌ Нет|❌ Нет|🔴 ТУПИК|
|`waiting_for_url`|✅ Есть (`skip_url`)|❌ Нет|⚠️ Частично|
|`waiting_for_image`|✅ Есть (`skip_image`)|❌ Нет|⚠️ Частично|
|`selecting_audience`|✅ Есть (`back_to_image`)|❌ Нет|⚠️ Частично|
|`setting_budget`|❌ Нет|❌ Нет|🔴 ТУПИК|
|`setting_schedule`|✅ Есть (`back_to_budget`)|❌ Нет|⚠️ Частично|
|`entering_schedule_date`|❌ Нет|❌ Нет|🔴 ТУПИК|
|`confirming`|❌ Нет|❌ Нет|🔴 ТУПИК|

**Итого:** 7 тупиков из 14 состояний (50%)

#### CampaignStates (Manual wizard)

|Состояние|Кнопка "Назад"|Кнопка "Отмена"|Статус|
|---------|-------------|---------------|------|
|`waiting_topic`|✅ Есть|✅ Есть|✅ OK|
|`waiting_header`|❌ Нет|❌ Нет|🔴 ТУПИК|
|`waiting_text`|✅ Есть|✅ Есть|✅ OK|
|`waiting_ai_description`|❌ Нет|❌ Нет|🔴 ТУПИК|
|`waiting_image`|✅ Есть|✅ Есть|✅ OK|
|`waiting_member_count`|✅ Есть|✅ Есть|✅ OK|
|`waiting_schedule`|✅ Есть|✅ Есть|✅ OK|
|`waiting_confirm`|✅ Есть|✅ Есть|✅ OK|

**Итого:** 2 тупика из 9 состояний (22%)

#### AddChannelStates

|Состояние|Кнопка "Назад"|Кнопка "Отмена"|Статус|
|---------|-------------|---------------|------|
|`waiting_username`|❌ Нет|❌ Нет|🔴 ТУПИК|
|`waiting_bot_admin_confirmation`|✅ Есть (`back_to_username`)|❌ Нет|⚠️ Частично|
|`waiting_price`|❌ Нет|❌ Нет|🔴 ТУПИК|
|`waiting_topics`|✅ Есть (`back_to_price`)|❌ Нет|⚠️ Частично|
|`waiting_settings`|✅ Есть (`back_to_topics`)|❌ Нет|⚠️ Частично|
|`waiting_confirm`|✅ Есть (`back_to_settings`)|❌ Нет|⚠️ Частично|

**Итого:** 2 тупика из 6 состояний (33%)

---

### 13.3 Throttling

**Статус:** ✅ РЕАЛИЗОВАНО

**Файл:** `src/bot/middlewares/throttling.py`

**Лимиты:**
```python
THROTTLE_TIME = 0.5  # секунды между запросами
```

**Что ограничивается:**
- Все сообщения (`Message`)
- Все callback query (`CallbackQuery`)
- Все обновления (`Update`)

**Сообщение при превышении:**
```python
if isinstance(event, Message):
    await event.answer("⏳ Подождите немного...")
elif isinstance(event, CallbackQuery):
    await event.answer("⏳ Подождите немного...", show_alert=False)
```

**Проблема:** Лимит **0.5 секунды** слишком мал для пользователей. Рекомендуется увеличить до 1-2 секунд.

**Где применяется:**
```python
# bot/main.py — middleware registration:
dp.update.middleware(ThrottlingMiddleware(redis))
```

---

### 13.4 Дополнительные handlers (без flow)

#### channels_db.py

**Назначение:** База каналов — статистика, поиск по категориям, фильтры.

**Точки входа:**
- `main:channels_db` → `show_channels_menu()`
- `channels:stats` → `handle_channels_stats()`
- `channels:categories` → `handle_categories()`
- `channels:category` → `handle_category_selected()`
- `channels:subcategories` → `handle_subcategories()`
- `channels:tariff` → `handle_tariff_filter()`
- `channels:top_channels` → `handle_top_channels()`
- `channels:advanced_filters` → `handle_advanced_filters()`
- `channels:filter_er` → `handle_er_filter()`
- `channels:filter_rating` → `handle_rating_filter()`
- `channels:filter_fraud` → `handle_fraud_filter()`
- `channels:menu` → `handle_channels_menu()`

**Flow:** Пользователь выбирает категорию → применяются фильтры → показывается список каналов с пагинацией.

---

#### templates.py

**Назначение:** Библиотека шаблонов рекламных текстов.

**Точки входа:**
- `main:templates` → `handle_templates_menu()`
- `campaign:template_category` → `handle_category_selected()`
- `campaign:template_preview` → `handle_template_preview()`
- `campaign:template_use` → `handle_template_use()`

**Flow:** Пользователь выбирает категорию → выбирает шаблон → просматривает → использует в визарде создания кампании.

**Связь с Flow 17:** После выбора шаблона переход на `CampaignStates.waiting_title`.

---

#### models.py

**Назначение:** Выбор AI модели (для админов).

**Точки входа:**
- Команда: `/models` → `handle_models()`
- `model:tariff_info` → `handle_tariff_info()`
- `model:select` → `handle_model_select()`
- `model:back` → `handle_model_back()`

**Доступ:** Только для админов (`is_admin(user_id)`).

**Проблема:** Для обычных пользователей команда `/models` показывает заглушку.

---

#### monitoring.py

**Назначение:** Мониторинг сервера и задач Celery (admin only).

**Точки входа:**
- `admin:server_monitoring` → `show_server_monitoring()`
- `admin:celery_tasks` → `show_celery_tasks()`

**Статус:** ⚠️ Заглушки. Реальные данные требуют SSH/API доступа.

---

### 13.5 Исправление ошибок в FSM

#### Ошибка: waiting_title vs waiting_topic

**Проблема:** В разделе 10.2 указано состояние `waiting_title`, но в Flow 17 первым шагом указан `waiting_topic`.

**Реальность по коду:**
```python
# campaigns.py:56-100
@router.callback_query(MainMenuCB.filter(F.action == "create_campaign"))
async def start_campaign_wizard(callback: CallbackQuery, state: FSMContext) -> None:
    """Начать wizard создания кампании."""
    text = (
        "📝 <b>Создание кампании</b>\n\n"
        "Шаг 1 из 7: Выберите тематику вашей кампании."
    )
    await safe_callback_edit(callback, text, reply_markup=get_topics_kb())
    await state.set_state(CampaignStates.waiting_topic)  # ✅ ПЕРВЫЙ ШАГ
```

**CampaignStates (campaign.py:8-32):**
```python
class CampaignStates(StatesGroup):
    waiting_title = State()       # ❌ НЕ ИСПОЛЬЗУЕТСЯ
    waiting_topic = State()       # ✅ ШАГ 1
    waiting_header = State()      # ✅ ШАГ 2 (заголовок, не title)
    waiting_text = State()        # ✅ ШАГ 3
    waiting_ai_description = State()  # ✅ Для AI генерации
    waiting_image = State()       # ✅ ШАГ 4
    waiting_member_count = State()  # ✅ ШАГ 5
    waiting_schedule = State()    # ✅ ШАГ 6
    waiting_confirm = State()     # ✅ ШАГ 7
```

**Исправление:** `waiting_title` — **мёртвое состояние**, не используется. Должно быть удалено или переименовано в `waiting_header`.

---

### 13.6 Исправления по клавиатурам

#### get_channels_list_kb() и get_channel_settings_kb()

**Проблема:** В разделе 8.5 указано:
```
get_channels_list_kb()  → src/bot/handlers/channel_owner.py
get_channel_settings_kb() → src/bot/handlers/channel_owner.py
```

**Реальность:** Эти клавиатуры **не являются отдельными функциями**. Они создаются inline в handler'ах `channel_owner.py`:

```python
# channel_owner.py:796-850
keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="📊 Статистика", callback_data=f"ch_stats:{channel_id}")],
    [InlineKeyboardButton(text="⚙️ Настройки", callback_data=f"ch_settings:{channel_id}")],
    [InlineKeyboardButton(text="📋 Заявки", callback_data=f"ch_requests:{channel_id}")],
    [InlineKeyboardButton(text="◀️ Назад", callback_data="my_channels_back")],
])
```

**Исправление:** Это не отдельные функции, а inline клавиатуры, создаваемые в `channel_owner.py`.

---

## 14. РЕКОМЕНДАЦИИ

### 14.1 Критические проблемы

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

## 13. ТАБЛИЦА КОМАНД И ВЫЗОВОВ FLOW

### 13.1 Полная таблица вызова всех flow (42 flow)

В данной таблице представлены все 42 пользовательских потока системы: 28 основных пользовательских flows, 4 B2B flows, 3 gamification flows, 6 admin flows и 1 analytics flow.

| Flow # | Название | Команда/Callback | Файл хендлера | Строка | FSM State | Следующий flow |
|--------|----------|------------------|---------------|--------|-----------|----------------|
| **ОНБОРДИНГ И РЕГИСТРАЦИЯ** |
| 1 | Онбординг нового | /start (новый) | `src/bot/handlers/start.py:_handle_start` | 175 | `OnboardingStates.role_selected` | 2, 3, или 4 |
| 2 | Возвращающийся (рекламодатель) | /start (advertiser) | `src/bot/handlers/start.py:_handle_start` | 175 | — | 5 или 17 |
| 3 | Возвращающийся (владелец) | /start (owner) | `src/bot/handlers/start.py:_handle_start` | 175 | — | 22, 26 |
| 4 | Смена роли | `main:change_role` | `src/bot/handlers/start.py:change_role` | 518 | — | 2 или 3 |
| **AI СОЗДАНИЕ КАМПАНИИ (12 flows)** |
| 5 | AI кампания — стиль | `main:create_campaign_ai` | `src/bot/handlers/campaign_create_ai.py:start_campaign_create` | 40 | `CampaignCreateState.selecting_style` | 6 |
| 6 | AI кампания — категория | `campaign_create:style_{style}` | `src/bot/handlers/campaign_create_ai.py:style_selected` | 72 | `CampaignCreateState.selecting_category` | 7 |
| 7 | AI кампания — описание продукта | `campaign_create:category_{cat}` | `src/bot/handlers/campaign_create_ai.py:category_selected` | 120 | `CampaignCreateState.waiting_for_description` | 8 |
| 8 | AI кампания — название | Сообщение (description) | `src/bot/handlers/campaign_create_ai.py:process_description` | 155 | `CampaignCreateState.waiting_for_campaign_name` | 9 |
| 9 | AI кампания — генерация | Сообщение (name) | `src/bot/handlers/campaign_create_ai.py:process_campaign_name` | 195 | `CampaignCreateState.selecting_variant` | 10 |
| 10 | AI кампания — выбор варианта | `ai_variant:{index}` | `src/bot/handlers/campaign_create_ai.py:select_variant` | 250 | `CampaignCreateState.editing_text` | 11 |
| 11 | AI кампания — редактор текста | `ai_edit:add_url` | `src/bot/handlers/campaign_create_ai.py:process_edited_text` | 290 | `CampaignCreateState.waiting_for_url` | 12 |
| 12 | AI кампания — добавление URL | Сообщение (URL) | `src/bot/handlers/campaign_create_ai.py:process_url` | 330 | `CampaignCreateState.waiting_for_image` | 13 |
| 13 | AI кампания — изображение | `ai_edit:add_image` или фото | `src/bot/handlers/campaign_create_ai.py:process_image` | 370 | `CampaignCreateState.selecting_audience` | 14 |
| 14 | AI кампания — аудитория | `campaign_create:audience_{aud}` | `src/bot/handlers/campaign_create_ai.py:select_audience` | 420 | `CampaignCreateState.setting_budget` | 15 |
| 15 | AI кампания — бюджет | Сообщение (число) | `src/bot/handlers/campaign_create_ai.py:process_budget` | 460 | `CampaignCreateState.setting_schedule` | 16 |
| 16 | AI кампания — расписание | `campaign_create:schedule_*` | `src/bot/handlers/campaign_create_ai.py:schedule_*` | 510 | `CampaignCreateState.confirming` | — |
| **MANUAL СОЗДАНИЕ КАМПАНИИ (12 flows)** |
| 17 | Manual кампания — тематика | `main:create_campaign` | `src/bot/handlers/campaigns.py:start_campaign_wizard` | 56 | `CampaignStates.waiting_topic` | 18 |
| 18 | Manual кампания — заголовок | `campaign:topic:{topic}` | `src/bot/handlers/campaigns.py:select_topic` | 78 | `CampaignStates.waiting_header` | 19 |
| 19 | Manual кампания — тип текста | Сообщение (header) | `src/bot/handlers/campaigns.py:handle_header_input` | 110 | `CampaignStates.waiting_text` | 20 или 21 |
| 20 | Manual кампания — AI текст | `campaign:ai_text` | `src/bot/handlers/campaigns.py:select_ai_text` | 180 | `CampaignStates.waiting_ai_description` | 21 |
| 21 | Manual кампания — ручной текст | `campaign:manual_text` или сообщение | `src/bot/handlers/campaigns.py:handle_text_input` | 240 | `CampaignStates.waiting_image` | 22 |
| 22 | Manual кампания — изображение | `campaign:image_upload` или фото | `src/bot/handlers/campaigns.py:handle_image_upload` | 310 | `CampaignStates.waiting_member_count` | 23 |
| 23 | Manual кампания — размер аудитории | `campaign:members:{value}` | `src/bot/handlers/campaigns.py:select_member_count` | 380 | `CampaignStates.waiting_schedule` | 24 |
| 24 | Manual кампания — расписание | `campaign:schedule_now` или later | `src/bot/handlers/campaigns.py:schedule_now` | 440 | `CampaignStates.waiting_confirm` | 25 |
| 25 | Manual кампания — подтверждение | `campaign:confirm_*` | `src/bot/handlers/campaigns.py:handle_schedule_datetime` | 490 | — | — |
| **УПРАВЛЕНИЕ КАНАЛАМИ (4 flows)** |
| 26 | Добавление канала — username | `/add_channel` | `src/bot/handlers/channel_owner.py:cmd_add_channel` | 61 | `AddChannelStates.waiting_username` | 27 |
| 27 | Добавление канала — верификация | Сообщение (username) | `src/bot/handlers/channel_owner.py:process_channel_username` | 85 | `AddChannelStates.waiting_bot_admin_confirmation` | 28 |
| 28 | Добавление канала — цена | `channel_add:check_admin` | `src/bot/handlers/channel_owner.py:process_bot_admin_check` | 150 | `AddChannelStates.waiting_price` | 29 |
| 29 | Добавление канала — тематики | Сообщение (цена) | `src/bot/handlers/channel_owner.py:process_price` | 200 | `AddChannelStates.waiting_topics` | 30 |
| 30 | Добавление канала — настройки | `topics_done` | `src/bot/handlers/channel_owner.py:process_topics` | 260 | `AddChannelStates.waiting_settings` | 31 |
| 31 | Добавление канала — подтверждение | `channel_add:settings_done` | `src/bot/handlers/channel_owner.py:process_settings` | 310 | `AddChannelStates.waiting_confirm` | — |
| 32 | Мои каналы | `main:my_channels` | `src/bot/handlers/start.py:go_to_my_channels` | 587 | — | — |
| 33 | Заявки на размещение | `main:my_requests` | `src/bot/handlers/start.py:go_to_my_requests` | 596 | — | — |
| **B2B ПОТОКИ (4 flows)** |
| B2B-1 | Главное меню B2B | `/b2b` | `src/bot/handlers/b2b.py:cmd_b2b` | 18 | — | B2B-2 |
| B2B-2 | Просмотр пакетов ниши | `b2b_niche:{niche}` | `src/bot/handlers/b2b.py:show_niche_packages` | 45 | — | B2B-3 |
| B2B-3 | Детали пакета | `b2b_package:{id}` | — | — | — | B2B-4 |
| B2B-4 | Покупка пакета | `b2b_buy:{id}` | — | — | — | — |
| **ГЕЙМИФИКАЦИЯ (3 flows)** |
| G-1 | Просмотр значков | `cabinet:badges` | `src/bot/handlers/cabinet.py:show_badges` | 220 | — | — |
| G-2 | Прогресс уровня | `main:cabinet` | `src/bot/handlers/cabinet.py:show_cabinet` | 150 | — | — |
| G-3 | Реферальная программа | `billing:referral` | `src/bot/handlers/cabinet.py:referral_callback` | 320 | — | — |
| **АДМИН ПОТОКИ (6 flows)** |
| A-1 | Вход в админку | `/admin` | `src/bot/handlers/admin.py:handle_admin_menu` | 66 | — | A-2, A-3, A-4, A-5, A-6 |
| A-2 | Управление пользователями | `admin:users` | `src/bot/handlers/admin/users.py:handle_users_list` | 38 | `AdminBalanceStates`, `AdminBanStates` | — |
| A-3 | Broadcast рассылка | `admin:broadcast` | `src/bot/handlers/admin.py:handle_broadcast_start` | 350 | `AdminBroadcastStates` | — |
| A-4 | Тест кампании (AI) | `admin:test_campaign` → `admin:ai_generate` | `src/bot/handlers/admin/ai.py:handle_ai_generate_start` | 28 | `AdminAIGenerateStates` | — |
| A-5 | Чёрный список каналов | `admin:blacklist` | `src/bot/handlers/admin.py:show_blacklist` | 520 | — | — |
| A-6 | Здоровье рассылок | `admin:mailing_health` | `src/bot/handlers/admin.py:show_mailing_health` | 600 | — | — |
| **АНАЛИТИКА (1 flow)** |
| AN-1 | Главное меню аналитики | `main:analytics` | `src/bot/handlers/analytics.py:show_analytics_menu` | 42 | — | AN-2, AN-3 |
| AN-2 | Аналитика рекламодателя | `main:advertiser_analytics` | `src/bot/handlers/analytics.py:show_advertiser_analytics` | 95 | — | — |
| AN-3 | Аналитика владельца | `owner_analytics:role` | `src/bot/handlers/analytics.py:show_owner_analytics` | 140 | — | — |
| AN-4 | AI-аналитика кампаний | `main:ai_campaign_analytics` | `src/bot/handlers/campaign_analytics.py:show_ai_campaign_analytics` | 32 | — | — |
| **БИЛЛИНГ (3 flows)** |
| BL-1 | Просмотр баланса | `main:balance` | `src/bot/handlers/billing.py:show_balance` | 51 | — | BL-2 |
| BL-2 | Пополнение баланса | `billing:topup` | `src/bot/handlers/billing.py:show_topup_methods` | 120 | — | BL-3 |
| BL-3 | Выбор пакета кредитов | `billing:package_{pkg}` | `src/bot/handlers/billing.py:select_package` | 180 | — | — |
| **КАБИНЕТ (2 flows)** |
| C-1 | Личный кабинет | `main:cabinet` | `src/bot/handlers/cabinet.py:show_cabinet` | 100 | — | C-2 |
| C-2 | Смена тарифа | `billing:plans` | `src/bot/handlers/cabinet.py:show_plans` | 250 | — | — |

---

### 13.2 Последовательность вызова flow (Flow Sequence)

Данная диаграмма показывает направленный граф вызовов между flow, демонстрируя порядок переходов от одного flow к другому.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           ПОСЛЕДОВАТЕЛЬНОСТЬ ВЫЗОВА FLOW                         │
└─────────────────────────────────────────────────────────────────────────────────┘

                                    /start
                                       │
                    ┌──────────────────┼──────────────────┐
                    │                  │                  │
              [Новый пользователь]  [Рекламодатель]   [Владелец]
                    │                  │                  │
                    ▼                  ▼                  ▼
            ┌───────────────┐  ┌───────────────┐  ┌───────────────┐
            │   Flow 1      │  │   Flow 2      │  │   Flow 3      │
            │   Онбординг   │  │   Меню adv.   │  │   Меню own.   │
            └───────┬───────┘  └───────┬───────┘  └───────┬───────┘
                    │                  │                  │
                    │                  │                  ├──► Flow 26 (add_channel)
                    │                  │                  ├──► Flow 32 (my_channels)
                    │                  │                  └──► Flow 33 (my_requests)
                    │                  │
                    │                  ├──► Flow 5-16 (AI кампания)
                    │                  ├──► Flow 17-25 (Manual кампания)
                    │                  ├──► Flow BL-1 (balance)
                    │                  ├──► Flow C-1 (cabinet)
                    │                  └──► Flow AN-2 (analytics)
                    │
                    ▼
            ┌───────────────┐
            │   Flow 2/3/4  │
            │   Выбор роли  │
            └───────┬───────┘
                    │
         ┌──────────┴──────────┐
         │                     │
         ▼                     ▼
  [Рекламодатель]        [Владелец]
         │                     │
         ▼                     ▼
┌─────────────────┐   ┌─────────────────┐
│ AI CAMPAIGN     │   │ CHANNEL FLOW    │
│ FLOW 5-16       │   │ FLOW 26-31      │
│                 │   │                 │
│ 5: style        │   │ 26: username    │
│ 6: category     │   │ 27: verify      │
│ 7: description  │   │ 28: price       │
│ 8: campaign_name│   │ 29: topics      │
│ 9: generate     │   │ 30: settings    │
│ 10: select      │   │ 31: confirm     │
│ 11-12: edit     │   └────────┬────────┘
│ 13: image       │            │
│ 14: audience    │            ▼
│ 15: budget      │   ┌─────────────────┐
│ 16: schedule    │   │ MANUAL CAMPAIGN │
└────────┬────────┘   │ FLOW 17-25      │
         │            └────────┬────────┘
         │                     │
         └──────────┬──────────┘
                    │
                    ▼
         ┌─────────────────┐
         │   BILLING       │
         │   FLOW BL-1-3   │
         │                 │
         │ BL-1: balance   │
         │ BL-2: topup     │
         │ BL-3: package   │
         └────────┬────────┘
                  │
                  ▼
         ┌─────────────────┐
         │   CABINET       │
         │   FLOW C-1-2    │
         │                 │
         │ C-1: cabinet    │
         │ C-2: tariff     │
         │ G-1: badges     │
         │ G-2: level      │
         │ G-3: referral   │
         └────────┬────────┘
                  │
                  ▼
         ┌─────────────────┐
         │   ANALYTICS     │
         │   FLOW AN-1-4   │
         │                 │
         │ AN-1: menu      │
         │ AN-2: advertiser│
         │ AN-3: owner     │
         │ AN-4: AI        │
         └────────┬────────┘
                  │
                  ▼
         ┌─────────────────┐
         │   ADMIN         │
         │   FLOW A-1-6    │
         │                 │
         │ A-1: admin_menu │
         │ A-2: users      │
         │ A-3: broadcast  │
         │ A-4: AI test    │
         │ A-5: blacklist  │
         │ A-6: mailing    │
         └─────────────────┘


┌─────────────────────────────────────────────────────────────────────────────────┐
│                           B2B ПОСЛЕДОВАТЕЛЬНОСТЬ                                 │
└─────────────────────────────────────────────────────────────────────────────────┘

         /b2b
           │
           ▼
    ┌──────────────┐
    │  B2B Flow 1  │
    │  Главное меню│
    └──────┬───────┘
           │
           ▼
    ┌──────────────┐
    │  B2B Flow 2  │
    │  Выбор ниши  │
    └──────┬───────┘
           │
           ▼
    ┌──────────────┐
    │  B2B Flow 3  │
    │  Детали пакета│
    │  (❌ Not impl)│
    └──────┬───────┘
           │
           ▼
    ┌──────────────┐
    │  B2B Flow 4  │
    │  Покупка     │
    │  (❌ Not impl)│
    └──────────────┘
```

---

### 13.3 Матрица переходов между состояниями FSM

Для каждой группы FSM состояний показаны: точка входа, все возможные переходы и точка выхода.

#### CampaignCreateState (AI создание кампании)

```
CampaignCreateState:
  Entry: campaign_create:start (src/bot/handlers/campaign_create_ai.py:40)
  
  selecting_style
    → campaign_create:style_{style} → selecting_category
  
  selecting_category
    → campaign_create:category_{cat} → waiting_for_description
    → campaign_create:custom_category → entering_custom_category
  
  entering_custom_category
    → (текстовое сообщение) → selecting_category
  
  waiting_for_description
    → (текстовое сообщение, мин. 20 симв.) → waiting_for_campaign_name
  
  waiting_for_campaign_name
    → (текстовое сообщение, 3-100 симв.) → [AI генерация] → selecting_variant
  
  selecting_variant
    → ai_variant:{index} → editing_text
  
  editing_text
    → ai_edit:add_url → waiting_for_url
    → ai_edit:add_image → waiting_for_image
    → ai_edit:confirm → selecting_audience
  
  waiting_for_url
    → (текстовое сообщение, URL) → waiting_for_image
    → ai_edit:skip_url → waiting_for_image
  
  waiting_for_image
    → (фото) → selecting_audience
    → campaign_create:skip_image → selecting_audience
  
  selecting_audience
    → campaign_create:audience_{audience} → setting_budget
  
  setting_budget
    → (текстовое сообщение, число ≥100) → setting_schedule
  
  setting_schedule
    → campaign_create:schedule_now → confirming
    → campaign_create:schedule_1h → confirming
    → campaign_create:schedule_evening → confirming
    → campaign_create:schedule_tomorrow → confirming
    → campaign_create:schedule_custom → entering_schedule_date
  
  entering_schedule_date
    → (текстовое сообщение, ГГГГ-ММ-ДД ЧЧ:ММ) → confirming
  
  confirming
    → campaign_create:confirm_launch → [СОЗДАНИЕ КАМПАНИИ В БД]
  
  Exit: campaign launched OR campaign_create:cancel
```

#### CampaignStates (Manual создание кампании)

```
CampaignStates:
  Entry: main:create_campaign (src/bot/handlers/campaigns.py:56)
  
  waiting_topic
    → campaign:topic:{topic} → waiting_header
    → campaign:back → main_menu
  
  waiting_header
    → (текстовое сообщение, 5-255 симв.) → waiting_text
    → campaign:back → waiting_topic
  
  waiting_text
    → campaign:manual_text → waiting_image (ручной ввод)
    → campaign:ai_text → waiting_ai_description (AI генерация)
    → campaign:back → waiting_header
  
  waiting_ai_description
    → (текстовое сообщение, мин. 10 симв.) → [AI генерация 3 вариантов] → waiting_image
    → campaign:back → waiting_text
  
  waiting_image
    → (фото) → waiting_member_count
    → campaign:image_skip → waiting_member_count
    → campaign:back → waiting_text
  
  waiting_member_count
    → campaign:members:{value} → waiting_schedule
    → campaign:back → waiting_image
  
  waiting_schedule
    → campaign:schedule_now → waiting_confirm
    → campaign:schedule_later → waiting_confirm (с датой)
    → campaign:back → waiting_member_count
  
  waiting_confirm
    → campaign:confirm_launch → [СОЗДАНИЕ КАМПАНИИ]
    → campaign:confirm_edit → [РЕДАКТИРОВАНИЕ]
    → campaign:confirm_draft → [СОХРАНЕНИЕ ЧЕРНОВИКА]
    → campaign:back → waiting_schedule
  
  Exit: campaign created/draft OR campaign:cancel
```

#### AddChannelStates (Добавление канала)

```
AddChannelStates:
  Entry: /add_channel (src/bot/handlers/channel_owner.py:61)
  
  waiting_username
    → (текстовое сообщение, @username) → waiting_bot_admin_confirmation
  
  waiting_bot_admin_confirmation
    → channel_add:check_admin → [верификация бота админом] → waiting_price
  
  waiting_price
    → (текстовое сообщение, число ≥50) → waiting_topics
  
  waiting_topics
    → topic_toggle_{code} → waiting_topics (toggle)
    → topics_done → waiting_settings
  
  waiting_settings
    → channel_add:settings_done → waiting_confirm
  
  waiting_confirm
    → channel_add:confirm → [СОХРАНЕНИЕ КАНАЛА В БД]
  
  Exit: channel added OR /cancel
```

#### AdminAIGenerateStates (Админ AI генерация)

```
AdminAIGenerateStates:
  Entry: admin:ai_generate (src/bot/handlers/admin/ai.py:28)
  
  waiting_description
    → (текстовое сообщение, 10-500 симв.) → [AI генерация] → waiting_variants
  
  waiting_variants
    → admin:ai_variant_select:{n} → waiting_topic
    → admin:ai_regenerate → waiting_variants (перегенерация)
  
  waiting_topic
    → campaign:topic:{topic} → waiting_member_count
  
  waiting_member_count
    → campaign:members:{value} → waiting_schedule
  
  waiting_schedule
    → campaign:schedule_now → waiting_confirm
    → campaign:schedule_later → waiting_confirm
  
  waiting_confirm
    → campaign:confirm_launch → [БЕСПЛАТНЫЙ ЗАПУСК КАМПАНИИ]
  
  Exit: campaign launched OR /cancel
```

#### AdminBroadcastStates (Админ рассылка)

```
AdminBroadcastStates:
  Entry: admin:broadcast (src/bot/handlers/admin.py:350)
  
  waiting_message
    → (текстовое сообщение) → waiting_confirm
  
  waiting_confirm
    → admin:broadcast_confirm → [ОТПРАВКА ВСЕМ ПОЛЬЗОВАТЕЛЯМ]
    → admin:broadcast_cancel → waiting_message
  
  Exit: broadcast sent OR cancelled
```

#### OnboardingStates (Онбординг)

```
OnboardingStates:
  Entry: /start (новый пользователь) (src/bot/handlers/start.py:175)
  
  role_selected
    → onboard:role_advertiser → [сохранение роли] → main_menu (advertiser)
    → onboard:role_owner → [сохранение роли] → main_menu (owner)
  
  Exit: role saved, state cleared on next /start
```

---

### 13.4 Точки входа для каждой роли

В данной таблице показаны доступные команды, callback и первый экран для каждой роли пользователя.

| Роль | Доступные команды | Доступные callback | Первый экран |
|------|------------------|-------------------|--------------|
| **new** | `/start` | `onboard:role_advertiser`, `onboard:role_owner` | Онбординг с выбором роли |
| **advertiser** | `/start`, `/cabinet`, `/balance`, `/campaigns`, `/help`, `/models`, `/addchat`, `/b2b`, `/stats` | `main:create_campaign`, `main:create_campaign_ai`, `main:my_campaigns`, `main:analytics`, `main:cabinet`, `main:balance`, `main:feedback`, `main:help`, `main:channels_db`, `main:templates`, `main:change_role` | Меню рекламодателя с кнопками: Создать кампанию, Мои кампании, Каталог каналов, B2B, Статистика, Кабинет, Помощь |
| **owner** | `/start`, `/cabinet`, `/add_channel`, `/my_channels`, `/help`, `/stats` | `main:add_channel`, `main:my_channels`, `main:my_requests`, `main:payouts`, `main:analytics`, `main:cabinet`, `main:feedback`, `main:help`, `main:change_role` | Меню владельца с кнопками: Добавить канал, Мои каналы, Заявки, Выплаты, Статистика, Кабинет, Помощь |
| **both** | Все команды advertiser + owner | Все callback advertiser + owner | Комбинированное меню с разделами для обеих ролей |
| **admin** | `/start`, `/admin`, `/cancel`, `/cabinet`, `/balance` | `main:admin_panel`, `admin:users`, `admin:broadcast`, `admin:test_campaign`, `admin:blacklist`, `admin:mailing_health`, `admin:llm_classify`, `admin:celery_tasks`, `admin:monitoring` | Админ панель с разделами: Статистика, Пользователи, Рассылки, ЧС, Broadcast, Тест кампании, Мониторинг, Задачи Celery, LLM-классификация |

#### Детализация точек входа:

**Роль: new**
- **Точка входа:** `/start` (первый запуск)
- **Handler:** `src/bot/handlers/start.py:_handle_start` (строка 175)
- **Переход:** После выбора роли → Flow 2 (advertiser) или Flow 3 (owner)

**Роль: advertiser**
- **Точка входа:** `/start` (возвращающийся пользователь)
- **Handler:** `src/bot/handlers/start.py:_handle_start` (строка 175)
- **Ключевые callback:**
  - `main:create_campaign_ai` → Flow 5 (AI кампания)
  - `main:create_campaign` → Flow 17 (Manual кампания)
  - `main:balance` → Flow BL-1 (Баланс)
  - `main:cabinet` → Flow C-1 (Кабинет)
  - `main:analytics` → Flow AN-1 (Аналитика)
  - `main:my_campaigns` → Campaign analytics

**Роль: owner**
- **Точка входа:** `/start` (возвращающийся пользователь)
- **Handler:** `src/bot/handlers/start.py:_handle_start` (строка 175)
- **Ключевые callback:**
  - `main:add_channel` → Flow 26 (Добавить канал)
  - `main:my_channels` → Flow 32 (Мои каналы)
  - `main:my_requests` → Flow 33 (Заявки)
  - `main:payouts` → Выплаты
  - `main:analytics` → Flow AN-3 (Аналитика владельца)

**Роль: admin**
- **Точка входа:** `/admin`
- **Handler:** `src/bot/handlers/admin.py:handle_admin_menu` (строка 66)
- **Фильтр:** `AdminFilter()` (проверка на ADMIN_IDS)
- **Ключевые callback:**
  - `admin:users` → Управление пользователями
  - `admin:broadcast` → Рассылка
  - `admin:test_campaign` → Тест кампании
  - `admin:blacklist` → Чёрный список
  - `admin:mailing_health` → Здоровье рассылок

---

### 13.5 Критические пути (Critical Paths)

Документированы критические пользовательские пути с указанием файлов и номеров строк.

#### 1. Путь рекламодателя (полный цикл)

Пользователь создаёт кампанию, пополняет баланс, запускает и отслеживает аналитику.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ КРИТИЧЕСКИЙ ПУТЬ РЕКЛАМОДАТЕЛЯ (ПОЛНЫЙ ЦИКЛ)                                     │
└─────────────────────────────────────────────────────────────────────────────────┘

/start (Flow 2)
   │
   ├─ src/bot/handlers/start.py:_handle_start (строка 175)
   │
   ▼
main:create_campaign_ai
   │
   ├─ src/bot/handlers/start.py:start_ai_campaign (строка 131)
   │
   ▼
Flow 5-16 (AI Campaign Wizard)
   │
   ├─ src/bot/handlers/campaign_create_ai.py:start_campaign_create (строка 40)
   ├─ src/bot/handlers/campaign_create_ai.py:style_selected (строка 72)
   ├─ src/bot/handlers/campaign_create_ai.py:category_selected (строка 120)
   ├─ src/bot/handlers/campaign_create_ai.py:process_description (строка 155)
   ├─ src/bot/handlers/campaign_create_ai.py:process_campaign_name (строка 195)
   ├─ src/bot/handlers/campaign_create_ai.py:select_variant (строка 250)
   ├─ src/bot/handlers/campaign_create_ai.py:process_edited_text (строка 290)
   ├─ src/bot/handlers/campaign_create_ai.py:process_url (строка 330)
   ├─ src/bot/handlers/campaign_create_ai.py:process_image (строка 370)
   ├─ src/bot/handlers/campaign_create_ai.py:select_audience (строка 420)
   ├─ src/bot/handlers/campaign_create_ai.py:process_budget (строка 460)
   └─ src/bot/handlers/campaign_create_ai.py:schedule_* (строка 510)
   │
   ▼
main:balance (Flow BL-1)
   │
   ├─ src/bot/handlers/billing.py:show_balance (строка 51)
   │
   ▼
Flow BL-2-3 (Пополнение баланса)
   │
   ├─ src/bot/handlers/billing.py:show_topup_methods (строка 120)
   ├─ src/bot/handlers/billing.py:select_package (строка 180)
   │
   ▼
main:my_campaigns
   │
   ├─ src/bot/handlers/cabinet.py (строка 406)
   │
   ▼
Flow AN-1-2 (Аналитика кампаний)
   │
   ├─ src/bot/handlers/analytics.py:show_analytics_menu (строка 42)
   ├─ src/bot/handlers/analytics.py:show_advertiser_analytics (строка 95)
   │
   ▼
[КАМПАНИЯ ЗАПУЩЕНА]
```

**Файлы, задействованные в пути:**
- `src/bot/handlers/start.py` (строки 131-175)
- `src/bot/handlers/campaign_create_ai.py` (строки 40-550)
- `src/bot/handlers/billing.py` (строки 51-200)
- `src/bot/handlers/cabinet.py` (строки 406-450)
- `src/bot/handlers/analytics.py` (строки 42-150)
- `src/bot/states/campaign_create.py` (все состояния)
- `src/bot/keyboards/campaign_ai.py` (клавиатуры AI wizard)
- `src/tasks/mailing_tasks.py` (отправка кампании)

---

#### 2. Путь владельца (полный цикл)

Пользователь добавляет канал, получает заявки, одобряет и получает выплаты.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ КРИТИЧЕСКИЙ ПУТЬ ВЛАДЕЛЬЦА (ПОЛНЫЙ ЦИКЛ)                                         │
└─────────────────────────────────────────────────────────────────────────────────┘

/start (Flow 3)
   │
   ├─ src/bot/handlers/start.py:_handle_start (строка 175)
   │
   ▼
main:add_channel
   │
   ├─ src/bot/handlers/start.py (строка 636)
   │
   ▼
Flow 26-31 (Добавление канала)
   │
   ├─ src/bot/handlers/channel_owner.py:cmd_add_channel (строка 61)
   ├─ src/bot/handlers/channel_owner.py:process_channel_username (строка 85)
   ├─ src/bot/handlers/channel_owner.py:process_bot_admin_check (строка 150)
   ├─ src/bot/handlers/channel_owner.py:process_price (строка 200)
   ├─ src/bot/handlers/channel_owner.py:process_topics (строка 260)
   ├─ src/bot/handlers/channel_owner.py:process_settings (строка 310)
   └─ src/bot/handlers/channel_owner.py:process_confirm (строка 360)
   │
   ▼
main:my_requests
   │
   ├─ src/bot/handlers/start.py:go_to_my_requests (строка 596)
   │
   ▼
[Просмотр заявок]
   │
   ├─ src/bot/handlers/channel_owner.py (заявки)
   │
   ▼
[Одобрение/Отклонение]
   │
   ├─ src/bot/handlers/channel_owner.py (approve/reject)
   │
   ▼
main:payouts
   │
   ├─ src/bot/handlers/start.py (строка 645)
   │
   ▼
Flow 27 (Выплаты)
   │
   ├─ src/bot/handlers/channel_owner.py (payout request)
   │
   ▼
[ВЫПЛАТА СОЗДАНА]
```

**Файлы, задействованные в пути:**
- `src/bot/handlers/start.py` (строки 596, 636, 645)
- `src/bot/handlers/channel_owner.py` (строки 61-400)
- `src/bot/states/channel_owner.py` (AddChannelStates)
- `src/bot/keyboards/channels.py` (клавиатуры каналов)
- `src/db/repositories/channel_repo.py` (репозиторий каналов)

---

#### 3. Путь админа (мониторинг)

Администратор проверяет статистику, управляет пользователями и запускает рассылки.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ КРИТИЧЕСКИЙ ПУТЬ АДМИНА (МОНИТОРИНГ)                                             │
└─────────────────────────────────────────────────────────────────────────────────┘

/admin (Flow A-1)
   │
   ├─ src/bot/handlers/admin.py:handle_admin_menu (строка 66)
   │
   ▼
admin:stats
   │
   ├─ src/bot/handlers/admin.py (статистика)
   │
   ▼
admin:mailing_health (Flow A-6)
   │
   ├─ src/bot/handlers/admin.py:show_mailing_health (строка 600)
   │
   ▼
[Просмотр статуса рассылок]
   │
   ├─ Активные кампании
   ├─ Паузы и баны
   └─ Каналы в ЧС
   │
   ▼
admin:users (Flow A-2)
   │
   ├─ src/bot/handlers/admin/users.py:handle_users_list (строка 38)
   │
   ▼
[Список пользователей]
   │
   ├─ src/bot/handlers/admin/users.py:show_users_page (строка 48)
   │
   ▼
admin:user_detail
   │
   ├─ src/bot/handlers/admin/users.py:handle_user_detail (строка 85)
   │
   ▼
[Детали пользователя]
   │
   ├─ Просмотр баланса
   ├─ История транзакций
   └─ Статус бана
   │
   ▼
admin:ban_user (опционально)
   │
   ├─ src/bot/handlers/admin/users.py (бан)
   │
   ▼
admin:broadcast (Flow A-3)
   │
   ├─ src/bot/handlers/admin.py:handle_broadcast_start (строка 350)
   │
   ▼
[Рассылка всем пользователям]
   │
   ├─ AdminBroadcastStates.waiting_message
   └─ AdminBroadcastStates.waiting_confirm
   │
   ▼
[РАССЫЛКА ОТПРАВЛЕНА]
```

**Файлы, задействованные в пути:**
- `src/bot/handlers/admin.py` (строки 66-700)
- `src/bot/handlers/admin/users.py` (строки 38-200)
- `src/bot/handlers/admin/ai.py` (AI генерация)
- `src/bot/states/admin.py` (AdminBalanceStates, AdminBanStates, AdminBroadcastStates)
- `src/bot/keyboards/admin.py` (админ клавиатуры)
- `src/bot/filters/admin.py` (AdminFilter)

---

### 13.6 Анализ связанных файлов (File Dependencies)

Для каждого крупного функционального блока перечислены все связанные файлы проекта.

#### Создание кампании (AI)

| Файл | Строк | Описание |
|------|-------|----------|
| `src/bot/handlers/campaign_create_ai.py` | 911 | Основной handler AI wizard'а |
| `src/bot/states/campaign_create.py` | 49 | FSM состояния для AI кампании |
| `src/bot/keyboards/campaign_ai.py` | 280 | Клавиатуры AI wizard'а |
| `src/core/services/ai_service.py` | ~400 | Генерация текста через AI (Groq/OpenAI) |
| `src/tasks/mailing_tasks.py` | ~200 | Celery задачи отправки кампании |
| `src/db/repositories/campaign_repo.py` | ~300 | Репозиторий кампаний |
| `src/db/models/campaign.py` | ~150 | Модель кампании |
| `src/bot/utils/safe_callback.py` | ~50 | Утилиты безопасного редактирования callback |

**Зависимости:**
- AI провайдеры: Groq, OpenAI, OpenRouter
- Redis: кэширование состояний FSM
- Celery: асинхронная отправка кампаний

---

#### Создание кампании (Manual)

| Файл | Строк | Описание |
|------|-------|----------|
| `src/bot/handlers/campaigns.py` | 1106 | Основной handler manual wizard'а |
| `src/bot/states/campaign.py` | 35 | FSM состояния для manual кампании |
| `src/bot/keyboards/campaign.py` | ~200 | Клавиатуры manual wizard'а |
| `src/utils/content_filter/filter.py` | ~150 | Фильтр контента |
| `src/core/services/ai_service.py` | ~400 | AI генерация (опционально) |

**Зависимости:**
- Content filter: проверка текста на запрещённые категории
- AI service: генерация текста по описанию

---

#### Управление каналами

| Файл | Строк | Описание |
|------|-------|----------|
| `src/bot/handlers/channel_owner.py` | 1150 | Handler добавления/управления каналами |
| `src/bot/states/channel_owner.py` | 30 | FSM состояния для каналов |
| `src/bot/keyboards/channels.py` | ~250 | Клавиатуры каналов |
| `src/db/repositories/channel_repo.py` | ~200 | Репозиторий каналов |
| `src/db/models/channel.py` | ~100 | Модель канала |

**Зависимости:**
- Telegram Bot API: проверка членства бота в канале
- SQLAlchemy: работа с БД каналов

---

#### Биллинг

| Файл | Строк | Описание |
|------|-------|----------|
| `src/bot/handlers/billing.py` | 605 | Handler платежей и баланса |
| `src/bot/keyboards/billing.py` | 150 | Клавиатуры биллинга |
| `src/core/services/cryptobot_service.py` | ~250 | CryptoBot API интеграция |
| `src/db/models/crypto_payment.py` | ~100 | Модель крипто-платежей |
| `src/db/repositories/payment_repo.py` | ~150 | Репозиторий платежей |
| `src/core/services/billing_service.py` | ~200 | Бизнес-логика биллинга |

**Зависимости:**
- CryptoBot API: создание инвойсов, проверка оплаты
- Telegram Stars: альтернативный метод оплаты

---

#### Личный кабинет и геймификация

| Файл | Строк | Описание |
|------|-------|----------|
| `src/bot/handlers/cabinet.py` | 552 | Handler личного кабинета |
| `src/bot/keyboards/cabinet.py` | ~100 | Клавиатуры кабинета |
| `src/core/services/xp_service.py` | ~150 | Расчёт XP и уровней |
| `src/core/services/badge_service.py` | ~200 | Система значков |
| `src/db/models/user.py` | ~200 | Модель пользователя |

**Зависимости:**
- XP система: начисление опыта за действия
- Badge система: получение достижений

---

#### Админ панель

| Файл | Строк | Описание |
|------|-------|----------|
| `src/bot/handlers/admin.py` | 1584 | Основной handler админки |
| `src/bot/handlers/admin/users.py` | 467 | Управление пользователями |
| `src/bot/handlers/admin/campaigns.py` | 188 | Тест кампаний |
| `src/bot/handlers/admin/ai.py` | 169 | AI генерация для админа |
| `src/bot/states/admin.py` | 60 | FSM состояния админки |
| `src/bot/keyboards/admin.py` | ~300 | Клавиатуры админки |
| `src/bot/filters/admin.py` | ~50 | AdminFilter для защиты |

**Зависимости:**
- AdminFilter: проверка на ADMIN_IDS
- Celery: мониторинг задач

---

#### Аналитика

| Файл | Строк | Описание |
|------|-------|----------|
| `src/bot/handlers/analytics.py` | 578 | Handler аналитики |
| `src/bot/handlers/campaign_analytics.py` | 267 | AI-аналитика кампаний |
| `src/bot/keyboards/campaign_analytics.py` | ~150 | Клавиатуры аналитики |
| `src/core/services/analytics_service.py` | ~300 | Сервис аналитики |
| `src/core/services/campaign_analytics_ai.py` | ~200 | AI-анализ кампаний |
| `src/db/repositories/chat_analytics.py` | ~250 | Репозиторий чат-аналитики |

**Зависимости:**
- AI service: генерация инсайтов
- PostgreSQL: агрегация статистики

---

#### B2B маркетплейс

| Файл | Строк | Описание |
|------|-------|----------|
| `src/bot/handlers/b2b.py` | 131 | Handler B2B маркетплейса |
| `src/core/services/b2b_package_service.py` | ~150 | Сервис B2B пакетов |
| `src/db/models/b2b_package.py` | ~100 | Модель B2B пакета |

**Зависимости:**
- База пакетов: predefined пакеты каналов

---

#### Обратная связь

| Файл | Строк | Описание |
|------|-------|----------|
| `src/bot/handlers/feedback.py` | ~150 | Handler обратной связи |
| `src/bot/states/feedback.py` | 25 | FSM состояния feedback |
| `src/bot/keyboards/feedback.py` | ~50 | Клавиатуры feedback |

---

#### Онбординг и главное меню

| Файл | Строк | Описание |
|------|-------|----------|
| `src/bot/handlers/start.py` | 807 | Обработчик /start и главных меню |
| `src/bot/states/onboarding.py` | 15 | FSM состояния онбординга |
| `src/bot/keyboards/main_menu.py` | ~350 | Главные меню (role-dependent) |
| `src/core/services/user_role_service.py` | ~150 | Сервис ролей пользователей |

---

#### Уведомления

| Файл | Строк | Описание |
|------|-------|----------|
| `src/bot/handlers/notifications.py` | ~200 | Handler уведомлений |
| `src/tasks/mailing_tasks.py` | ~200 | Celery задачи уведомлений |
| `src/db/models/notification.py` | ~50 | Модель уведомлений |

---

#### Вспомогательные файлы

| Файл | Строк | Описание |
|------|-------|----------|
| `src/bot/utils/safe_callback.py` | ~50 | Безопасное редактирование callback |
| `src/bot/utils/message_utils.py` | ~50 | Утилиты сообщений |
| `src/bot/keyboards/pagination.py` | ~80 | Универсальная пагинация |
| `src/db/session.py` | ~50 | SQLAlchemy session factory |
| `src/config/settings.py` | ~100 | Настройки проекта |

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
