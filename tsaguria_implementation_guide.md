# TSAGURIA — Разработчик интерфейсов
## Market Telegram Bot — Пошаговое руководство по реализации

---

| Параметр | Значение |
|---|---|
| **Роль** | Разработчик интерфейсов (Bot UX, FSM, Mini App frontend) |
| **Личная ветка** | `developer/tsaguria` |
| **Рабочие ветки** | `feature/*` создаются от `developer/tsaguria`, мержатся в `develop` |
| **Стек** | Python 3.13 · aiogram 3 · FSM · React · Vite · TypeScript · recharts |
| **Инструмент** | Qwen Code (промпты к каждому шагу) |
| **Всего шагов** | 17 шагов, 5 спринтов, 10 недель |

> **Ключевое правило:** не пиши бизнес-логику сам! Все сервисы (`user_repo`, `campaign_repo`, `billing_service`, `ai_service`, `analytics_service`) реализует belin. Твоя задача — вызывать готовые методы из handlers и форматировать результат для пользователя. Перед началом каждого шага — проверь чеклист Prerequisites.

### Правило ветвления для каждого шага

```bash
git checkout develop && git pull origin develop
git checkout developer/tsaguria && git merge develop
git checkout -b feature/название-шага
# ... работаешь, коммитишь ...
git push origin feature/название-шага
# Открываешь PR в develop → belin делает review → Squash Merge
```

### Конвенция коммитов

```
feat(bot): add /start handler with user registration
feat(keyboards): add campaign wizard keyboards with back button
feat(mini-app): add Dashboard page with glassmorphism cards
fix(fsm): fix back button state transition in campaign wizard
```

---

## 🛠️ SPRINT 0 — НАСТРОЙКА РАБОЧЕГО ОКРУЖЕНИЯ

---

### Шаг 1 — Клонирование репозитория и настройка окружения
> 🌿 **Ветка:** `developer/tsaguria`

> ⚠️ **ПЕРЕД НАЧАЛОМ:**
> - ✓ belin завершил Шаги 1-3: Docker Compose, Dockerfiles, CI/CD, `.env.example`
> - ✓ Репозиторий доступен на GitHub
> - ✓ Ветка `develop` существует

Твоя задача в Sprint 0 — настроить окружение и изучить архитектуру. Всю инфраструктуру создаёт belin — твоя инфраструктура поднимается его командами.

```bash
git clone https://github.com/your-org/market-telegram-bot.git
cd market-telegram-bot
git checkout developer/tsaguria
pyenv install 3.13.7 && pyenv local 3.13.7
pip install poetry && poetry install
cp .env.example .env
# Заполнить: BOT_TOKEN (получить у @BotFather), DATABASE_URL, REDIS_URL
pre-commit install
```

✅ **ЧЕКПОИНТ** — `poetry install` без ошибок, `pre-commit install` прошёл

---

### Шаг 2 — Запуск инфраструктуры от belin
> 🌿 **Ветка:** `developer/tsaguria`

> ⚠️ **ПЕРЕД НАЧАЛОМ:**
> - ✓ belin завершил Шаг 2: `docker-compose.yml` и Dockerfiles смержены в `develop`
> - ✓ Docker Desktop установлен на твоём компьютере

```bash
git checkout develop && git pull origin develop
git checkout developer/tsaguria && git merge develop
docker compose up -d postgres redis
docker compose ps  # оба должны быть healthy
```

1. Изучить `ARCHITECTURE.md` и `README.md` — понять структуру папок
2. Изучить `src/db/models/` — понять все модели (User, Campaign, Chat и др.)
3. Договориться с belin: какие методы репозиториев нужны тебе для handlers

✅ **ЧЕКПОИНТ** — postgres и redis healthy, структура проекта понятна

---

## 💬 SPRINT 1 — БОТ-ИНТЕРФЕЙС: МЕНЮ, КАБИНЕТ, FSM WIZARD

---

