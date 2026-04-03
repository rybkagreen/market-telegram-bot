"""InvoiceService — генерация счетов на оплату (B2B).

Использует DocumentNumberService для сквозной нумерации (prefix='СЧ'),
Jinja2 для рендеринга HTML и WeasyPrint для генерации PDF.
"""

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings as _settings
from src.core.services.document_number_service import DocumentNumberService
from src.db.models.invoice import Invoice
from src.db.repositories.legal_profile_repo import LegalProfileRepo

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
INVOICE_TEMPLATE = "invoices/invoice_b2b.html"

# Директория для хранения PDF счетов
INVOICES_OUTPUT_DIR = Path(_settings.contracts_storage_path) / "invoices"
INVOICES_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class InvoiceService:
    """Сервис для генерации счетов на оплату (B2B)."""

    @classmethod
    async def generate_for_topup(
        cls,
        session: AsyncSession,
        user_id: int,
        amount_rub: float | str,
    ) -> Invoice:
        """Сгенерировать счёт на пополнение баланса.

        Args:
            session: Асинхронная сессия.
            user_id: ID пользователя.
            amount_rub: Сумма в рублях.

        Returns:
            Созданный объект Invoice.
        """
        from decimal import Decimal

        amount = Decimal(str(amount_rub))

        # Получить юр. статус пользователя
        legal_repo = LegalProfileRepo(session)
        profile = await legal_repo.get_by_user_id(user_id)
        legal_status = profile.legal_status if profile else "individual"

        # Рассчитать НДС 22% (только для legal_entity)
        vat_amount = Decimal("0")
        if legal_status == "legal_entity":
            vat_amount = (amount * Decimal("0.22")).quantize(Decimal("0.01"))

        # Сгенерировать номер счёта
        invoice_number = await DocumentNumberService.generate_next(session, "СЧ")

        # Рендерить HTML и сохранить PDF
        html = cls._render_invoice_html(invoice_number, user_id, amount, vat_amount, profile)
        pdf_path = cls._html_to_pdf(html, invoice_number)
        if pdf_path is None:
            raise RuntimeError(f"PDF generation failed for invoice {invoice_number}")

        # Создать запись в БД
        invoice = Invoice(
            user_id=user_id,
            invoice_number=invoice_number,
            amount_rub=amount,
            vat_amount=vat_amount,
            status="draft",
            pdf_path=str(pdf_path),
        )
        session.add(invoice)
        await session.flush()
        await session.refresh(invoice)

        logger.info(
            f"Invoice generated: {invoice_number} for user {user_id}, "
            f"amount={amount} ₽, vat={vat_amount} ₽"
        )
        return invoice

    @classmethod
    async def sign_invoice_with_edo(
        cls,
        invoice: Invoice,
        edo_provider: Any = None,
    ) -> dict | None:
        """Опционально подписать счёт через ЭДО-провайдер.

        Вызывается после установки статуса 'paid'. Если edo_provider
        не передан — возвращается None (ЭДО не настроен).

        Args:
            invoice: Объект счёта.
            edo_provider: Экземпляр EdoProvider (опционально).

        Returns:
            dict со статусом ЭДО или None.
        """
        if edo_provider is None:
            logger.debug("EDO provider not configured for invoice %s", invoice.invoice_number)
            return None

        try:
            pdf_path = Path(invoice.pdf_path)
            if not pdf_path.exists():
                logger.warning("Invoice PDF not found: %s", pdf_path)
                return None

            doc_id = await edo_provider.sign_document(pdf_path)
            await edo_provider.get_status(doc_id)
            result = await edo_provider.send_signed(doc_id, doc_id)

            logger.info(
                "EDO signing completed for invoice %s: status=%s",
                invoice.invoice_number,
                result.get("status"),
            )
            return result
        except Exception as e:
            logger.warning(
                "EDO signing failed for invoice %s: %s",
                invoice.invoice_number,
                e,
            )
            return None

    @classmethod
    def _render_invoice_html(
        cls,
        invoice_number: str,
        user_id: int,
        amount: Any,
        vat_amount: Any,
        profile: object | None = None,
    ) -> str:
        """Отрендерить HTML счёт через Jinja2.

        Args:
            invoice_number: Номер счёта.
            user_id: ID пользователя.
            amount: Сумма в рублях.
            vat_amount: Сумма НДС.
            profile: Юридический профиль пользователя (опционально).

        Returns:
            HTML строка для конвертации в PDF.
        """

        generated_at = datetime.now(UTC)
        platform_name = getattr(_settings, "bot_username", "RekHarborBot")

        ctx: dict[str, Any] = {
            "invoice_number": invoice_number,
            "generated_at": generated_at,
            "platform_name": platform_name,
            "amount": amount,
            "vat_amount": vat_amount,
            "total_with_vat": amount + vat_amount if vat_amount > 0 else amount,
            # Client info
            "client_name": getattr(profile, "legal_name", "") or f"User #{user_id}",
            "client_inn": getattr(profile, "inn", "") or "",
            "client_legal_status": getattr(profile, "legal_status", "") or "individual",
        }

        if USE_JINJA2 and TEMPLATES_DIR.exists():
            env = Environment(
                loader=FileSystemLoader(str(TEMPLATES_DIR)),
                autoescape=select_autoescape(["html", "xml"]),
            )
            try:
                return env.get_template(INVOICE_TEMPLATE).render(**ctx)
            except Exception:
                logger.exception(f"Jinja2 invoice template render failed for {invoice_number}")

        # Fallback: plain HTML
        vat_row = ""
        if vat_amount > 0:
            vat_row = f"<tr><td>НДС (22%)</td><td>{vat_amount:.2f} ₽</td></tr>"

        return (
            "<!DOCTYPE html><html><head>"
            "<style>body{font-family:Arial,sans-serif;margin:40px}"
            "table{border-collapse:collapse;width:100%}"
            "th,td{border:1px solid #ccc;padding:8px;text-align:left}"
            ".total{font-weight:bold}</style>"
            "</head><body>"
            f"<h1>Счёт на оплату №{invoice_number}</h1>"
            f"<p>Дата: {generated_at.strftime('%d.%m.%Y')}</p>"
            f"<p>Поставщик: {platform_name}</p>"
            f"<p>Покупатель: {ctx['client_name']}</p>"
            f"<table><tr><th>Наименование</th><th>Сумма</th></tr>"
            f"<tr><td>Пополнение баланса</td><td>{amount:.2f} ₽</td></tr>"
            f"{vat_row}"
            f'<tr class="total"><td>Итого</td><td>{ctx["total_with_vat"]:.2f} ₽</td></tr>'
            f"</table>"
            f"</body></html>"
        )

    @classmethod
    def _html_to_pdf(cls, html_content: str, invoice_number: str) -> Path | None:
        """Конвертировать HTML в PDF (если WeasyPrint доступен).

        Args:
            html_content: HTML содержимое счёта.
            invoice_number: Номер счёта для имени файла.

        Returns:
            Путь к PDF файлу или None при ошибке.
        """
        output_path = INVOICES_OUTPUT_DIR / f"{invoice_number}.pdf"

        if USE_WEASYPRINT:
            try:
                weasyprint.HTML(string=html_content).write_pdf(str(output_path))  # type: ignore[name-defined]
                return output_path
            except Exception as e:
                logger.warning(f"Invoice PDF generation failed: {e}")
                return None
        else:
            # Save HTML as fallback
            html_path = INVOICES_OUTPUT_DIR / f"{invoice_number}.html"
            html_path.write_text(html_content, encoding="utf-8")
            return None
