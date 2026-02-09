"""3-Month semester calendar PDF template.

Generates a wall-calendar style PDF with one month per page.
Each day cell shows the courses scheduled on that day with times.
"""
from __future__ import annotations
import calendar
from io import BytesIO
from datetime import date, timedelta
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, HRFlowable, PageBreak
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, Color
from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame

from pdf.styles import (
    get_evlin_styles, EVLIN_NAVY, EVLIN_BLUE, EVLIN_LIGHT_BLUE,
    EVLIN_GRAY, EVLIN_DARK_GRAY, EVLIN_ACCENT, EVLIN_TEXT,
    HEADING_FONT, BODY_FONT, ITALIC_FONT, PAGE_MARGIN,
)

PAGE_WIDTH, PAGE_HEIGHT = landscape(letter)

DAY_HEADERS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

SUBJECT_COLORS = {
    "Math":    ("#4A90D9", "#EAF1FA"),
    "Science": ("#27AE60", "#E8F8EF"),
    "English": ("#E67E22", "#FDF2E9"),
    "History": ("#8E44AD", "#F4ECF7"),
    "Art":     ("#E74C3C", "#FDEDEC"),
    "PE":      ("#16A085", "#E8F6F3"),
}


class _CalendarDoc(BaseDocTemplate):
    """Landscape document for calendar pages."""

    def __init__(self, filename, title="", subtitle="", **kwargs):
        self.doc_title = title
        self.doc_subtitle = subtitle
        margin = 0.5 * inch

        super().__init__(
            filename,
            pagesize=landscape(letter),
            leftMargin=margin,
            rightMargin=margin,
            topMargin=margin + 0.4 * inch,
            bottomMargin=margin + 0.25 * inch,
            **kwargs,
        )

        content_width = PAGE_WIDTH - 2 * margin
        content_height = PAGE_HEIGHT - 2 * margin - 0.4 * inch - 0.25 * inch

        frame = Frame(margin, margin + 0.25 * inch, content_width, content_height, id="cal")
        template = PageTemplate(id="calendar", frames=[frame], onPage=self._draw_page)
        self.addPageTemplates([template])

    def _draw_page(self, canvas, doc):
        canvas.saveState()
        margin = 0.5 * inch

        # Header bar
        header_y = PAGE_HEIGHT - margin
        canvas.setFillColor(EVLIN_NAVY)
        canvas.rect(margin, header_y - 2, PAGE_WIDTH - 2 * margin, 22, fill=1, stroke=0)
        canvas.setFillColor(HexColor("#FFFFFF"))
        canvas.setFont(HEADING_FONT, 9)
        canvas.drawString(margin + 6, header_y + 2, "EVLIN EDUCATION")
        canvas.setFont(BODY_FONT, 8)
        canvas.drawRightString(PAGE_WIDTH - margin - 6, header_y + 2, self.doc_title[:80])

        # Accent line
        canvas.setStrokeColor(EVLIN_BLUE)
        canvas.setLineWidth(1.5)
        canvas.line(margin, header_y - 4, PAGE_WIDTH - margin, header_y - 4)

        # Footer
        footer_y = margin - 0.08 * inch
        canvas.setStrokeColor(EVLIN_LIGHT_BLUE)
        canvas.setLineWidth(0.5)
        canvas.line(margin, footer_y + 10, PAGE_WIDTH - margin, footer_y + 10)
        canvas.setFillColor(EVLIN_DARK_GRAY)
        canvas.setFont(BODY_FONT, 7)
        canvas.drawString(margin, footer_y, "Evlin Homeschool Education Platform")
        canvas.drawRightString(PAGE_WIDTH - margin, footer_y, f"Page {canvas.getPageNumber()}")
        if self.doc_subtitle:
            canvas.drawCentredString(PAGE_WIDTH / 2, footer_y, self.doc_subtitle)

        canvas.restoreState()


