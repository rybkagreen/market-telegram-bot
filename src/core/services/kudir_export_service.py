"""KudirExportService — экспорт КУДиР в PDF и CSV.

Использует Jinja2 + WeasyPrint для PDF и stdlib csv для CSV.
"""

import csv
import io
import logging
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings as _settings
from src.core.services.tax_aggregation_service import TaxAggregationService
from src.db.repositories.tax_repo import TaxRepository

logger = logging.getLogger(__name__)

# ─── Jinja2 / WeasyPrint detection ───

try:
    from jinja2 import (  # type: ignore[import-not-found]
        Environment,
        FileSystemLoader,
        select_autoescape,
    )

    USE_JINJA2 = True
except ImportError:
    USE_JINJA2 = False
    Environment = None  # type: ignore[assignment,misc]

try:
    import weasyprint  # type: ignore[import-not-found]

    USE_WEASYPRINT = True
except ImportError:
    USE_WEASYPRINT = False

TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"
KUDIR_TEMPLATE = "kudir/kudir_book.html"


class KudirExportService:
    """Сервис для экспорта КУДиР в PDF и CSV."""

    @classmethod
    async def generate_kudir_pdf(cls, session: AsyncSession, year: int, quarter: int) -> BytesIO:
        """Сгенерировать PDF книги учёта доходов (КУДиР) за квартал.

        Args:
            session: Асинхронная сессия.
            year: Год.
            quarter: Номер квартала (1-4).

        Returns:
            BytesIO с содержимым PDF.

        Raises:
            ValueError: Если квартал не найден или PDF генерация не удалась.
        """
        # Получить сводку
        summary = await TaxAggregationService.get_quarterly_summary(session, year, quarter)

        # Рендерить HTML
        html = cls._render_kudir_html(summary)

        # Конвертировать в PDF
        if USE_WEASYPRINT:
            pdf_bytes = BytesIO()
            weasyprint.HTML(string=html).write_pdf(target=pdf_bytes)
            pdf_bytes.seek(0)
            logger.info(
                f"KUDiR PDF generated: {year}-Q{quarter}, {len(pdf_bytes.getvalue())} bytes"
            )
            return pdf_bytes

        raise RuntimeError("WeasyPrint not available — PDF generation disabled")

    @classmethod
    async def generate_kudir_csv(cls, session: AsyncSession, year: int, quarter: int) -> str:
        """Сгенерировать CSV книги учёта доходов и расходов (КУДиР) за квартал.

        Разделитель: ; (требование ФНС). Секции: Доходы, Расходы.

        Args:
            session: Асинхронная сессия.
            year: Год.
            quarter: Номер квартала (1-4).

        Returns:
            Строка CSV с заголовками, строками доходов/расходов и итогами.
        """
        from decimal import Decimal

        quarter_str = TaxAggregationService._get_quarter_string(year, quarter)
        repo = TaxRepository(session)
        records = await repo.get_by_quarter(quarter_str)

        output = io.StringIO()
        writer = csv.writer(output, delimiter=";")

        # Заголовки
        writer.writerow(
            [
                "№",
                "Дата",
                "Тип операции",
                "Категория",
                "Описание",
                "Сумма дохода (₽)",
                "Сумма расхода (₽)",
            ]
        )

        # Секция: Доходы
        total_income = Decimal("0")
        for r in records:
            if r.operation_type != "income":
                continue
            date_str = r.operation_date.strftime("%d.%m.%Y") if r.operation_date else ""
            writer.writerow(
                [
                    r.entry_number,
                    date_str,
                    "Доход",
                    "",
                    r.description,
                    str(r.income_amount),
                    "",
                ]
            )
            total_income += r.income_amount

        # Разделитель
        writer.writerow(["", "", "", "", "", "", ""])

        # Секция: Расходы
        total_expenses = Decimal("0")
        for r in records:
            if r.operation_type != "expense" or r.expense_amount is None:
                continue
            date_str = r.operation_date.strftime("%d.%m.%Y") if r.operation_date else ""
            writer.writerow(
                [
                    r.entry_number,
                    date_str,
                    "Расход",
                    r.expense_category or "",
                    r.description,
                    "",
                    str(r.expense_amount),
                ]
            )
            total_expenses += r.expense_amount

        # Итого
        writer.writerow(["", "", "", "", "ИТОГО", str(total_income), str(total_expenses)])
        writer.writerow(["", "", "", "", "Налоговая база", str(total_income - total_expenses), ""])

        csv_content = output.getvalue()
        logger.info(
            f"KUDiR CSV generated: {year}-Q{quarter}, income={total_income} ₽, "
            f"expenses={total_expenses} ₽"
        )
        return csv_content

    @classmethod
    def _render_kudir_html(cls, summary: dict[str, Any]) -> str:
        """Отрендерить HTML для КУДиР через Jinja2.

        Args:
            summary: Словарь из TaxAggregationService.get_quarterly_summary().

        Returns:
            HTML строка для конвертации в PDF.
        """
        generated_at = datetime.now(UTC)
        platform_name = getattr(_settings, "bot_username", "RekHarborBot")

        ctx = {
            "summary": summary,
            "platform_name": platform_name,
            "generated_at": generated_at,
        }

        if USE_JINJA2 and TEMPLATES_DIR.exists():
            env = Environment(
                loader=FileSystemLoader(str(TEMPLATES_DIR)),
                autoescape=select_autoescape(["html", "xml"]),
            )
            try:
                return env.get_template(KUDIR_TEMPLATE).render(**ctx)
            except Exception:
                logger.exception("Jinja2 KUDiR template render failed")

        # Fallback: plain HTML
        entries_html = "".join(
            f"<tr>"
            f"<td>{e['entry_number']}</td>"
            f"<td>{e['operation_date'].strftime('%d.%m.%Y') if e.get('operation_date') else ''}</td>"
            f"<td>{e['description']}</td>"
            f"<td>{e['income_amount']:.2f}</td>"
            f"</tr>"
            for e in summary.get("kudir_entries", [])
        )

        return (
            "<!DOCTYPE html><html><head>"
            "<style>table{border-collapse:collapse;width:100%}"
            "th,td{border:1px solid #ccc;padding:8px;text-align:left}"
            ".total{font-weight:bold}</style>"
            "</head><body>"
            f"<h1>Книга учёта доходов (КУДиР)</h1>"
            f"<p>Квартал: Q{summary['quarter']} {summary['year']}</p>"
            f"<table><thead><tr><th>№</th><th>Дата</th>"
            f"<th>Описание операции</th><th>Сумма дохода (₽)</th></tr></thead>"
            f"<tbody>{entries_html}"
            f'<tr class="total"><td colspan="3">ИТОГО</td>'
            f"<td>{summary['total_income']:.2f}</td></tr>"
            f"</tbody></table>"
            f"<p>Налог УСН 6%: {summary['tax_6percent']:.2f} ₽</p>"
            f"<p>Сформировано: {generated_at.strftime('%d.%m.%Y %H:%M')}</p>"
            f"</body></html>"
        )
