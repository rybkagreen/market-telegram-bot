"""
Celery tasks for tax compliance and calendar reminders.
"""

import logging
from datetime import date

from src.db.repositories.user_repo import UserRepository
from src.db.session import async_session_factory
from src.tasks.notification_tasks import notify_user

logger = logging.getLogger(__name__)

# =============================================================================
# TAX DEADLINES (Russian tax calendar for ИП УСН)
# =============================================================================

# УСН квартальные авансовые платежи: 25-е число месяца, следующего за кварталом
USN_QUARTERLY_DEADLINES = [
    # (month, day, description)
    (4, 25, "УСН аванс за Q1"),  # 25 апреля
    (7, 25, "УСН аванс за Q2"),  # 25 июля
    (10, 25, "УСН аванс за Q3"),  # 25 октября
    (4, 25, "УСН годовой / Q4"),  # 25 апреля след. года
]

# НДФЛ (для налоговых агентов): 28-е число каждого месяца
NDFL_MONTHLY_DEADLINE = (28, "НДФЛ за предыдущий месяц")

# НПД (самозанятые): 25-е число месяца, следующего за отчётным
NPD_MONTHLY_DEADLINE = (25, "НПД за предыдущий месяц")


def _get_upcoming_tax_deadlines(days_ahead: int = 14) -> list[dict]:
    """Рассчитать ближайшие налоговые дедлайны.

    Args:
        days_ahead: Горизонт планирования (дней).

    Returns:
        Список диктов с deadline_date, description, tax_type.
    """
    today = date.today()
    current_year = today.year
    deadlines: list[dict] = []

    cutoff = (
        today.replace(day=today.day + days_ahead)
        if today.day + days_ahead <= 28
        else today.replace(month=today.month + 1, day=min(days_ahead - (28 - today.day), 28))
    )

    # УСН квартальные
    for month, day, desc in USN_QUARTERLY_DEADLINES:
        deadline_year = current_year
        # Если дата уже прошла в этом году, берим следующий год
        deadline_date = date(deadline_year, month, day)
        if deadline_date < today:
            deadline_date = date(deadline_year + 1, month, day)

        if today <= deadline_date <= cutoff:
            deadlines.append(
                {
                    "deadline_date": deadline_date,
                    "description": desc,
                    "tax_type": "USN",
                }
            )

    # НДФЛ ежемесячный (28 число)
    ndfl_deadline_month = today.month
    ndfl_day = NDFL_MONTHLY_DEADLINE[0]
    ndfl_date = date(current_year, ndfl_deadline_month, ndfl_day)
    if ndfl_date < today:
        ndfl_deadline_month += 1
        if ndfl_deadline_month > 12:
            ndfl_deadline_month = 1
        ndfl_date = date(current_year + 1, ndfl_deadline_month, ndfl_day)

    if today <= ndfl_date <= cutoff:
        deadlines.append(
            {
                "deadline_date": ndfl_date,
                "description": f"НДФЛ за {ndfl_deadline_month - 1 if ndfl_deadline_month > 1 else 12}-й месяц",
                "tax_type": "NDFL",
            }
        )

    # Сортируем по дате
    deadlines.sort(key=lambda d: d["deadline_date"])

    # Возвращаем ближайшие 3
    return deadlines[:3]


async def _notify_admins(deadlines: list[dict]) -> None:
    """Отправить уведомления администраторам о налоговых дедлайнах.

    Args:
        deadlines: Список дедлайнов из _get_upcoming_tax_deadlines().
    """
    if not deadlines:
        return

    lines = []
    for d in deadlines:
        date_str = d["deadline_date"].strftime("%d.%m.%Y")
        lines.append(f"📅 {date_str} — {d['description']} ({d['tax_type']})")

    message = (
        "⚠️ <b>Налоговый календарь</b>\n\n"
        "Ближайшие дедлайны:\n\n"
        + "\n".join(lines)
        + "\n\nПроверьте соответствие данных в системе."
    )

    # Отправляем всем админам
    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        admins = await user_repo.get_all_admins()

        for admin in admins:
            if not admin.telegram_id:
                continue
            try:
                notify_user.delay(
                    telegram_id=admin.telegram_id,
                    message=message,
                    parse_mode="HTML",
                )
                logger.info(f"Tax reminder sent to admin #{admin.id}")
            except Exception as e:
                logger.error(f"Failed to send tax reminder to admin #{admin.id}: {e}")
