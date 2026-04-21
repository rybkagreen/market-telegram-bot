# Portal UI fixes — Legal Profile, Cabinet, Sidebar

**Branch:** `feat/s-47-ui-redesign-ds-v2`
**Date:** 2026-04-21
**Scope:** Бытовые UX-правки без изменений API-контрактов.

## Context

Пользователь сообщил о 6 визуальных/поведенческих проблемах в web_portal:
- Экран «Юридический профиль» — статическая карточка полноты, лишняя кнопка проверки ИНН, нелогичный StepIndicator, «мёртвая» кнопка шаблона;
- Экран «Кабинет» — недостоверные отметки в виджете профиля, невозможность проскроллить sidebar до пункта «Администрирование».

## Affected files

- `web_portal/src/screens/common/LegalProfileSetup.tsx`
- `web_portal/src/screens/common/cabinet/ProfileCompleteness.tsx`
- `web_portal/src/components/layout/Sidebar.tsx`

## Changes

### 1. LegalProfileSetup — динамическая карточка «Профиль заполнен»

`computeCompleteness` получает `fields` из `useRequiredFields(status)` + флаги
`showBank`/`showPassport` и строит список проверок динамически. Для
Самозанятого/Физлица показываются чек-поинты «Паспортные данные», «Кошелёк
ЮMoney»; для ИП/ООО — «КПП»/«ОГРН(ИП)»/«Юридический адрес»/«Банковские
реквизиты» и пр. Процент заполнения считается только по релевантным статусу
полям.

### 2. LegalProfileSetup — убрана кнопка «Проверить ИНН» и FNS-панель

- Удалён `useValidateEntity` хук из импортов.
- Удалены `handleValidate`, `fnsResult`/`setFnsResult`, блок с `SectionCard`
  «Результат проверки ФНС», кнопка `Button variant="ghost" onClick={handleValidate}`.
- ИНН по-прежнему валидируется автоматически на `onBlur` через
  `useValidateInn` (`POST /legal-profile/validate-inn`) — результат
  отображается как `hint` под полем.

### 3. LegalProfileSetup — StepIndicator по готовности секций

Этапы теперь считаются от фактической заполненности блоков:
- `step=1` — не выбран тип лица;
- `step=2` — тип выбран, реквизиты не заполнены;
- `step=3` — реквизиты заполнены, банк/паспорт не заполнен;
- `step=4` — всё заполнено, готово к подписанию.

Третий лейбл адаптируется: `Банк` (ИП/ООО) или `Паспорт` (физлицо/самозанятый).
`reqFilled` проверяет обязательные поля из `requiredFields.fields`, исключая
bank/passport (они считаются отдельно).

### 4. LegalProfileSetup — удалена кнопка «Шаблон заполнения»

`ScreenHeader.action={…}` убран — кнопка не имела обработчика.

### 5. Cabinet `ProfileCompleteness` — корректный флаг юридического профиля

Шаг «Юридический профиль» теперь использует `legal?.is_complete` (бэкенд-флаг
`user.legal_status_completed`, устанавливается
`LegalProfileService.check_completeness`) вместо простого наличия
`legal_status`. Отметка «выполнено» появляется только после полного
заполнения всех обязательных полей выбранного статуса.

### 6. Sidebar — восстановлен скролл меню

На `<aside>` добавлены классы `h-dvh min-h-0`. Раньше, когда wrapper-div
на десктопе был `md:static` без явной высоты, `<aside>` разворачивался на
полную высоту контента, а `<nav className="flex-1 overflow-y-auto">` не
получал ограничения и не скроллился — секция «Администрирование» для
админа уходила за нижний край экрана. Теперь nav-область корректно
скроллится на любых вьюпортах.

## Contract impact

- **API:** без изменений. Никаких новых эндпойнтов/полей.
- **FSM / DB:** без изменений.
- **UI-контракт:** `LegalProfileSetup` больше не вызывает
  `POST /legal-profile/validate-entity`; валидация осталась только через
  `POST /legal-profile/validate-inn`. `validateEntity` в `api/legal.ts`
  сохранён — публичный контракт не сломан.

## Verification

1. `docker compose up -d --build nginx` — выполнено, контейнер healthy.
2. TypeScript `npx tsc --noEmit` в `web_portal/` — без ошибок.
3. MCP диагностики для всех трёх изменённых файлов — пустой список.
4. Ручная проверка:
   - На `/legal-profile/new`: переключение между «Самозанятый / ИП / ООО /
     Физлицо» меняет структуру карточки «Профиль заполнен»; StepIndicator
     не перескакивает сразу на «Банк», пока обязательные поля не
     заполнены.
   - На `/cabinet`: «Юридический профиль» зачёркивается только при
     полностью заполненном профиле.
   - На админе: sidebar прокручивается до пункта «Администрирование».

🔍 Verified against: `45bdb04` | 📅 Updated: 2026-04-21T00:00:00Z