### Шаг 3 — /start, /help — первый контакт с пользователем
> 🌿 **Ветка:** `feature/bot-start`

> ⚠️ **ПЕРЕД НАЧАЛОМ:**
> - ✓ Sprint 0 завершён
> - ✓ belin завершил Шаг 6: `user_repo.get_by_telegram_id()` и `create_or_update()` готовы и смержены
> - ✓ `BOT_TOKEN` в `.env`

1. Создать `src/bot/main.py`:
   - `bot = Bot(token=settings.BOT_TOKEN, parse_mode=ParseMode.HTML)`
   - `dp = Dispatcher(storage=RedisStorage(redis_client))`
   - Зарегистрировать все роутеры и middleware
2. Создать `src/bot/middlewares/throttling.py`:
   - Проверять время последнего запроса из Redis
   - Если < 0.5 сек — ответить "⏳ Подождите немного..." и не передавать дальше
3. Создать `src/bot/handlers/start.py`:
   - `@router.message(CommandStart())`: вызвать `user_repo.create_or_update(telegram_id, username)`
   - Персональное приветствие: `f"👋 Привет, {user.full_name}!"`
   - Если новый пользователь — онбординг (3 шага)
   - Если вернувшийся — главное меню с балансом
   - `@router.message(Command("help"))`: форматированный список команд с эмодзи

> 🤖 **Промпт для Qwen Code:**
> ```
> Создай aiogram 3 обработчик /start для Telegram бота. При старте: вызвать
> user_repo.create_or_update(telegram_id, username, first_name). Если пользователь
> новый — показать "🚀 Добро пожаловать в Market Bot!". Если вернувшийся —
> "👋 С возвращением, {name}! Баланс: {balance}₽". Throttling middleware 0.5 сек через Redis.
> ```

✅ **ЧЕКПОИНТ** — /start регистрирует нового пользователя в БД и показывает приветствие

---

### Шаг 4 — Главное меню и все клавиатуры
> 🌿 **Ветка:** `feature/keyboards`

> ⚠️ **ПЕРЕД НАЧАЛОМ:**
> - ✓ Шаг 3 завершён (/start работает)

1. Создать `src/bot/keyboards/main_menu.py`:
   - `get_main_menu(balance: Decimal) → InlineKeyboardMarkup`
   - Ряд 1: `[🚀 Создать кампанию]` `[📊 Мои кампании]`
   - Ряд 2: `[👤 Кабинет  |  💳 {balance}₽]`
   - Ряд 3: `[🤖 ИИ-генерация]` `[📋 Шаблоны]`
   - Ряд 4: `[ℹ️ Помощь]`
   - Использовать `CallbackData` factory: `MainMenuCB(action: str)`
2. Создать `src/bot/keyboards/campaign.py`:
   - `get_campaign_step_kb(step, back=True)`: `[← Назад]` `[✖ Отмена]` на каждом шаге
   - `get_campaign_confirm_kb()`: `[✅ Запустить]` `[📝 Изменить]` `[💾 Черновик]` `[✖ Отмена]`
   - `get_topics_kb()`: 9 кнопок тематик (IT, Бизнес, Новости, …)
   - `get_member_count_kb()`: `[100-1К]` `[1К-10К]` `[10К-100К]` `[Любой]`
3. Создать `src/bot/keyboards/billing.py`:
   - `get_amount_kb()`: `[100₽]` `[500₽]` `[1000₽]` `[Другая сумма]`
   - `get_plans_kb()`: 4 кнопки тарифов с ценами
4. Создать `src/bot/keyboards/pagination.py`:
   - `get_pagination_kb(page, total_pages, cb_prefix)`: `[◀ Prev]` `[1/5]` `[Next ▶]`

> 🤖 **Промпт для Qwen Code:**
> ```
> Создай систему InlineKeyboard клавиатур для aiogram 3 с CallbackData factory.
> Главное меню: 2 столбца, кнопки с эмодзи (🚀 Создать кампанию, 📊 Мои кампании,
> 👤 Кабинет, 💳 Баланс {amount}₽, 🤖 ИИ-генерация, ℹ️ Помощь).
> Клавиатура выбора тематики: 3 столбца, 9 тематик.
> Пагинация с кнопкой текущей страницы. Все через CallbackData(prefix="...").
> ```

