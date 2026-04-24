import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Icon, ScreenHeader } from '@shared/ui'
import type { IconName } from '@shared/ui'

interface CategoryConf {
  id: string
  label: string
  icon: IconName
}

const HELP_CATEGORIES: CategoryConf[] = [
  { id: 'all', label: 'Все темы', icon: 'zap' },
  { id: 'advertiser', label: 'Для рекламодателя', icon: 'cabinet' },
  { id: 'owner', label: 'Для владельца', icon: 'channels' },
  { id: 'billing', label: 'Финансы', icon: 'wallet' },
  { id: 'legal', label: 'Документы', icon: 'docs' },
  { id: 'safety', label: 'Безопасность', icon: 'lock' },
]

interface FaqItem {
  cat: string
  q: string
  a: string
}

const FAQ: FaqItem[] = [
  {
    cat: 'advertiser',
    q: 'Как создать кампанию?',
    a: 'Перейдите в раздел «Кампании» → «Создать». Визард состоит из 7 шагов: категория → каналы → формат → текст креатива → AI-правки → оплата эскроу → ожидание подтверждения владельца канала.',
  },
  {
    cat: 'advertiser',
    q: 'Что такое эскроу и зачем оно нужно?',
    a: 'Эскроу — это временная заморозка средств на платформе. После оплаты деньги не попадают владельцу канала сразу, а «замораживаются». Перевод владельцу происходит только после того, как он опубликует ваш пост и пройдёт контрольный срок. Если публикация не состоялась — вы получаете полный возврат.',
  },
  {
    cat: 'advertiser',
    q: 'Политика возвратов',
    a: 'До подтверждения владельцем — возврат 100%. После подтверждения, но до публикации — 50%. Если владелец отклонил вашу заявку — 100% мгновенно. Возврат приходит на баланс в течение 5 минут.',
  },
  {
    cat: 'owner',
    q: 'Как добавить канал?',
    a: 'Добавьте бота @RekHarborBot администратором канала с правом «Публикация сообщений». Затем откройте «Каналы» → «Добавить» и укажите @username или Chat ID канала. Автопроверка займёт до 2 минут.',
  },
  {
    cat: 'owner',
    q: 'Как получить выплату?',
    a: 'Раздел «Выплаты» → «Запросить вывод». Минимальная сумма — 1 000 ₽. Обработка происходит в рабочие часы 09:00–22:00 МСК и занимает до 24 часов. Комиссия платформы — 1,5% от суммы.',
  },
  {
    cat: 'owner',
    q: 'Какие каналы не проходят модерацию',
    a: 'Каналы младше 60 дней, каналы с накрутками (детектим ER < 0,8%), тематики: ставки, крипта без лицензии, 18+, нелегальные услуги. Полный список — в разделе «Документы» → «Правила платформы».',
  },
  {
    cat: 'billing',
    q: 'Как пополнить баланс?',
    a: 'Кабинет → «Пополнить». Способы: банковская карта (Visa/Mir/Mastercard), СБП, ЮKassa, ЮMoney. Зачисление мгновенное, для карт — в течение 2 минут. Минимальное пополнение — 500 ₽.',
  },
  {
    cat: 'billing',
    q: 'Есть ли комиссия за пополнение?',
    a: 'Комиссии платформы нет. Банк может удерживать свою комиссию при оплате картой — обычно это 0–2,9% и зависит от вашего банка-эмитента.',
  },
  {
    cat: 'legal',
    q: 'Нужно ли быть самозанятым или ИП?',
    a: 'Для рекламодателей — нет, подойдёт физлицо. Для владельцев каналов при выплатах выше 60 000 ₽ в месяц потребуется статус самозанятого или ИП. Акты и чеки формируются автоматически.',
  },
  {
    cat: 'legal',
    q: 'Как работают акты оказанных услуг?',
    a: 'После каждой завершённой кампании платформа формирует акт и отправляет его обеим сторонам. Подписание возможно прямо на платформе — простой электронной подписью. Срок автоподписания — 5 рабочих дней.',
  },
  {
    cat: 'safety',
    q: 'Что делать при споре?',
    a: 'Откройте заявку и нажмите «Открыть спор». Опишите проблему и приложите скриншоты. Арбитр платформы рассмотрит спор в течение 48 часов. Решение обязательно для обеих сторон.',
  },
  {
    cat: 'safety',
    q: 'Как платформа защищает от накруток?',
    a: 'Мы отслеживаем метрики канала круглосуточно: ER, динамику подписчиков, источники трафика. При обнаружении накруток канал блокируется, рекламодатели получают возврат. Проверьте репутацию канала перед заказом — она видна в карточке.',
  },
]

