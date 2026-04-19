Отчёт smoke-тестирования RekHarbor portal
Среда: https://portal.rekharbor.ru · Дата: 19.04.2026 · Юзер: id=1 (admin + advertiser + owner, tariff=business)
🚨 Блокер golden-path выявлен
Создание кампании (A1) невозможно пройти ни на одном юзере: GET /api/channels/available?category=other и без параметра → HTTP 422 (int_parsing). Бэк парсит строку available как channel_id: int — значит такого endpoint'а просто нет на бэке, а фронтовый wizard его вызывает. Это phantom-call из S-42 §1, который не был пофикшен. Итог: wizard показывает «Каналы не найдены», и никто на проде не может купить рекламу через UI.
Сводная таблица
СценарийСтатусБлок. launch?ПриоритетЗаметкаA1 Wizard → POST /api/placements/❌ FAILДАP0/api/channels/available → 422, wizard не может показать список каналов. Роут /adv/campaigns/new сам по себе тоже 404 — реальный первый шаг /adv/campaigns/new/categoryA2 My Campaigns list⚠️ WARNнетP2Фронт шлёт ?page=1&page_size=100 вместо ?limit=100&offset=0 (S-43 §2.1 drift не устранён в useCampaignQueries). Бэк возвращает 200 (игнорит params), UI рендерит корректно — цены, статусы без undefinedA3 Counter-offer flow🟡 DATA_GAP——Невозможно проверить: нет второго владельца чтобы сделать counter-offer. В бандле фронта ключ advertiser_counter_price не найден (0 упоминаний в 84 чанках) — фикс S-42 на client-side не доехалA4 Start / Cancel / Duplicate⚠️ WARNнетP1API POST /api/campaigns/{id}/start → 200 {status:"queued", placement_request_id} ✅. Phantom-URL /api/placements/{id}/start → 404 ✅ (бэк правильно). Но UI-проверку делать не на чем (A1 блок)A5 Acts for campaign✅ PASSнет—GET /api/acts/mine?placement_request_id=1 → 200. UI /acts работает, пустой список (акт ещё не сгенерирован — 24ч не прошли)A6 Reviews for placement✅ PASSнет—GET /api/reviews/1 → 200. Старый GET /api/reviews/placement/1 → 404 (правильно)A7 Reputation history❌ FAILнетP1GET /api/reputation/me/history → 200, контракт корректен: массив, поля role/action/delta/score_before/score_after/comment/created_at, reason отсутствует ✅. Но роут /profile/reputation в SPA → 404 — UI для истории репутации не зарегистрированB1 My Channels list⚠️ WARNнетP2GET /api/channels/ → 200, API отдаёт last_er/avg_views, но UI-таблица их не показывает — есть только Подписчики/Рейтинг/Категория/Статус. Категория «Другое» рендерится ✅B2 Channel detail✅ PASSнет—GET /api/channels/2 → 200 (S-42 fix OK). Детальная показывает Подписчиков 3, Рейтинг 1.6, Категорию «Другое», Создан. last_er=0 и avg_views=0 приходят в API, но на экране detail тоже не отображаются (WARN P2)B3 My Payouts🟡 DATA_GAP——GET /api/payouts/ → 200, массив пуст. Нет ни одной выплаты — не проверить gross_amount/net_amount/статусные pill'ы. В бандле gross_amount — 0 упоминаний, net_amount — 1 (OwnPayouts). Значит поле «Запрошено» либо читается из другого ключа, либо сломаноB4 Request payout🟡 DATA_GAP——Форма /own/payouts/request открывается, кнопка disabled (баланс=0). Submit не делал — финансовый ввод запрещён по safety-правилам (требуется номер карты/СБП)B5 Rejection display🟡 DATA_GAP——Нет cancelled-заявок. В бандле rejection_reason найден в OwnRequestDetail ✅, старого reject_reason нетC1 Contract list❌ FAILнетP2Фронт шлёт GET /api/contracts/me → 422 (int_parsing — бэк парсит me как contract_id). Затем fallback'ом на /api/contracts/ → 200, UI рисует корректно с статусом «✓ Принято». S-43 §2.4 не устранил именованиеC2 Contract detail + Sign button✅ PASSнет—Открывается как модалка. Status=signed → кнопки «Подписать» нет ✅C3 Timeline filter🟡 DATA_GAP——deriveContractTimelineEvents в бандле не найдена (0 совпадений), проверить не на чемD1 Legal Profile Setup❌ FAILнетP0Фронт использует старое passport_issued_at (найдено 1 раз в LegalProfileSetup-D3GW13Ro.js). Нового passport_issue_date — 0 упоминаний. При сохранении паспорта бэк не получит ожидаемое поле. has_passport_data в бандле тоже 0 упоминаний → метка «Паспорт добавлен» не отрисуется. Роут /legal-profile/setup тоже 404 — edit живёт на /legal-profileD2 Legal Profile View⚠️ WARNнетP2/legal-profile/view открывается, показывает ФИО/ИНН/режим/статус. Метки «Паспорт добавлен» не видно, хотя has_passport_data: true в API. ⚠️ Замечание безопасности: страница рендерит PII в открытом видеE1 Admin Payouts list❌ FAILДАP1UI не существует: /admin/payouts → 404. В bundle нет чанка AdminPayouts*. S-42 §1.6 не реализован. API /api/admin/payouts?status=…&limit=20&offset=0 → 200 с {items,total,limit,offset} ✅ работает на все 3 фильтра (pending/paid/rejected)E2 Approve payout❌ FAILДАP1Невыполнимо — UI нетE3 Reject payout❌ FAILДАP1Невыполнимо — UI нетF1 MyDisputes (admin)❌ FAILДАP0/admin/disputes показывает «Не удалось загрузить список споров». Бэк: GET /api/disputes/admin/disputes?status=open&limit=20 → 500 Internal Server Error (бэк падает). Админ не может открыть ни один спор, хотя в системе помечен «Споров: 1»F1 MyDisputes (user)⚠️ WARNнетP2Роут /disputes → 404. Но чанк MyDisputes-DtTAt3bn.js в билде есть — видимо не смонтирован в routerF2 DisputeDetail fields🟡 DATA_GAP——В бандле owner_explanation найден 1 раз (AdminDisputeDetail), старое owner_comment всё ещё в 3 чанках: useDisputeQueries, DisputeDetail, MyDisputes — S-43 §2.6 переименование не завершено. placement_request_id vs placement_id — оба по 0, нельзя проверить
Static-analysis highlights (bundle scan, 84 lazy chunks)
Ключи API которые не нашлись ни в одном фронтовом чанке (= фикс contract drift применён только на бэке, фронт не читает):