✅ **ЧЕКПОИНТ** — главное меню красиво, все callback_data уникальны, нет ошибок

---

### Шаг 5 — Личный кабинет пользователя
> 🌿 **Ветка:** `feature/cabinet`

> ⚠️ **ПЕРЕД НАЧАЛОМ:**
> - ✓ Шаг 4 завершён (клавиатуры готовы)
> - ✓ belin завершил Шаг 6: `user_repo.get_with_stats()` и `campaign_repo.get_by_user()` готовы

1. Создать `src/bot/handlers/cabinet.py`:
   - `handle_cabinet(callback)`: вызвать `user_repo.get_with_stats(user_id)`
   - Карточка кабинета (HTML форматирование):
     ```
     👤 Ваш кабинет
     💳 Баланс: {balance}₽  |  📦 Тариф: {plan}
     📊 Кампаний: {total}   |  🔄 Активных: {active}
     📅 Дата регистрации: {created_at}
     ```
   - Кнопки: `[📋 Мои кампании]` `[💳 Пополнить]` `[🔗 Реферальная ссылка]`
   - `handle_my_campaigns(callback, page=1)`: список с пагинацией (5 на страницу)
     - Статус-эмодзи: ✅ done / ⏳ queued / 🔄 running / ❌ error / 📝 draft
   - `handle_referral(callback)`:
     - Реф-код: `t.me/botname?start=ref_{code}`
     - Статистика: приглашено / заработано

> 🤖 **Промпт для Qwen Code:**
> ```
> Создай aiogram 3 обработчик личного кабинета. /cabinet: HTML-форматированная карточка
> с балансом, тарифом, числом кампаний. Список кампаний с пагинацией (5 штук, кнопки ◀/▶).
> Для каждой кампании — строка со статусом-эмодзи (✅ done, ⏳ queued, ❌ error).
> При клике на кампанию — inline детали.
> ```

✅ **ЧЕКПОИНТ** — кабинет открывается, список кампаний листается, реф-ссылка копируется

---

### Шаг 6 — FSM Wizard создания рекламной кампании
> 🌿 **Ветка:** `feature/campaign-wizard`

> ⚠️ **ПЕРЕД НАЧАЛОМ:**
> - ✓ Шаг 5 завершён (кабинет работает)
> - ✓ Шаг 4 завершён (клавиатуры с тематиками готовы)
> - ✓ belin завершил Шаг 9: `campaign_repo.create()` доступен
> - ✓ belin завершил Шаг 10: `mailing_tasks.send_campaign.delay()` доступен
> - ✓ belin завершил Шаг 8: `content_filter.check()` доступен

1. Создать `src/bot/states/campaign.py`:
   ```python
   class CampaignStates(StatesGroup):
       waiting_title = State()
       waiting_text = State()
       waiting_ai_description = State()
       waiting_topic = State()
       waiting_member_count = State()
       waiting_schedule = State()
       waiting_confirm = State()
   ```
2. Создать `src/bot/handlers/campaigns.py`:
   - **Шаг 1** — название: "📝 Введите название (3-100 символов)", валидация, сохранить в FSM
   - **Шаг 2** — текст или ИИ: `[✏️ Ввести текст]` `[🤖 Сгенерировать (+10₽)]`
   - **Шаг 2а** — ИИ: запрос описания → `ai_service.generate_ab_variants()` → 3 варианта
   - **Шаг 3** — тематика: `get_topics_kb()`, сохранить выбор
   - **Шаг 4** — аудитория: `get_member_count_kb()`, сохранить диапазон
   - **Шаг 5** — расписание: `[▶️ Сейчас]` или `[⏰ Запланировать]` → ввод ДД.ММ.ГГГГ ЧЧ:ММ
   - **Шаг 6** — подтверждение:
     - ПЕРЕД показом: `content_filter.check(text)` — если не прошёл → ошибка, вернуть на шаг 2
     - Карточка со всеми параметрами + кнопки `[✅ Запустить]` `[📝 Изменить]` `[💾 Черновик]` `[✖ Отмена]`
     - При "Запустить": `campaign_repo.create()` + `mailing_tasks.send_campaign.delay()`
   - **Кнопка "← Назад"** — на каждом шаге возвращает к предыдущему State
   - **Кнопка "✖ Отмена"** — `dp.fsm.clear()`, вернуть главное меню

