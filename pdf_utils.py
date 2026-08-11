"""Create a polished PDF download for one LexAssist response."""

from __future__ import annotations

from functools import lru_cache
from html import escape
from io import BytesIO

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


@lru_cache(maxsize=128)
def create_answer_pdf(answer: str) -> bytes:
    """Return a PDF containing a single LexAssist answer."""
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=0.7 * inch,
        leftMargin=0.7 * inch,
        topMargin=0.7 * inch,
        bottomMargin=0.7 * inch,
        title="LexAssist answer",
    )
    styles = getSampleStyleSheet()
    heading = ParagraphStyle(
        "LexAssistHeading",
        parent=styles["Heading1"],
        textColor=HexColor("#0B4F6C"),
        spaceAfter=14,
    )
    body = ParagraphStyle(
        "LexAssistBody",
        parent=styles["BodyText"],
        fontSize=10.5,
        leading=15,
        textColor=HexColor("#18212A"),
    )
    escaped_answer = escape(answer).replace("\n", "<br/>")
    document.build(
        [
            Paragraph("LexAssist", heading),
            Paragraph("Legal information response", styles["Italic"]),
            Spacer(1, 14),
            Paragraph(escaped_answer, body),
        ]
    )
    return buffer.getvalue()


def create_chat_report_pdf(messages: list[dict[str, str | int]]) -> bytes:
    """Return a PDF report containing the complete saved conversation."""
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=0.7 * inch,
        leftMargin=0.7 * inch,
        topMargin=0.7 * inch,
        bottomMargin=0.7 * inch,
        title="LexAssist chat report",
    )
    styles = getSampleStyleSheet()
    heading = ParagraphStyle(
        "LexAssistReportHeading",
        parent=styles["Heading1"],
        textColor=HexColor("#0B4F6C"),
        spaceAfter=8,
    )
    message_label = ParagraphStyle(
        "MessageLabel",
        parent=styles["Heading3"],
        spaceBefore=12,
        spaceAfter=4,
    )
    body = ParagraphStyle(
        "ReportBody",
        parent=styles["BodyText"],
        fontSize=10.5,
        leading=15,
        textColor=HexColor("#18212A"),
    )
    story = [
        Paragraph("LexAssist", heading),
        Paragraph("Conversation report", styles["Italic"]),
        Spacer(1, 14),
    ]
    for message in messages:
        role = "You" if message["role"] == "user" else "LexAssist"
        content = escape(str(message["content"])).replace("\n", "<br/>")
        story.extend([Paragraph(role, message_label), Paragraph(content, body)])
    document.build(story)
    return buffer.getvalue()
