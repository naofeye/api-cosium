"""Common PDF helpers: styles, formatting, table utilities."""

import io
from datetime import UTC, datetime

from reportlab.lib import colors as rl_colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.core.logging import get_logger

logger = get_logger("export_pdf")


# ---------------------------------------------------------------------------
# Reusable table styles
# ---------------------------------------------------------------------------

def section_table_style() -> TableStyle:
    """Reusable table style for data sections."""
    return TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), rl_colors.HexColor("#2563EB")),
        ("TEXTCOLOR", (0, 0), (-1, 0), rl_colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("GRID", (0, 0), (-1, -1), 0.5, rl_colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [rl_colors.white, rl_colors.HexColor("#F9FAFB")]),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ])


def kpi_table_style() -> TableStyle:
    """Reusable table style for KPI sections."""
    return TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), rl_colors.HexColor("#2563EB")),
        ("TEXTCOLOR", (0, 0), (-1, 0), rl_colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, rl_colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [
            rl_colors.white, rl_colors.HexColor("#F9FAFB"),
        ]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ])


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def fmt_money(val: float) -> str:
    """Format a float as EUR money string."""
    return f"{val:,.2f} EUR".replace(",", " ").replace(".", ",").replace(" ", " ")


def fmt_diopter(val: float | None) -> str:
    """Format a diopter value with sign."""
    if val is None:
        return "-"
    sign = "+" if val >= 0 else ""
    return f"{sign}{val:.2f}"


# ---------------------------------------------------------------------------
# Document scaffolding helpers
# ---------------------------------------------------------------------------

def create_pdf_doc(output: io.BytesIO, **kwargs) -> SimpleDocTemplate:
    """Create a standard A4 PDF document with OptiFlow margins."""
    defaults = {
        "pagesize": A4,
        "topMargin": 20 * mm,
        "bottomMargin": 15 * mm,
        "leftMargin": 15 * mm,
        "rightMargin": 15 * mm,
    }
    defaults.update(kwargs)
    return SimpleDocTemplate(output, **defaults)


def make_title_style(name: str, font_size: int = 18) -> ParagraphStyle:
    """Create a centered title paragraph style."""
    styles = getSampleStyleSheet()
    return ParagraphStyle(
        name, parent=styles["Heading1"],
        fontSize=font_size, alignment=1, spaceAfter=6,
    )


def make_date_style(name: str) -> ParagraphStyle:
    """Create a centered date/subtitle paragraph style."""
    styles = getSampleStyleSheet()
    return ParagraphStyle(
        name, parent=styles["Normal"],
        fontSize=10, alignment=1, spaceAfter=20, textColor=rl_colors.grey,
    )


def make_section_style(name: str) -> ParagraphStyle:
    """Create a section heading paragraph style."""
    styles = getSampleStyleSheet()
    return ParagraphStyle(
        name, parent=styles["Heading2"],
        fontSize=13, spaceAfter=8, spaceBefore=14,
        textColor=rl_colors.HexColor("#1E40AF"),
    )


def make_footer_style(name: str) -> ParagraphStyle:
    """Create a footer paragraph style."""
    styles = getSampleStyleSheet()
    return ParagraphStyle(
        name, parent=styles["Italic"],
        fontSize=8, textColor=rl_colors.grey, alignment=1,
    )


def append_footer(elements: list, style_name: str = "Footer") -> None:
    """Append the standard OptiFlow footer to elements."""
    elements.append(Spacer(1, 10 * mm))
    elements.append(Paragraph(
        "Document genere automatiquement par OptiFlow AI. Confidentiel.",
        make_footer_style(style_name),
    ))


def generated_timestamp() -> str:
    """Return current UTC timestamp formatted for PDF headers."""
    return datetime.now(UTC).strftime("%d/%m/%Y %H:%M")