> 🤖 **Промпт для Qwen Code:**
> ```
> Создай aiogram 3 FSM wizard для создания рекламной кампании.
> States: waiting_title → waiting_text (или waiting_ai_description) → waiting_topic →
> waiting_member_count → waiting_schedule → waiting_confirm.
> На каждом шаге кнопка "← Назад" возвращает к предыдущему State.
> На шаге подтверждения — красивая карточка со всеми параметрами и кнопками
> Запустить/Изменить/Черновик/Отмена.
> ```

✅ **ЧЕКПОИНТ** — wizard проходит все шаги, "Назад" работает везде, кампания создаётся в БД

---

## 💳 SPRINT 2 — БИЛЛИНГ И ПЛАТЕЖИ

---

### Шаг 7 — Биллинг — отображение баланса и выбор суммы
> 🌿 **Ветка:** `feature/billing-ui`

> ⚠️ **ПЕРЕД НАЧАЛОМ:**
> - ✓ Sprint 1 смержен в `develop`
> - ✓ belin реализовал `billing_service.py` с методами `create_payment()`, `get_history()`
> - ✓ `YOOKASSA_SHOP_ID` и `YOOKASSA_SECRET_KEY` в `.env`
> - ✓ `transaction_repo.get_by_user()` доступен

1. Создать `src/bot/handlers/billing.py`:
   - `handle_balance(callback)`: показать баланс + кнопку "Пополнить"
   - `handle_topup(callback)`: показать `get_amount_kb()`
   - `handle_amount_selected(callback, amount)`:
     - Если `amount == "custom"` → запросить ввод числа (мин 50₽, макс 100 000₽)
     - Вызвать `billing_service.create_payment(user_id, amount)` → `payment_url`
     - Отправить кнопку "💳 Перейти к оплате" со ссылкой
     - Сохранить `payment_id` в Redis TTL=30min
   - `handle_payment_check(callback, payment_id)`:
     - `billing_service.check_payment(payment_id)`
     - `succeeded` → "✅ Оплата прошла! Баланс: {new_balance}₽"
     - `pending` → "⏳ Ожидаем подтверждение..."
   - `handle_history(callback, page=1)`:
     - Список транзакций: дата, тип (+/-), сумма, описание
     - Эмодзи: 💚 topup / 🔴 spend / 🎁 bonus

> 🤖 **Промпт для Qwen Code:**
> ```
> Создай aiogram 3 обработчик биллинга. handle_topup: InlineKeyboard с суммами
> [100₽] [500₽] [1000₽] [Другая]. При выборе — billing_service.create_payment()
> и кнопка-ссылка на YooKassa. handle_history: список транзакций с пагинацией,
> эмодзи (💚 пополнение / 🔴 списание).
> ```

✅ **ЧЕКПОИНТ** — кнопка "Оплатить" открывает YooKassa, история транзакций листается

---

### Шаг 8 — Реферальная система и выбор тарифа
> 🌿 **Ветка:** `feature/referral-plans`

> ⚠️ **ПЕРЕД НАЧАЛОМ:**
> - ✓ Шаг 7 завершён
> - ✓ `user_repo.get_referral_stats()` доступен (договориться с belin)
> - ✓ `billing_service.apply_referral_bonus()` доступен