def _build_month_page(
    year: int,
    month: int,
    slots: list[dict],
    schedules: list[dict],
    styles,
    start_date: date = None,
    end_date: date = None,
) -> list:
    """Build flowables for one month calendar page.

    Args:
        year, month: Which month to render
        slots: All weekly schedule slots with course info
        schedules: Schedule records with course metadata
        styles: ReportLab paragraph styles
        start_date: Optional semester start (greys out days before)
        end_date: Optional semester end (greys out days after)

    Returns: list of flowables
    """
    month_name = calendar.month_name[month]
    story = []

    # Month title
    story.append(Paragraph(
        f'<font size="20" color="#{EVLIN_NAVY.hexval()[2:]}">{month_name} {year}</font>',
        styles["EvlinTitle"],
    ))
    story.append(Spacer(1, 0.1 * inch))

    # Build lookup: day_of_week -> list of course entries
    # day_of_week: 0=Monday (matching Python calendar and our DB)
    slot_by_dow = {}
    for s in slots:
        dow = s.get("day_of_week", 0)
        if dow not in slot_by_dow:
            slot_by_dow[dow] = []
        slot_by_dow[dow].append(s)

    # Build course subject lookup
    course_subjects = {}
    for sch in schedules:
        c = sch.get("courses", {})
        code = c.get("code", "")
        course_subjects[code] = c.get("subject", "")

    # Get calendar matrix (weeks as rows, 0=Monday)
    cal = calendar.Calendar(firstweekday=0)
    month_weeks = cal.monthdayscalendar(year, month)

    # Ensure exactly 6 rows for consistent layout
    while len(month_weeks) < 6:
        month_weeks.append([0] * 7)

    # Column widths for 7-day grid: landscape letter is 11" wide, ~0.5" margin each side = 10" usable
    col_w = (PAGE_WIDTH - 1.0 * inch) / 7.0

    # Build header row
    header_row = []
    for dh in DAY_HEADERS:
        header_row.append(Paragraph(
            f'<font name="{HEADING_FONT}" size="9" color="#FFFFFF">{dh}</font>',
            styles["Normal"],
        ))

    # Build data rows
    data_rows = [header_row]
    cell_styles = []  # extra style commands

    for week_idx, week in enumerate(month_weeks):
        row = []
        for day_idx, day_num in enumerate(week):
            if day_num == 0:
                # Empty cell (not in this month)
                row.append("")
                continue

            this_date = date(year, month, day_num)
            is_outside = False
            if start_date and this_date < start_date:
                is_outside = True
            if end_date and this_date > end_date:
                is_outside = True

            # Day number
            day_color = EVLIN_DARK_GRAY.hexval()[2:] if is_outside else EVLIN_NAVY.hexval()[2:]
            cell_content = f'<font name="{HEADING_FONT}" size="9" color="#{day_color}">{day_num}</font>'

            # Check if it's today
            if this_date == date.today():
                cell_content = (
                    f'<font name="{HEADING_FONT}" size="9" color="#{EVLIN_ACCENT.hexval()[2:]}">'
                    f'<u>{day_num}</u></font>'
                )

            # Add courses for this day of week (only within semester range)
            if not is_outside and day_idx in slot_by_dow:
                for s in slot_by_dow[day_idx]:
                    code = s.get("course_code", "")
                    subj = course_subjects.get(code, s.get("subject", ""))
                    fg, bg = SUBJECT_COLORS.get(subj, ("#333333", "#F0F0F0"))
                    time_str = f"{str(s.get('start_time', ''))[:5]}"
                    cell_content += (
                        f'<br/><font name="{BODY_FONT}" size="6" color="{fg}">'
                        f'{code} {time_str}</font>'
                    )

            # Weekend shading (Sat=5, Sun=6)
            row_in_table = week_idx + 1  # +1 for header row
            if day_idx >= 5:
                cell_styles.append(
                    ("BACKGROUND", (day_idx, row_in_table), (day_idx, row_in_table),
                     HexColor("#F8F8F8"))
                )

            if is_outside:
                cell_styles.append(
                    ("BACKGROUND", (day_idx, row_in_table), (day_idx, row_in_table),
                     HexColor("#F0F0F0"))
                )

            row.append(Paragraph(cell_content, styles["Normal"]))
        data_rows.append(row)

    # Row height: divide available space evenly for 6 weeks + header
    # Available height ~ 5.5" in landscape after title + header/footer
    row_h = 0.82 * inch
    header_h = 0.3 * inch

    tbl = Table(
        data_rows,
        colWidths=[col_w] * 7,
        rowHeights=[header_h] + [row_h] * 6,
    )

    style_commands = [
        # Header row
        ("BACKGROUND", (0, 0), (-1, 0), EVLIN_NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#FFFFFF")),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
        # All cells
        ("VALIGN", (0, 1), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, EVLIN_LIGHT_BLUE),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 1), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 3),
    ]
    style_commands.extend(cell_styles)

    tbl.setStyle(TableStyle(style_commands))
    story.append(tbl)

    return story


