"""School Management System — PDF Report Card Generator.

Produces professional, printable report cards using ReportLab.
Design: Kenyan-style term report with school header, per-subject table,
grade summary, rank, and teacher/principal remarks.
"""

from __future__ import annotations

import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.services.results_engine import StudentReportCard


def generate_report_card_pdf(report: StudentReportCard, school_name: str = "School Management System for Schools") -> bytes:
    """Return a PDF report card as raw bytes."""

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title=f"Report Card — {report.student_name}",
        author="School Management System",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontSize=16,
        alignment=TA_CENTER,
        spaceAfter=6,
        textColor=colors.HexColor("#1e40af"),
    )
    subtitle_style = ParagraphStyle(
        "Subtitle",
        parent=styles["Normal"],
        fontSize=11,
        alignment=TA_CENTER,
        spaceAfter=12,
        textColor=colors.HexColor("#374151"),
    )
    label_style = ParagraphStyle(
        "Label",
        parent=styles["Normal"],
        fontSize=10,
        fontName="Helvetica-Bold",
    )
    value_style = ParagraphStyle(
        "Value",
        parent=styles["Normal"],
        fontSize=10,
    )
    header_style = ParagraphStyle(
        "Header",
        parent=styles["Normal"],
        fontSize=9,
        fontName="Helvetica-Bold",
        textColor=colors.white,
        alignment=TA_CENTER,
    )
    cell_style = ParagraphStyle(
        "Cell",
        parent=styles["Normal"],
        fontSize=9,
        alignment=TA_CENTER,
    )
    remarks_style = ParagraphStyle(
        "Remarks",
        parent=styles["Normal"],
        fontSize=9,
        fontName="Helvetica-Oblique",
        textColor=colors.HexColor("#4b5563"),
    )

    story = []

    # ── Header ───────────────────────────────────────────────────
    story.append(Paragraph(school_name.upper(), title_style))
    story.append(Paragraph(
        f"Term Report — {report.term_name} | Academic Year {report.academic_year}",
        subtitle_style,
    ))

    # ── Student info grid ────────────────────────────────────────
    info_data = [
        [
            Paragraph("<b>Student:</b>", label_style),
            Paragraph(report.student_name, value_style),
            Paragraph("<b>Adm No:</b>", label_style),
            Paragraph(report.admission_number, value_style),
        ],
        [
            Paragraph("<b>Class:</b>", label_style),
            Paragraph(report.class_name, value_style),
            Paragraph("<b>Stream:</b>", label_style),
            Paragraph(report.stream_name or "—", value_style),
        ],
    ]
    info_table = Table(info_data, colWidths=[3.5 * cm, 5 * cm, 3.5 * cm, 5 * cm])
    info_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 12))

    # ── Subject table ────────────────────────────────────────────
    table_data = [
        [
            Paragraph("#", header_style),
            Paragraph("Subject", header_style),
            Paragraph("Score", header_style),
            Paragraph("Max", header_style),
            Paragraph("%", header_style),
            Paragraph("Grade", header_style),
            Paragraph("Pts", header_style),
        ]
    ]

    # Color alternating rows
    row_colors: list[colors.Color | None] = [
        colors.HexColor("#1e40af"),  # header row
    ]

    for i, subj in enumerate(report.subjects):
        bg = colors.HexColor("#f9fafb") if i % 2 == 0 else None
        row_colors.append(bg)
        table_data.append([
            Paragraph(str(i + 1), cell_style),
            Paragraph(subj.subject_name, ParagraphStyle("SubjCell", parent=cell_style, alignment=TA_LEFT)),
            Paragraph(str(subj.total_score), cell_style),
            Paragraph(str(subj.max_possible), cell_style),
            Paragraph(f"{subj.percentage:.1f}", cell_style),
            Paragraph(f"<b>{subj.grade}</b>", ParagraphStyle("GradeCell", parent=cell_style, fontName="Helvetica-Bold")),
            Paragraph(str(subj.points), cell_style),
        ])

    subject_table = Table(
        table_data,
        colWidths=[1.5 * cm, 5 * cm, 2.5 * cm, 2.5 * cm, 2 * cm, 2 * cm, 1.5 * cm],
    )
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e40af")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
        ("LINEBELOW", (0, -1), (-1, -1), 1.5, colors.HexColor("#1e40af")),
    ]
    for i, bg in enumerate(row_colors):
        if bg and i > 0:
            style_cmds.append(("BACKGROUND", (0, i), (-1, i), bg))
    subject_table.setStyle(TableStyle(style_cmds))
    story.append(subject_table)
    story.append(Spacer(1, 10))

    # ── Summary row ──────────────────────────────────────────────
    summary_data = [
        [
            Paragraph("<b>Overall Mean:</b>", label_style),
            Paragraph(f"<b>{report.overall_mean:.2f}%</b>", value_style),
            Paragraph("<b>Grade:</b>", label_style),
            Paragraph(f"<b>{report.overall_grade}</b>", ParagraphStyle("BigGrade", parent=value_style, fontSize=12, fontName="Helvetica-Bold")),
            Paragraph("<b>Rank:</b>", label_style),
            Paragraph(f"<b>{report.rank_in_class} / —</b>", value_style),
        ]
    ]
    summary_table = Table(summary_data, colWidths=[4 * cm, 3 * cm, 3 * cm, 2 * cm, 3 * cm, 2 * cm])
    summary_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#1e40af")),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eff6ff")),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 16))

    # ── Remarks ─────────────────────────────────────────────────
    story.append(Paragraph(f"<b>Teacher's Remarks:</b> {report.teacher_remarks}", remarks_style))
    story.append(Spacer(1, 6))
    story.append(Paragraph(f"<b>Principal's Remarks:</b> {report.principal_remarks}", remarks_style))
    story.append(Spacer(1, 20))

    # ── Footer ──────────────────────────────────────────────────
    footer_style = ParagraphStyle(
        "Footer",
        parent=styles["Normal"],
        fontSize=8,
        textColor=colors.HexColor("#9ca3af"),
        alignment=TA_CENTER,
    )
    story.append(Paragraph(
        f"Generated by School Management System on {datetime.now().strftime('%d/%m/%Y')} | Page 1 of 1",
        footer_style,
    ))

    doc.build(story)
    pdf_bytes = buf.getvalue()
    buf.close()
    return pdf_bytes