1. Создать `src/bot/handlers/referral.py`:
   - Реф-экран: код, ссылка `t.me/{botname}?start=ref_{code}`, статистика
   - Кнопка `[📤 Поделиться ссылкой]` → share URL
   - В `/start` handler: проверить аргумент `ref_*` → `billing_service.apply_referral_bonus()`
   - Уведомить пригласившего: "🎁 +20₽ — {name} зарегистрировался по вашей ссылке"
2. Создать `src/bot/handlers/plans.py`:
   - 4 карточки тарифов с ценами и описанием
   - FREE / STARTER (299₽/мес) / PRO (999₽/мес) / BUSINESS (2999₽/мес)
   - Кнопка "Подключить" → `billing_service.change_plan()`

✅ **ЧЕКПОИНТ** — реф-ссылка работает, бонус начисляется, тарифы отображаются

---

## 🔔 SPRINT 3 — УВЕДОМЛЕНИЯ И ШАБЛОНЫ

---

### Шаг 9 — Система уведомлений пользователю
> 🌿 **Ветка:** `feature/notifications-ui`

> ⚠️ **ПЕРЕД НАЧАЛОМ:**
> - ✓ Sprint 2 смержен в `develop`
> - ✓ belin завершил Шаг 11: `notification_service.py` готов

1. Создать `src/bot/handlers/notifications.py`:
   - `format_campaign_started(campaign) → str`:
     ```
     🚀 Кампания запущена!
     📋 {title}
     👥 Целевых чатов: {chat_count}
     ⏱ Ожидаемое время: ~{estimate} мин
     ```
   - `format_campaign_done(stats) → str`:
     ```
     ✅ Рассылка завершена!
     📤 Отправлено: {sent} из {total}
     📊 Успешность: {rate}%
     ```
     Кнопка `[📊 Скачать отчёт PDF]`
   - `format_campaign_error(error_msg) → str`:
     ```
     ❌ Ошибка рассылки
     Причина: {error_msg}
     ```
     Кнопки: `[🔄 Повторить]` `[📞 Поддержка]`
   - `handle_low_balance_alert(user_id, balance)`:
     - "⚠️ Баланс заканчивается ({balance}₽)" + кнопка `[💳 Пополнить]`
   - `handle_report_request(callback, campaign_id)`:
     - `analytics_service.generate_campaign_report()` → bytes
     - `bot.send_document(user_id, BufferedInputFile(pdf_bytes, "report.pdf"))`

> 🤖 **Промпт для Qwen Code:**
> ```
> Создай aiogram 3 обработчики для уведомлений о кампаниях. HTML-сообщения:
> кампания запущена (с числом чатов), кампания завершена (sent/failed/rate%),
> ошибка рассылки (кнопка "Повторить"). handle_report_request: получить PDF bytes
> от analytics_service и отправить как document через bot.send_document с BufferedInputFile.
> ```

✅ **ЧЕКПОИНТ** — после тестовой рассылки приходит уведомление с кнопкой PDF

---

### Шаг 10 — Библиотека шаблонов рекламных сообщений
> 🌿 **Ветка:** `feature/ad-templates`

> ⚠️ **ПЕРЕД НАЧАЛОМ:**
> - ✓ FSM wizard (Шаг 6) принимает pre-filled текст

1. Создать `src/bot/data/templates.py`:
   - `TEMPLATES = {"category": [{"title": ..., "text": ..., "preview": ...}]}`
   - 7 категорий: Услуги / IT / Курсы / Товары / Недвижимость / Крипта / Другое
   - Минимум 3 шаблона на категорию (21+ шаблон)
   - Текст с плейсхолдерами: `{название}`, `{цена}`, `{ссылка}`
2. Создать `src/bot/handlers/templates.py`:
   - `handle_templates_menu(callback)`: категории через InlineKeyboard
   - `handle_category_selected(callback, category)`: список шаблонов
   - `handle_template_preview(callback, template_id)`: превью + `[✅ Использовать]` `[◀ Назад]`
   - `handle_use_template(callback, template_id)`:
     - Подставить текст в FSM data["text"]
     - Запустить wizard с шага `waiting_topic` (текст уже заполнен)