interface PopLink {
  icon: IconName
  title: string
  sub: string
}

const POP_LINKS: PopLink[] = [
  { icon: 'docs', title: 'Правила платформы', sub: 'Обновлено 15 апреля 2026' },
  { icon: 'placement', title: 'Политика конфиденциальности', sub: 'Версия 3.2' },
  { icon: 'lock', title: 'Публичная оферта', sub: 'Договор с пользователями' },
  { icon: 'zap', title: 'API-документация', sub: 'Для тарифа Agency' },
]

interface SupportChannel {
  icon: IconName
  title: string
  sub: string
}

const SUPPORT_CHANNELS: SupportChannel[] = [
  { icon: 'telegram', title: '@RekHarborSupport', sub: 'Telegram · онлайн 24/7' },
  { icon: 'email', title: 'help@rekharbor.ru', sub: 'Email · ответ в течение 4 ч' },
  { icon: 'phone', title: '+7 495 222-11-44', sub: 'Пн–Пт, 09:00–22:00 МСК' },
]

export default function Help() {
  const navigate = useNavigate()
  const [cat, setCat] = useState('all')
  const [q, setQ] = useState('')
  const [openIdx, setOpenIdx] = useState<Set<number>>(new Set([0, 3]))

  const filtered = useMemo(() => {
    return FAQ.filter((item) => {
      if (cat !== 'all' && item.cat !== cat) return false
      if (q && !`${item.q} ${item.a}`.toLowerCase().includes(q.toLowerCase())) return false
      return true
    })
  }, [cat, q])

  const toggle = (i: number) => {
    setOpenIdx((prev) => {
      const next = new Set(prev)
      if (next.has(i)) next.delete(i)
      else next.add(i)
      return next
    })
  }

  return (
    <div className="max-w-[1280px] mx-auto">
      <ScreenHeader
        title="Чем можем помочь?"
        subtitle="Ответы на частые вопросы и связь с поддержкой за одну минуту"
      />

      <div className="relative bg-gradient-to-br from-harbor-card to-harbor-secondary border border-border rounded-2xl pt-7 pb-6 px-6 mb-5 text-center overflow-hidden">
        <div className="absolute top-0 left-0 right-0 h-[3px] bg-gradient-to-r from-accent to-accent-2" />

        <div className="font-display text-[22px] font-bold text-text-primary tracking-[-0.02em] mb-4">
          Что вы хотите узнать?
        </div>

        <div className="max-w-[560px] mx-auto flex items-center gap-2.5 py-3 px-4 bg-harbor-elevated border border-border rounded-xl shadow-md">
          <Icon name="search" size={18} className="text-text-tertiary" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Поиск по базе знаний…"
            className="flex-1 bg-transparent border-0 outline-none text-text-primary text-sm placeholder:text-text-tertiary"
          />
          <span className="text-[10.5px] font-mono text-text-tertiary py-0.5 px-1.5 border border-border rounded">
            ⌘K
          </span>
        </div>

        <div className="flex gap-1.5 justify-center mt-4 flex-wrap">
          {HELP_CATEGORIES.map((c) => {
            const on = cat === c.id
            return (
              <button
                key={c.id}
                onClick={() => setCat(c.id)}
                className={`flex items-center gap-1.5 py-1.5 px-3 text-[12.5px] font-medium rounded-2xl border transition-all ${
                  on
                    ? 'border-accent bg-accent-muted text-accent'
                    : 'border-border bg-harbor-card text-text-secondary hover:border-border-active'
                }`}
              >
                <Icon name={c.icon} size={13} />
                {c.label}
              </button>
            )
          })}
        </div>
      </div>

      <div className="grid gap-4 grid-cols-1 lg:[grid-template-columns:minmax(0,1.8fr)_minmax(280px,1fr)]">
        <div>
          {filtered.length === 0 ? (
            <div className="bg-harbor-card border border-dashed border-border rounded-xl p-[60px] text-center">
              <div className="inline-grid place-items-center w-14 h-14 rounded-[14px] bg-harbor-elevated text-text-tertiary mb-3.5">
                <Icon name="search" size={22} />
              </div>
              <div className="font-display text-base font-semibold text-text-primary mb-1">
                Ничего не найдено
              </div>
              <div className="text-[13px] text-text-secondary">
                Измените запрос или напишите в поддержку
              </div>
            </div>
          ) : (
            <div className="flex flex-col gap-2.5">
              {filtered.map((item, i) => {
                const open = openIdx.has(i)
                const catMeta = HELP_CATEGORIES.find((c) => c.id === item.cat)
                return (
                  <div
                    key={item.q}
                    className={`bg-harbor-card border rounded-[11px] overflow-hidden transition-colors ${
                      open ? 'border-border-active' : 'border-border'
                    }`}
                  >
                    <button
                      onClick={() => toggle(i)}
                      className="w-full py-3.5 px-[18px] flex items-center gap-3.5 bg-transparent border-0 cursor-pointer text-left"
                    >
                      <span className="w-8 h-8 rounded-lg bg-accent-muted text-accent grid place-items-center flex-shrink-0">
                        <Icon name={catMeta?.icon ?? 'info'} size={14} />
                      </span>
                      <div className="flex-1 min-w-0">
                        <div className="text-[13.5px] font-semibold text-text-primary">{item.q}</div>
                        <div className="text-[11px] text-text-tertiary mt-0.5 uppercase tracking-wider font-semibold">
                          {catMeta?.label ?? item.cat}
                        </div>
                      </div>
                      <Icon
                        name="chevron-down"
                        size={14}
                        className={`text-text-secondary transition-transform ${open ? 'rotate-180' : ''}`}
                      />
                    </button>
                    {open && (
                      <div className="pb-4 pl-16 pr-[18px] text-[13px] text-text-secondary leading-relaxed">
                        {item.a}
                        <div className="mt-2.5 flex gap-3.5 text-xs">
                          <button className="bg-transparent border-0 text-text-tertiary cursor-pointer flex items-center gap-1 p-0 hover:text-success transition-colors">
                            <Icon name="check" size={12} /> Полезно
                          </button>
                          <button className="bg-transparent border-0 text-text-tertiary cursor-pointer flex items-center gap-1 p-0 hover:text-danger transition-colors">
                            <Icon name="warning" size={12} /> Не помогло
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>

        <div className="flex flex-col gap-3.5">
          <div className="bg-gradient-to-br from-accent to-accent-2 rounded-xl p-5 text-white">
            <div className="flex items-center gap-2.5 mb-2.5">
              <Icon name="feedback" size={18} className="text-white" />
              <div className="font-display text-[15px] font-bold">Не нашли ответ?</div>
            </div>
            <div className="text-[13px] opacity-90 leading-[1.5] mb-3.5">
              Напишите в поддержку. Среднее время первого ответа — 14 минут.
            </div>
            <button
              onClick={() => navigate('/feedback')}
              className="w-full py-2.5 px-4 bg-white/20 border border-white/30 rounded-lg text-white text-[13px] font-semibold flex items-center justify-center gap-1.5 cursor-pointer backdrop-blur-sm hover:bg-white/30 transition-colors"
            >
              <Icon name="feedback" size={14} /> Написать в поддержку
            </button>
          </div>

          <div className="bg-harbor-card border border-border rounded-xl p-[18px]">
            <div className="font-display text-[13px] font-semibold text-text-primary mb-3">
              Другие каналы связи
            </div>
            <div className="flex flex-col gap-2">
              {SUPPORT_CHANNELS.map((c) => (
                <a
                  key={c.title}
                  href="#"
                  className="flex items-center gap-[11px] py-2.5 px-3 rounded-lg bg-harbor-elevated border border-border text-text-primary hover:border-border-active transition-colors"
                >
                  <span className="w-8 h-8 rounded-lg bg-accent-muted text-accent grid place-items-center flex-shrink-0">
                    <Icon name={c.icon} size={14} />
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="text-[13px] font-medium text-text-primary">{c.title}</div>
                    <div className="text-[11px] text-text-tertiary mt-px">{c.sub}</div>
                  </div>
                  <Icon name="arrow-right" size={12} className="text-text-tertiary" />
                </a>
              ))}
            </div>
          </div>

          <div className="bg-harbor-card border border-border rounded-xl p-[18px]">
            <div className="font-display text-[13px] font-semibold text-text-primary mb-3">
              Популярные документы
            </div>
            <div className="flex flex-col gap-1">
              {POP_LINKS.map((l) => (
                <a
                  key={l.title}
                  href="#"
                  className="flex items-center gap-2.5 py-2 px-1.5 rounded-md hover:bg-harbor-elevated transition-colors"
                >
                  <Icon name={l.icon} size={14} className="text-text-secondary" />
                  <div className="flex-1 min-w-0">
                    <div className="text-[12.5px] font-medium text-text-primary">{l.title}</div>
                    <div className="text-[11px] text-text-tertiary mt-px">{l.sub}</div>
                  </div>
                  <Icon name="external" size={11} className="text-text-tertiary" />
                </a>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