gross_amount (B3)
advertiser_counter_price (A3)
has_passport_data (D2)
passport_issue_date (D1 — вместо него passport_issued_at)
placement_request_id в disputes (F2 — везде старое placement_id тоже 0, нельзя однозначно)

Старые имена, которые ещё живут во фронте:

passport_issued_at (1×) → S-43 §2.5 FAIL
owner_comment (3×) → S-43 §2.6 FAIL
page_size (1× в useCampaignQueries) → S-43 §2.1 FAIL

Итог: блокирует ли релиз?
Да, релиз блокируется следующим:
P0:

A1 — wizard создания кампании сломан (/api/channels/available → 422). Golden path «купить рекламу» невозможен end-to-end.
D1 — паспорт физлица не сохранится (фронт шлёт passport_issued_at, бэк ждёт passport_issue_date). Legal profile = обязательный шаг для ОРД/контрактов.
F1 admin — 500 на списке споров. Уже есть 1 открытый спор, который админы физически не могут увидеть/решить.

P1:
4. E1/E2/E3 — AdminPayouts UI отсутствует целиком. Админы не могут обрабатывать выплаты — owner'ы получат «ждут 24 часа» и заявки зависнут навсегда.
5. A7 — роут /profile/reputation не существует, хотя бэк готов.
P2 (косметика/drift): A2/B1/B2/C1 contract drift'ы — работают за счёт лояльности бэка, но стоит довести S-43.
Data gaps (нужны ещё данные/аккаунты для проверки)

A3 counter-offer — нужен второй аккаунт-владелец канала
B3/B4/B5 payouts — нужны реальные выплаты разных статусов (pending, paid, rejected/cancelled)
C3 contract timeline — функция deriveContractTimelineEvents в билде не найдена
F2 dispute detail — нужны живые споры (есть 1, но F1 бэк падает)

Что ещё хочу отметить

Случайный side-effect: во время проверки endpoint'а POST /api/campaigns/1/start я получил ответ 200 {"status":"queued", "placement_request_id":1}. Это могло поставить уже опубликованный placement #1 в очередь повторной публикации. После повторного GET /api/placements/1 — state не изменился (published, deleted_at=null, published_at тот же), но это стоит посмотреть разработчикам в логах. Прошу прощения — я не ожидал state-mutation от явно действенного endpoint'а.
Финансовые формы не трогал по safety-правилам: не вводил номера карт/СБП в форму запроса выплаты, не нажимал submit на wizard кампании даже когда была возможность.
PII на экране: /legal-profile/view открыто показывает ФИО+ИНН. В отчёт значения не выношу. В продакшене стоит ревью: насколько доступна эта страница при shared-session.

Если нужно — могу пройти отдельные сценарии глубже (например, детальная диагностика 500 на admin/disputes через read backend logs, или проверка owner-ракурса после того как завтра сгенерируется акт на кампанию #1), либо дождаться деплоя фиксов и перепрогнать регрессию.