"""Course overview PDF template."""
from __future__ import annotations
from io import BytesIO
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor

from pdf.styles import (
    get_evlin_styles, EVLIN_NAVY, EVLIN_BLUE, EVLIN_LIGHT_BLUE,
    EVLIN_ACCENT, EVLIN_GRAY, EVLIN_DARK_GRAY,
)
from pdf.templates.textbook_base import EvlinTextbookDoc


def build_course_overview_pdf(course: dict) -> bytes:
    """Generate a course overview PDF.

    Args:
        course: Course dict with code, title, subject, description, etc.

    Returns: PDF as bytes
    """
    buffer = BytesIO()
    styles = get_evlin_styles()

    doc = EvlinTextbookDoc(
        buffer,
        title=f"{course['code']} - {course['title']}",
        subtitle=course.get("subject", ""),
    )

    story = []

    # Title
    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph(f"{course['code']}", styles["EvlinSubtitle"]))
    story.append(Paragraph(course["title"], styles["EvlinTitle"]))
    story.append(HRFlowable(width="100%", thickness=2, color=EVLIN_BLUE))
    story.append(Spacer(1, 0.2 * inch))

    # Course details table
    details = [
        ["Subject", course.get("subject", "")],
        ["Grade Level", f"{course.get('grade_level_min', '')}-{course.get('grade_level_max', '')}"],
        ["Difficulty", course.get("difficulty", "standard").title()],
        ["Duration", f"{course.get('duration_weeks', 12)} weeks"],
        ["Hours per Week", str(course.get("hours_per_week", 3.0))],
    ]

    if course.get("prerequisites"):
        details.append(["Prerequisites", ", ".join(course["prerequisites"])])
    if course.get("tags"):
        details.append(["Tags", ", ".join(course["tags"])])

    detail_table = Table(details, colWidths=[1.8 * inch, 4 * inch])
    detail_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), EVLIN_LIGHT_BLUE),
        ("TEXTCOLOR", (0, 0), (0, -1), EVLIN_NAVY),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("PADDING", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, EVLIN_LIGHT_BLUE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (1, 0), (1, -1), [HexColor("#FFFFFF"), EVLIN_GRAY]),
    ]))
    story.append(detail_table)

    # Description
    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph("Course Description", styles["EvlinH2"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=EVLIN_LIGHT_BLUE))
    story.append(Spacer(1, 0.1 * inch))
    story.append(Paragraph(
        course.get("description", "No description available."),
        styles["EvlinBody"],
    ))

    # Learning objectives (placeholder)
    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph("Learning Objectives", styles["EvlinH2"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=EVLIN_LIGHT_BLUE))
    story.append(Spacer(1, 0.1 * inch))

    objectives = [
        "Develop foundational understanding of core concepts",
        "Apply knowledge through hands-on activities and exercises",
        "Build critical thinking and problem-solving skills",
        "Prepare for the next level of study in this subject",
    ]
    for i, obj in enumerate(objectives, 1):
        story.append(Paragraph(f"{i}. {obj}", styles["EvlinBody"]))

    # Build
    doc.build(story)
    return buffer.getvalue()
