"""
Генерация PDF-отчётов для кампаний с помощью reportlab.
"""

import io
import logging
from datetime import datetime
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Flowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

logger = logging.getLogger(__name__)


def generate_campaign_report(
    campaign_id: int,
    campaign_title: str,
    stats: dict[str, Any],
    created_at: datetime | None = None,
) -> bytes:
    """
    Сгенерировать PDF-отчёт по кампании.

    Args:
        campaign_id: ID кампании.
        campaign_title: Название кампании.
        stats: Статистика кампании.
        created_at: Дата создания кампании.

    Returns:
        PDF файл в виде bytes.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    elements: list[Flowable] = []
    styles = getSampleStyleSheet()

    # Заголовок
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontSize=24,
        textColor=colors.HexColor("#1a1a2e"),
        spaceAfter=1 * cm,
        alignment=1,  # Center
    )

    elements.append(Paragraph("Отчёт по кампании", title_style))
    elements.append(Spacer(1, 0.5 * cm))

    # Информация о кампании
    info_style = ParagraphStyle(
        "Info",
        parent=styles["Normal"],
        fontSize=12,
        textColor=colors.HexColor("#333333"),
        spaceAfter=0.5 * cm,
    )

    elements.append(Paragraph(f"<b>ID кампании:</b> {campaign_id}", info_style))
    elements.append(Paragraph(f"<b>Название:</b> {campaign_title}", info_style))
    if created_at:
        elements.append(
            Paragraph(
                f"<b>Дата создания:</b> {created_at.strftime('%d.%m.%Y %H:%M')}",
                info_style,
            )
        )
    elements.append(Spacer(1, 0.5 * cm))

    # Таблица статистики
    data = [
        ["Метрика", "Значение"],
        ["Всего отправлено", str(stats.get("total_sent", 0))],
        ["Успешно", str(stats.get("total_sent", 0))],
        ["Не удалось", str(stats.get("total_failed", 0))],
        ["Пропущено", str(stats.get("total_skipped", 0))],
        ["Success Rate", f"{stats.get('success_rate', 0):.1f}%"],
        ["Стоимость", f"{stats.get('total_cost', 0)} RUB"],
        ["Охват (оценка)", str(stats.get("reach_estimate", 0))],
    ]

    table = Table(data, colWidths=[6 * cm, 6 * cm])
    table.setStyle(
        TableStyle(
            [
                # Заголовок
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 14),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                # Чётные строки
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8f9fa")),
                ("BACKGROUND", (0, 2), (-1, -1), colors.white),
                ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor("#333333")),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -1), 12),
                ("TOPPADDING", (0, 1), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 8),
                # Границы
                ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#dee2e6")),
            ]
        )
    )

    elements.append(table)
    elements.append(Spacer(1, 1 * cm))

    # Диаграмма (pie chart) - упрощённая версия
    try:
        from reportlab.graphics.charts.piecharts import Pie
        from reportlab.graphics.shapes import Drawing

        drawing = Drawing(width=12 * cm, height=6 * cm)
        pie = Pie()
        pie.x = 0
        pie.y = 0
        pie.width = 12 * cm
        pie.height = 6 * cm
        sent_val = int(float(stats.get("total_sent", 0) or 0))  # type: ignore[arg-type]
        failed_val = int(float(stats.get("total_failed", 0) or 0))  # type: ignore[arg-type]
        skipped_val = int(float(stats.get("total_skipped", 0) or 0))  # type: ignore[arg-type]
        pie.data = [sent_val, failed_val, skipped_val]  # type: ignore[assignment]
        pie.labels = ["Успешно", "Не удалось", "Пропущено"]
        pie.slices.strokeWidth = 0.5
        pie.slices[0].fillColor = colors.HexColor("#28a745")
        pie.slices[1].fillColor = colors.HexColor("#dc3545")
        pie.slices[2].fillColor = colors.HexColor("#ffc107")

        drawing.add(pie)
        elements.append(drawing)
        elements.append(Spacer(1, 1 * cm))
    except Exception as e:
        logger.warning(f"Could not add pie chart: {e}")

    # Подвал
    footer_style = ParagraphStyle(
        "Footer",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#6c757d"),
        alignment=1,
    )

    elements.append(Spacer(1, 2 * cm))
    elements.append(
        Paragraph(
            f"Отчёт сгенерирован: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            footer_style,
        )
    )
    elements.append(Paragraph("Market Telegram Bot", footer_style))

    # Build PDF
    doc.build(elements)

    # Get bytes
    pdf_bytes = buffer.getvalue()
    buffer.close()

    logger.info(f"Generated PDF report for campaign {campaign_id}")
    return pdf_bytes


def generate_user_summary_report(
    user_id: int,
    username: str,
    analytics: dict[str, Any],
    period_days: int = 30,
) -> bytes:
    """
    Сгенерировать PDF-отчёт для пользователя.

    Args:
        user_id: ID пользователя.
        username: Username пользователя.
        analytics: Аналитика пользователя.
        period_days: Период отчёта в днях.

    Returns:
        PDF файл в виде bytes.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    elements: list[Flowable] = []
    styles = getSampleStyleSheet()

    # Заголовок
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontSize=24,
        textColor=colors.HexColor("#1a1a2e"),
        spaceAfter=1 * cm,
        alignment=1,
    )

    elements.append(Paragraph("Отчёт пользователя", title_style))
    elements.append(Spacer(1, 0.5 * cm))

    # Информация о пользователе
    info_style = ParagraphStyle(
        "Info",
        parent=styles["Normal"],
        fontSize=12,
        textColor=colors.HexColor("#333333"),
        spaceAfter=0.5 * cm,
    )

    elements.append(Paragraph(f"<b>User ID:</b> {user_id}", info_style))
    elements.append(Paragraph(f"<b>Username:</b> @{username or 'N/A'}", info_style))
    elements.append(Paragraph(f"<b>Период:</b> последние {period_days} дн.", info_style))
    elements.append(Spacer(1, 0.5 * cm))

    # Таблица статистики
    data = [
        ["Метрика", "Значение"],
        ["Всего кампаний", str(analytics.get("total_campaigns", 0))],
        ["Активные кампании", str(analytics.get("active_campaigns", 0))],
        ["Завершённые кампании", str(analytics.get("completed_campaigns", 0))],
        ["Всего потрачено", f"{analytics.get('total_spent', 0)} RUB"],
        ["Средний Success Rate", f"{analytics.get('avg_success_rate', 0):.1f}%"],
        ["Всего чатов достигнуто", str(analytics.get("total_chats_reached", 0))],
    ]

    table = Table(data, colWidths=[6 * cm, 6 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 14),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8f9fa")),
                ("BACKGROUND", (0, 2), (-1, -1), colors.white),
                ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor("#333333")),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -1), 12),
                ("TOPPADDING", (0, 1), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#dee2e6")),
            ]
        )
    )

    elements.append(table)

    # Подвал
    footer_style = ParagraphStyle(
        "Footer",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#6c757d"),
        alignment=1,
    )

    elements.append(Spacer(1, 2 * cm))
    elements.append(
        Paragraph(
            f"Отчёт сгенерирован: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            footer_style,
        )
    )
    elements.append(Paragraph("Market Telegram Bot", footer_style))

    # Build PDF
    doc.build(elements)

    pdf_bytes = buffer.getvalue()
    buffer.close()

    logger.info(f"Generated PDF report for user {user_id}")
    return pdf_bytes
