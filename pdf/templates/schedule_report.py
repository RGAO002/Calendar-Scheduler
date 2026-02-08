"""Schedule report PDF template."""
from __future__ import annotations
from io import BytesIO
from datetime import date
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor

from pdf.styles import (
    get_evlin_styles, EVLIN_NAVY, EVLIN_BLUE, EVLIN_LIGHT_BLUE,
    EVLIN_GRAY, EVLIN_DARK_GRAY, EVLIN_GREEN, EVLIN_ACCENT,
)
from pdf.templates.textbook_base import EvlinTextbookDoc

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

SUBJECT_COLORS = {
    "Math": HexColor("#4A90D9"),
    "Science": HexColor("#27AE60"),
    "English": HexColor("#E67E22"),
    "History": HexColor("#8E44AD"),
    "Art": HexColor("#E74C3C"),
    "PE": HexColor("#16A085"),
}


def build_schedule_report_pdf(student: dict, schedules: list[dict], slots: list[dict]) -> bytes:
    """Generate a student schedule report PDF.

    Args:
        student: Student dict
        schedules: Active schedules with course info
        slots: All schedule slots with course info

    Returns: PDF as bytes
    """
    buffer = BytesIO()
    styles = get_evlin_styles()

    student_name = f"{student['first_name']} {student['last_name']}"

    doc = EvlinTextbookDoc(
        buffer,
        title=f"Schedule Report - {student_name}",
        subtitle=f"Grade {student['grade_level']} | {date.today().strftime('%B %Y')}",
    )

    story = []

    # Title section
    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph("Student Schedule Report", styles["EvlinTitle"]))
    story.append(Paragraph(
        f"{student_name} — Grade {student['grade_level']}",
        styles["EvlinSubtitle"],
    ))
    story.append(HRFlowable(width="100%", thickness=2, color=EVLIN_BLUE))

    # Student info
    story.append(Spacer(1, 0.2 * inch))
    info_items = [
        ["Student", student_name],
        ["Grade", str(student["grade_level"])],
        ["Report Date", date.today().strftime("%B %d, %Y")],
    ]
    if student.get("parent_name"):
        info_items.append(["Parent/Guardian", student["parent_name"]])

    info_table = Table(info_items, colWidths=[1.5 * inch, 4 * inch])
    info_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), EVLIN_LIGHT_BLUE),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("PADDING", (0, 0), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -1), 0.5, EVLIN_LIGHT_BLUE),
    ]))
    story.append(info_table)

    # Course summary
    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph("Enrolled Courses", styles["EvlinH2"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=EVLIN_LIGHT_BLUE))
    story.append(Spacer(1, 0.1 * inch))

    if schedules:
        course_data = [["Code", "Course Title", "Subject", "Hrs/Wk", "Status"]]
        for sch in schedules:
            course = sch.get("courses", {})
            course_data.append([
                course.get("code", ""),
                course.get("title", ""),
                course.get("subject", ""),
                str(course.get("hours_per_week", "")),
                sch.get("status", "").title(),
            ])

        course_table = Table(
            course_data,
            colWidths=[1 * inch, 2.5 * inch, 1 * inch, 0.8 * inch, 0.8 * inch],
        )
        course_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), EVLIN_NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#FFFFFF")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("PADDING", (0, 0), (-1, -1), 6),
            ("GRID", (0, 0), (-1, -1), 0.5, EVLIN_LIGHT_BLUE),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#FFFFFF"), EVLIN_GRAY]),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(course_table)

        total_hours = sum(
            s.get("courses", {}).get("hours_per_week", 0) for s in schedules
        )
        story.append(Spacer(1, 0.1 * inch))
        story.append(Paragraph(
            f"<b>Total Weekly Hours: {total_hours:.1f}</b>",
            styles["EvlinBody"],
        ))
    else:
        story.append(Paragraph("No active courses enrolled.", styles["EvlinBody"]))

    # Weekly schedule grid
    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph("Weekly Schedule", styles["EvlinH2"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=EVLIN_LIGHT_BLUE))
    story.append(Spacer(1, 0.1 * inch))

    if slots:
        # Organize slots by day
        slots_by_day = {}
        for s in slots:
            d = s.get("day_of_week", 0)
            if d not in slots_by_day:
                slots_by_day[d] = []
            slots_by_day[d].append(s)

        sched_data = [["Day", "Time", "Course", "Location"]]
        for day_idx in sorted(slots_by_day.keys()):
            day_slots = sorted(slots_by_day[day_idx], key=lambda x: str(x.get("start_time", "")))
            for s in day_slots:
                sched_data.append([
                    DAY_NAMES[day_idx],
                    f"{str(s.get('start_time', ''))[:5]} - {str(s.get('end_time', ''))[:5]}",
                    f"{s.get('course_code', '')} {s.get('course_title', '')}",
                    s.get("location", "Home"),
                ])

        sched_table = Table(
            sched_data,
            colWidths=[1.2 * inch, 1.2 * inch, 2.8 * inch, 1 * inch],
        )
        sched_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), EVLIN_NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#FFFFFF")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("PADDING", (0, 0), (-1, -1), 6),
            ("GRID", (0, 0), (-1, -1), 0.5, EVLIN_LIGHT_BLUE),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#FFFFFF"), EVLIN_GRAY]),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(sched_table)
    else:
        story.append(Paragraph("No scheduled time slots.", styles["EvlinBody"]))

    doc.build(story)
    return buffer.getvalue()