> 🤖 **Промпт для Qwen Code:**
> ```
> Создай раздел шаблонов рекламных сообщений для aiogram 3. TEMPLATES dict с 7 категориями,
> 3+ шаблона в каждой. Навигация: меню категорий → список → превью → "Использовать".
> При "Использовать" — сохранить текст в FSM state data и перейти к шагу выбора
> тематики wizard-а (пропустить шаг ввода текста).
> ```

✅ **ЧЕКПОИНТ** — шаблон выбирается, подставляется в wizard, пользователь продолжает с шага фильтров

---

### Шаг 11 — Экраны аналитики в боте
> 🌿 **Ветка:** `feature/analytics-screens`

> ⚠️ **ПЕРЕД НАЧАЛОМ:**
> - ✓ belin завершил Шаг 13: `analytics_service.get_user_summary()` и `get_campaign_stats()` готовы

1. Создать `src/bot/handlers/analytics.py`:
   - `handle_user_summary(callback)`:
     ```
     📊 Ваша аналитика за 30 дней
     📤 Всего отправлено: {total_sent}
     ✅ Успешность: {avg_rate}%
     🏆 Топ тематика: {top_topic}
     ```
   - `handle_campaign_stats(callback, campaign_id)`:
     - Прогресс-бар через Unicode: `████░░░░ 65%`
     - Кнопка `[📄 Скачать PDF]`
   - `handle_top_chats(callback)`:
     - Топ-5 чатов по success_rate: название, % успеха, кол-во отправок

> 🤖 **Промпт для Qwen Code:**
> ```
> Создай aiogram 3 обработчики аналитики. handle_user_summary: HTML-карточка
> со статистикой за 30 дней. handle_campaign_stats(campaign_id): статистика с
> Unicode прогресс-баром ("▓▓▓▓▓░░░░░ 52%") и кнопкой скачать PDF.
> handle_top_chats: топ-5 чатов с процентом успеха.
> ```

✅ **ЧЕКПОИНТ** — аналитика отображается, прогресс-бар верный, PDF скачивается

---

## 📱 SPRINT 4 — TELEGRAM MINI APP

---

### Шаг 12 — Инициализация Mini App — Vite + React + TypeScript
> 🌿 **Ветка:** `feature/mini-app-setup`

> ⚠️ **ПЕРЕД НАЧАЛОМ:**
> - ✓ Sprint 3 смержен в `develop`
> - ✓ belin завершил Шаг 14: FastAPI роутеры `/api/*` работают с JWT
> - ✓ Node.js 20+ установлен

