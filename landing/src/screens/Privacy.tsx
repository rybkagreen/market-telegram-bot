import Header from '../components/Header'
import Footer from '../components/Footer'

const LAST_UPDATED = '2026-04-09'

const SECTION_STYLE = {
  fontFamily: 'var(--font-ui)',
  fontSize: '0.9375rem',
  color: 'var(--color-text-secondary)',
  lineHeight: 1.7,
}

const H2_STYLE = {
  fontFamily: 'var(--font-display)',
  fontWeight: 600,
  fontSize: '1.125rem',
  color: 'var(--color-text-dark)',
}

export default function Privacy() {
  return (
    <>
      <Header />
      <main
        className="max-w-3xl mx-auto px-4 sm:px-6 pt-28 pb-24"
        style={{ fontFamily: 'var(--font-ui)' }}
      >
        <h1
          className="mb-2"
          style={{
            fontFamily: 'var(--font-display)',
            fontWeight: 600,
            fontSize: '1.9375rem',
            color: 'var(--color-text-dark)',
            lineHeight: 1.2,
          }}
        >
          Политика конфиденциальности
        </h1>
        <p
          className="mb-10 text-sm"
          style={{ fontFamily: 'var(--font-ui)', color: 'var(--color-text-muted)' }}
        >
          Последнее обновление: {LAST_UPDATED}
        </p>

        {/* 1. Оператор */}
        <section className="mb-8" aria-labelledby="section-operator">
          <h2 id="section-operator" className="mb-3" style={H2_STYLE}>
            1. Оператор персональных данных
          </h2>
          <p style={SECTION_STYLE}>
            Оператором персональных данных является{' '}
            <strong>ООО «АЛГОРИТМИК АРТС»</strong> (далее — «Платформа», «мы», «нас»).
            Платформа предоставляет сервис рекламной биржи RekHarbor, доступный через
            Telegram-бот @RekHarborBot и веб-портал portal.rekharbor.ru.
          </p>
        </section>

        {/* 2. Данные */}
        <section className="mb-8" aria-labelledby="section-data">
          <h2 id="section-data" className="mb-3" style={H2_STYLE}>
            2. Какие данные мы собираем
          </h2>
          <p className="mb-3" style={SECTION_STYLE}>
            При использовании сервиса мы собираем следующие данные:
          </p>
          <ul
            className="list-disc list-inside flex flex-col gap-2"
            style={SECTION_STYLE}
          >
            <li>
              <strong>Данные Telegram-аккаунта:</strong> Telegram ID, имя пользователя
              (username), язык интерфейса — передаются автоматически при авторизации
              через Telegram Login Widget.
            </li>
            <li>
              <strong>Данные каналов:</strong> идентификатор канала, название, количество
              подписчиков, категория — для обеспечения работы биржи.
            </li>
            <li>
              <strong>Юридические данные (опционально):</strong> ИНН, название организации,
              паспортные данные — только при заполнении юридического профиля, хранятся
              в зашифрованном виде.
            </li>
            <li>
              <strong>Платёжные данные:</strong> история транзакций и пополнений — без
              хранения данных банковских карт (обрабатываются YooKassa).
            </li>
            <li>
              <strong>Технические данные:</strong> IP-адрес (для защиты от злоупотреблений),
              данные запросов к API.
            </li>
          </ul>
        </section>

        {/* 3. Цели */}
        <section className="mb-8" aria-labelledby="section-purposes">
          <h2 id="section-purposes" className="mb-3" style={H2_STYLE}>
            3. Цели обработки персональных данных
          </h2>
          <ul className="list-disc list-inside flex flex-col gap-2" style={SECTION_STYLE}>
            <li>Предоставление сервиса рекламной биржи RekHarbor.</li>
            <li>Авторизация и аутентификация пользователей.</li>
            <li>Обработка платёжных операций (пополнение, выплаты, эскроу).</li>
            <li>Выполнение требований законодательства о рекламе (регистрация в ОРД).</li>
            <li>Обеспечение безопасности и защиты от мошенничества.</li>
            <li>Поддержка пользователей и урегулирование споров.</li>
          </ul>
        </section>

        {/* 4. Cookie */}
        <section className="mb-8" aria-labelledby="section-cookies">
          <h2 id="section-cookies" className="mb-3" style={H2_STYLE}>
            4. Файлы cookie
          </h2>
          <p style={SECTION_STYLE}>
            Сайт rekharbor.ru использует технические cookie, необходимые для работы
            интерфейса (сохранение предпочтений, защита от CSRF). Аналитические cookie
            используются только при наличии вашего согласия, выраженного через баннер
            cookie-согласия. Вы можете отозвать согласие в любой момент, нажав
            «Отозвать» в баннере или изменив настройки браузера.
          </p>
        </section>

        {/* 5. Передача третьим лицам */}
        <section className="mb-8" aria-labelledby="section-third-party">
          <h2 id="section-third-party" className="mb-3" style={H2_STYLE}>
            5. Передача данных третьим лицам
          </h2>
          <p className="mb-3" style={SECTION_STYLE}>
            Мы передаём данные третьим лицам только в следующих случаях:
          </p>
          <ul className="list-disc list-inside flex flex-col gap-2" style={SECTION_STYLE}>
            <li>
              <strong>Яндекс ОРД</strong> — передача данных рекламного размещения
              (содержание, участники, сроки) в целях регистрации в Операторе Рекламных
              Данных. Обязательно по требованию ФЗ «О рекламе».
            </li>
            <li>
              <strong>YooKassa (НКО «ЮМани»)</strong> — для обработки платежей
              (пополнение баланса, выплаты владельцам каналов). Данные банковских карт
              обрабатываются напрямую YooKassa и не хранятся на наших серверах.
            </li>
          </ul>
          <p className="mt-3" style={SECTION_STYLE}>
            Мы не продаём и не передаём ваши данные рекламным сетям или иным третьим
            лицам без вашего согласия.
          </p>
        </section>

        {/* 6. Права пользователя */}
        <section className="mb-8" aria-labelledby="section-rights">
          <h2 id="section-rights" className="mb-3" style={H2_STYLE}>
            6. Ваши права
          </h2>
          <p className="mb-3" style={SECTION_STYLE}>
            В соответствии с 152-ФЗ вы имеете право:
          </p>
          <ul className="list-disc list-inside flex flex-col gap-2" style={SECTION_STYLE}>
            <li>Получить информацию о хранящихся персональных данных.</li>
            <li>Исправить неточные или неполные данные.</li>
            <li>Удалить данные («право на забвение»), если это не противоречит законодательству.</li>
            <li>Отозвать согласие на обработку данных.</li>
            <li>Обратиться с жалобой в Роскомнадзор.</li>
          </ul>
        </section>

        {/* 7. Хранение и защита */}
        <section className="mb-8" aria-labelledby="section-storage">
          <h2 id="section-storage" className="mb-3" style={H2_STYLE}>
            7. Хранение и защита данных
          </h2>
          <p style={SECTION_STYLE}>
            Данные хранятся на серверах, расположенных на территории Российской Федерации.
            Конфиденциальные поля (ИНН, паспортные данные, контакты) хранятся в
            зашифрованном виде (AES-256). Доступ к базам данных строго ограничен.
            Действия с данными фиксируются в журнале аудита.
          </p>
        </section>

        {/* 8. Контакты */}
        <section className="mb-8" aria-labelledby="section-contacts">
          <h2 id="section-contacts" className="mb-3" style={H2_STYLE}>
            8. Контакты и обращения
          </h2>
          <p style={SECTION_STYLE}>
            По вопросам обработки персональных данных, реализации ваших прав или подачи
            обращений обращайтесь через Telegram-бот{' '}
            <a
              href="https://t.me/RekHarborBot"
              target="_blank"
              rel="noopener noreferrer"
              className="underline underline-offset-4 transition-opacity hover:opacity-70"
              style={{ color: 'var(--color-brand-blue)' }}
            >
              @RekHarborBot
            </a>
            . Ответственный за обработку персональных данных: ООО «АЛГОРИТМИК АРТС».
          </p>
        </section>

        <p
          className="text-xs pt-4 border-t"
          style={{
            fontFamily: 'var(--font-ui)',
            color: 'var(--color-text-muted)',
            borderColor: 'var(--color-border)',
          }}
        >
          © 2024–2026 ООО «АЛГОРИТМИК АРТС». Все права защищены.
          <br />
          Дата последнего обновления: {LAST_UPDATED}
        </p>
      </main>
      <Footer />
    </>
  )
}