def build_semester_calendar_pdf(
    student: dict,
    schedules: list[dict],
    slots: list[dict],
    num_months: int = 3,
    start_date: date = None,
) -> bytes:
    """Generate a multi-month semester calendar PDF.

    Each month gets its own landscape page with a wall-calendar grid.
    Course slots are shown in each day cell with color coding by subject.

    Args:
        student: Student dict
        schedules: Active schedules with nested course info
        slots: All weekly schedule slots with course_code, course_title, etc.
        num_months: Number of months to generate (default 3)
        start_date: Semester start date (defaults to start of current month)

    Returns: PDF as bytes
    """
    buffer = BytesIO()
    styles = get_evlin_styles()

    student_name = f"{student['first_name']} {student['last_name']}"

    if start_date is None:
        today = date.today()
        start_date = today.replace(day=1)

    end_date = start_date
    for _ in range(num_months):
        # Advance to next month
        if end_date.month == 12:
            end_date = end_date.replace(year=end_date.year + 1, month=1, day=1)
        else:
            end_date = end_date.replace(month=end_date.month + 1, day=1)
    end_date = end_date - timedelta(days=1)  # last day of final month

    start_str = start_date.strftime("%b %Y")
    end_str = end_date.strftime("%b %Y")

    doc = _CalendarDoc(
        buffer,
        title=f"Course Calendar — {student_name}",
        subtitle=f"Grade {student['grade_level']} | {start_str} – {end_str}",
    )

    story = []

    # ── Cover / Summary Page ─────────────────────────
    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph("Semester Course Calendar", styles["EvlinTitle"]))
    story.append(Paragraph(
        f"{student_name} — Grade {student['grade_level']}",
        styles["EvlinSubtitle"],
    ))
    story.append(Paragraph(
        f"{start_str} – {end_str}  ({num_months} months)",
        styles["EvlinBody"],
    ))
    story.append(HRFlowable(width="100%", thickness=2, color=EVLIN_BLUE))
    story.append(Spacer(1, 0.2 * inch))

    # Course legend
    if schedules:
        story.append(Paragraph("Enrolled Courses", styles["EvlinH2"]))

        legend_data = [["Code", "Course", "Subject", "Hrs/Wk", "Schedule"]]
        for sch in schedules:
            c = sch.get("courses", {})
            code = c.get("code", "")
            subj = c.get("subject", "")

            # Build schedule description from slots
            sch_slots = [s for s in slots if s.get("course_code") == code]
            day_names_short = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            sched_parts = []
            for s in sorted(sch_slots, key=lambda x: x.get("day_of_week", 0)):
                dn = day_names_short[s["day_of_week"]]
                t = str(s.get("start_time", ""))[:5]
                sched_parts.append(f"{dn} {t}")
            sched_str = ", ".join(sched_parts) if sched_parts else "TBD"

            legend_data.append([
                code,
                c.get("title", ""),
                subj,
                str(c.get("hours_per_week", "")),
                sched_str,
            ])

        legend_tbl = Table(
            legend_data,
            colWidths=[0.9 * inch, 2.8 * inch, 0.9 * inch, 0.7 * inch, 2.5 * inch],
        )
        legend_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), EVLIN_NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#FFFFFF")),
            ("FONTNAME", (0, 0), (-1, 0), HEADING_FONT),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("PADDING", (0, 0), (-1, -1), 5),
            ("GRID", (0, 0), (-1, -1), 0.5, EVLIN_LIGHT_BLUE),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#FFFFFF"), EVLIN_GRAY]),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(legend_tbl)

        # Color legend
        story.append(Spacer(1, 0.15 * inch))
        subjects_in_use = set()
        for sch in schedules:
            subjects_in_use.add(sch.get("courses", {}).get("subject", ""))

        color_parts = []
        for subj in sorted(subjects_in_use):
            fg, _ = SUBJECT_COLORS.get(subj, ("#333", "#FFF"))
            color_parts.append(f'<font color="{fg}"><b>■</b></font> {subj}')
        if color_parts:
            story.append(Paragraph(
                "Color key:  " + "    ".join(color_parts),
                styles["EvlinBody"],
            ))

        total_hours = sum(s.get("courses", {}).get("hours_per_week", 0) for s in schedules)
        story.append(Paragraph(
            f"<b>Total Weekly Hours: {total_hours:.1f}</b>",
            styles["EvlinBody"],
        ))
    else:
        story.append(Paragraph("No active courses enrolled.", styles["EvlinBody"]))

    # ── Monthly Calendar Pages ───────────────────────
    cur = start_date
    for i in range(num_months):
        story.append(PageBreak())
        month_story = _build_month_page(
            year=cur.year,
            month=cur.month,
            slots=slots,
            schedules=schedules,
            styles=styles,
            start_date=start_date,
            end_date=end_date,
        )
        story.extend(month_story)

        # Advance to next month
        if cur.month == 12:
            cur = cur.replace(year=cur.year + 1, month=1)
        else:
            cur = cur.replace(month=cur.month + 1)

    doc.build(story)
    return buffer.getvalue()