```bash
cd mini_app
npm create vite@latest . -- --template react-ts
npm install @twa-dev/sdk axios react-router-dom recharts zustand
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

1. Настроить `vite.config.ts`:
   - `proxy: { "/api": "http://localhost:8001" }` для dev
   - `build.outDir: "../src/static/mini_app"`
2. Создать `src/api/client.ts`: axios instance, JWT Bearer interceptor, refresh logic
3. Создать `src/hooks/useTelegramWebApp.ts`:
   ```ts
   const tg = window.Telegram.WebApp;
   useEffect(() => { tg.ready(); tg.expand(); }, []);
   return { tg, user: tg.initDataUnsafe.user, colorScheme: tg.colorScheme };
   ```
4. Создать `src/store/authStore.ts`: zustand store с токеном и пользователем
5. Создать `src/pages/Auth.tsx`: POST /api/auth/login с initData → сохранить JWT

> 🤖 **Промпт для Qwen Code:**
> ```
> Создай Telegram Mini App на Vite + React + TypeScript. Настрой @twa-dev/sdk:
> tg.ready() и tg.expand() при инициализации. axios client с JWT Bearer interceptor
> и автообновлением токена. AuthStore на zustand.
> Auth страница: отправить initData на POST /api/auth/login, сохранить JWT.
> ```

✅ **ЧЕКПОИНТ** — `npm run dev` открывается, авторизация проходит, JWT сохраняется

---

### Шаг 13 — Dashboard и страница кампаний
> 🌿 **Ветка:** `feature/mini-app-dashboard`

> ⚠️ **ПЕРЕД НАЧАЛОМ:**
> - ✓ Шаг 12 завершён (Mini App стартует, JWT работает)
> - ✓ GET /api/analytics/summary возвращает данные
> - ✓ GET /api/campaigns возвращает список

1. Создать glassmorphism CSS переменные в `src/styles/glass.css`:
   ```css
   .glass {
     background: rgba(255,255,255,0.1);
     backdrop-filter: blur(12px);
     border: 1px solid rgba(255,255,255,0.2);
     border-radius: 16px;
   }
   /* Градиентный фон: linear-gradient(135deg, #667eea 0%, #764ba2 100%) */
   ```
2. Создать `src/components/GlassCard.tsx`: переиспользуемая glass-карточка
3. Создать `src/components/StatusBadge.tsx`: цветной badge по статусу кампании
4. Создать `src/pages/Dashboard.tsx`:
   - Карточка баланса (glass): большая цифра + кнопка "Пополнить"
   - Карточка статистики: отправлено / успешность / кампаний
   - `recharts LineChart`: активность за последние 7 дней
   - Список 3 последних кампаний со статусами
5. Создать `src/pages/Campaigns.tsx`:
   - Табы: Все / Активные / Завершённые
   - Таблица: название, StatusBadge, дата, число чатов, кнопка деталей
   - `CampaignDetail` modal: полные параметры + stats

> 🤖 **Промпт для Qwen Code:**
> ```
> Создай React Dashboard для Telegram Mini App. GlassCard: background rgba(255,255,255,0.1),
> backdrop-filter blur(12px), rounded-2xl. Dashboard: карточка баланса, recharts LineChart
> активности за 7 дней, список последних кампаний с StatusBadge.
> StatusBadge: разные цвета для done/queued/running/error/draft. Tailwind адаптив.
> ```

✅ **ЧЕКПОИНТ** — Dashboard показывает реальные данные, график строится, статусы верные

---

### Шаг 14 — Страница аналитики и биллинга в Mini App
> 🌿 **Ветка:** `feature/mini-app-analytics-billing`

> ⚠️ **ПЕРЕД НАЧАЛОМ:**
> - ✓ Шаг 13 завершён (Dashboard работает)
> - ✓ GET /api/analytics/* и /api/billing/history работают

1. Создать `src/pages/Analytics.tsx`:
   - `recharts BarChart`: сравнение кампаний по отправкам
   - `recharts PieChart`: распределение по тематикам
   - Таблица топ-10 чатов по success_rate
   - Переключатель периода: 7 / 30 / 90 дней
2. Создать `src/pages/Billing.tsx`:
   - Карточка текущего тарифа
   - 4 карточки планов для переключения
   - История транзакций через `react-window` (виртуальный список)
   - Иконка + дата + описание + сумма (зелёная/красная)
3. Создать `src/components/BottomNav.tsx`: нижняя навигация
   - 🏠 Главная / 📊 Кампании / 📈 Аналитика / 💳 Биллинг
   - Активный элемент: подчёркивание и другой цвет
4. Настроить `react-router-dom`: `/` → Dashboard, `/campaigns`, `/analytics`, `/billing`
5. Поддержка темы: `tg.colorScheme === "dark"` → тёмные CSS-переменные

> 🤖 **Промпт для Qwen Code:**
> ```
> Создай React страницы Analytics и Billing для Telegram Mini App. Analytics: BarChart
> сравнения кампаний + PieChart тематик (recharts), таблица топ чатов, переключатель
> 7/30/90 дней. Billing: 4 тарифных плана, история транзакций с react-window.
> BottomNav: 4 иконки, react-router-dom. Dark/light тема через Telegram.WebApp.colorScheme.
> ```

✅ **ЧЕКПОИНТ** — все 4 страницы работают, тёмная тема переключается, данные реальные

---

### Шаг 15 — Сборка Mini App и интеграция с Nginx
> 🌿 **Ветка:** `feature/mini-app-build`

> ⚠️ **ПЕРЕД НАЧАЛОМ:**
> - ✓ Шаги 12-14 завершены (все страницы работают)
> - ✓ belin завершил Шаг 15: Nginx конфиг готов с `location /` → static files

```bash
cd mini_app && npm run build
# убедиться что dist попадает в src/static/mini_app/
```

1. Проверить Nginx: `location / → alias /app/src/static/mini_app/`
2. Добавить кнопку Mini App в бота:
   ```python
   WebAppButton(text="📱 Открыть кабинет", web_app=WebAppInfo(url=settings.MINI_APP_URL))
   ```
3. Добавить `MINI_APP_URL` в `.env.example` и `settings.py`
4. Тест на мобильном Telegram: открыть Mini App, проверить авторизацию
5. Тест на Telegram Desktop: проверить адаптив

✅ **ЧЕКПОИНТ** — Mini App открывается кнопкой в боте, работает на mobile и desktop

---

## 🏁 SPRINT 5 — ФИНАЛЬНОЕ ТЕСТИРОВАНИЕ

---

### Шаг 16 — Сквозное тестирование всех сценариев
> 🌿 **Ветка:** `developer/tsaguria`

> ⚠️ **ПЕРЕД НАЧАЛОМ:**
> - ✓ belin завершил production деплой (Шаг 15)
> - ✓ Бот работает через HTTPS webhook
> - ✓ Mini App открывается с production URL

| Сценарий | Шаги | Ожидаемый результат |
|---|---|---|
| **1. Новый пользователь** | /start → регистрация → приветствие | Пользователь создан в БД |
| **2. Кампания вручную** | Название → текст → тематика → сейчас → подтверждение | Кампания в очереди |
| **3. Кампания через ИИ** | Выбрать ИИ → описание → 3 варианта → выбор → запуск | ИИ генерирует текст |
| **4. Шаблоны** | Шаблоны → IT → выбрать → wizard с pre-filled текстом | Шаблон подставляется |
| **5. Биллинг** | Пополнить 100₽ → YooKassa → подтверждение | Баланс обновился |
| **6. Аналитика** | /cabinet → кампании → статистика → PDF → Mini App | PDF скачивается |
| **7. Реферал** | Реф-ссылка → второй аккаунт → бонус | +20₽ начислено |
| **8. Запрещённый контент** | Создать кампанию с запрещённым словом | Блокировка с сообщением |
| **9. Кнопка "Назад"** | 3 шага wizard → назад 3 раза → шаг 1 | Корректный возврат |

1. Пройти все 9 сценариев на production
2. Составить баг-репорт → GitHub Issues
3. Передать список belin для исправления

✅ **ЧЕКПОИНТ** — все 9 сценариев пройдены, критических ошибок нет

---

### Шаг 17 — Документация UI и финальный README
> 🌿 **Ветка:** `feature/docs-ui`

1. Написать секцию "Пользовательский интерфейс" в `README.md`:
   - Скриншоты: главное меню, wizard, кабинет, Mini App Dashboard
   - GIF-анимации: FSM wizard и Mini App навигация
   - Описание всех команд: `/start`, `/help`, `/cabinet`, `/balance`, `/report`
2. Написать `USER_GUIDE.md` — руководство для конечного пользователя
3. Снять screen-запись: 2-минутное демо всего функционала

✅ **ЧЕКПОИНТ** — README содержит скриншоты и описание, демо-видео готово

---

> **ТВОЙ КОД — ЭТО ТО, ЧТО ВИДИТ КАЖДЫЙ ПОЛЬЗОВАТЕЛЬ. УДАЧИ, tsaguria! 🎨**
