"""
Генерация PDF медиакита с помощью reportlab.
Спринт 9 — медиакиты для привлечения рекламодателей.
"""

import io
import logging
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Flowable,
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

logger = logging.getLogger(__name__)


def generate_mediakit_pdf(mediakit_data: dict[str, Any], logo_bytes: bytes | None = None) -> bytes:
    """
    Сгенерировать PDF медиакита.

    Args:
        mediakit_data: Данные из MediakitService.get_mediakit_data().
        logo_bytes: Опционально, логотип в bytes.

    Returns:
        PDF файл в bytes.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm,
    )

    elements: list[Flowable] = []
    styles = getSampleStyleSheet()

    # Цвет темы (из данных или дефолтный)
    theme_color = mediakit_data.get("mediakit", {}).get("theme_color", "#1a73e8")
    try:
        theme_color_obj = colors.HexColor(theme_color)
    except ValueError:
        theme_color_obj = colors.HexColor("#1a73e8")

    # 1. Заголовок с логотипом
    if logo_bytes:
        from reportlab.platypus import Image
        logo = Image(logo_bytes, width=2*cm, height=2*cm)
        elements.append(logo)
        elements.append(Spacer(1, 0.5*cm))

    # Стили
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontSize=24,
        textColor=theme_color_obj,
        spaceAfter=1*cm,
        alignment=1,  # Center
    )

    # Название канала
    channel_title = mediakit_data.get("channel", {}).get("title", "Канал")
    channel_username = mediakit_data.get("channel", {}).get("username", "")

    elements.append(Paragraph(f"📡 {channel_title}", title_style))

    if channel_username:
        username_style = ParagraphStyle(
            "Username",
            parent=styles["Normal"],
            fontSize=14,
            textColor=colors.grey,
            spaceAfter=0.5*cm,
            alignment=1,
        )
        elements.append(Paragraph(f"@{channel_username}", username_style))
        elements.append(Spacer(1, 0.5*cm))

    # 2. Описание
    description = mediakit_data.get("mediakit", {}).get("custom_description")
    if not description:
        description = mediakit_data.get("channel", {}).get("description", "")

    if description:
        desc_style = ParagraphStyle(
            "Description",
            parent=styles["Normal"],
            fontSize=12,
            textColor=colors.HexColor("#333333"),
            spaceAfter=1*cm,
        )
        elements.append(Paragraph(description, desc_style))
        elements.append(Spacer(1, 0.5*cm))

    # 3. Ключевые метрики (таблица)
    metrics = mediakit_data.get("metrics", {})
    price = mediakit_data.get("price", {})

    show_metrics = mediakit_data.get("mediakit", {}).get("show_metrics", {})

    table_data = [["📊 Метрика", "📈 Значение"]]

    if show_metrics.get("subscribers", True):
        table_data.append([
            "Подписчики",
            f"{metrics.get('subscribers', 0):,}"
        ])

    if show_metrics.get("avg_views", True):
        table_data.append([
            "Ср. просмотры",
            f"{metrics.get('avg_views', 0):,}"
        ])

    if show_metrics.get("er", True):
        table_data.append([
            "ER (Engagement Rate)",
            f"{metrics.get('er', 0.0):.1f}%"
        ])

    if show_metrics.get("post_frequency", True):
        table_data.append([
            "Постов в день",
            f"{metrics.get('post_frequency', 0.0):.1f}"
        ])

    if show_metrics.get("price", True):
        table_data.append([
            "Цена за пост",
            f"{price.get('amount', 0)} {price.get('currency', 'кр')}"
        ])

    # Стиль таблицы
    table = Table(table_data, colWidths=[7*cm, 7*cm])
    table.setStyle(TableStyle([
        # Заголовок
        ("BACKGROUND", (0, 0), (-1, 0), theme_color_obj),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 14),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
        # Чётные строки
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8f9fa")),
        ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor("#333333")),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 12),
        ("TOPPADDING", (0, 1), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 8),
        # Границы
        ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#dee2e6")),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 1*cm))

    # 4. Отзывы (если есть)
    reviews = mediakit_data.get("reviews", {})
    if reviews.get("count", 0) > 0:
        reviews_style = ParagraphStyle(
            "Reviews",
            parent=styles["Heading2"],
            fontSize=16,
            textColor=theme_color_obj,
            spaceAfter=0.5*cm,
        )
        elements.append(Paragraph("⭐ Отзывы", reviews_style))

        review_text_style = ParagraphStyle(
            "ReviewText",
            parent=styles["Normal"],
            fontSize=12,
            textColor=colors.HexColor("#333333"),
            spaceAfter=0.5*cm,
        )

        elements.append(Paragraph(
            f"Средний рейтинг: <b>{reviews.get('average_rating', 0):.1f}/5</b> "
            f"({reviews.get('count', 0)} отзывов)",
            review_text_style
        ))
        elements.append(Spacer(1, 0.5*cm))

    # 5. Тематики (если есть)
    topic = mediakit_data.get("channel", {}).get("topic")
    if topic and show_metrics.get("topics", True):
        topics_style = ParagraphStyle(
            "Topics",
            parent=styles["Heading2"],
            fontSize=16,
            textColor=theme_color_obj,
            spaceAfter=0.5*cm,
        )
        elements.append(Paragraph("🏷 Тематика", topics_style))

        elements.append(Paragraph(f"{topic}", review_text_style))
        elements.append(Spacer(1, 0.5*cm))

    # 6. Подвал с контактами
    elements.append(Spacer(1, 2*cm))

    footer_style = ParagraphStyle(
        "Footer",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#6c757d"),
        alignment=1,
    )

    contact_text = f"📧 Связь: @{channel_username}" if channel_username else "📧 Связь через платформу"
    elements.append(Paragraph(contact_text, footer_style))

    from datetime import datetime
    elements.append(Paragraph(
        f"Медиакит сгенерирован: {datetime.now().strftime('%d.%m.%Y')}",
        footer_style
    ))

    # Build PDF
    doc.build(elements)

    pdf_bytes = buffer.getvalue()
    buffer.close()

    logger.info(f"Generated PDF mediakit for channel {mediakit_data.get('channel', {}).get('id')}")
    return pdf_bytes
