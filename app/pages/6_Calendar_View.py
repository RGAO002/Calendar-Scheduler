"""Interactive calendar view for student course schedules.

Uses streamlit-calendar (FullCalendar wrapper) to display courses
in month / week / list views with color-coded subjects.
"""
from __future__ import annotations

import streamlit as st
import sys
from pathlib import Path
from datetime import date, timedelta, datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.components.sidebar import render_student_selector

st.set_page_config(page_title="Calendar View - Evlin", layout="wide")
st.title("📅 Course Calendar")

student_id = render_student_selector()
st.markdown("---")

# ── Subject color palette ────────────────────────────────
SUBJECT_COLORS = {
    "Math":    {"bg": "#4A90D9", "border": "#3A7CC3"},
    "Science": {"bg": "#27AE60", "border": "#1E9B4E"},
    "English": {"bg": "#E67E22", "border": "#CF6E15"},
    "History": {"bg": "#8E44AD", "border": "#7D389A"},
    "Art":     {"bg": "#E74C3C", "border": "#D43D2F"},
    "PE":      {"bg": "#16A085", "border": "#128E75"},
}

DEFAULT_COLOR = {"bg": "#666666", "border": "#555555"}


def _build_demo_events() -> tuple[list[dict], dict]:
    """Build demo calendar events when DB is not available.

    Returns (events_list, student_info_dict).
    """
    student = {
        "first_name": "Emma",
        "last_name": "Chen",
        "grade_level": 5,
    }

    demo_courses = [
        {"code": "MATH-5A", "title": "Fractions & Decimals", "subject": "Math",
         "slots": [(0, "09:00", "10:00"), (2, "09:00", "10:00")]},
        {"code": "ELA-5A", "title": "Grammar & Composition", "subject": "English",
         "slots": [(1, "09:00", "10:00"), (3, "09:00", "10:00")]},
        {"code": "SCI-5A", "title": "Earth Science", "subject": "Science",
         "slots": [(0, "10:30", "11:30"), (2, "10:30", "11:30")]},
        {"code": "HIST-5A", "title": "US History I", "subject": "History",
         "slots": [(1, "10:30", "11:30"), (3, "10:30", "11:30")]},
        {"code": "ART-3A", "title": "Drawing Fundamentals", "subject": "Art",
         "slots": [(4, "09:00", "11:00")]},
        {"code": "PE-3A", "title": "Movement & Fitness", "subject": "PE",
         "slots": [(4, "13:00", "14:00")]},
    ]

    events = _weekly_slots_to_events(demo_courses, num_weeks=14)
    return events, student


def _weekly_slots_to_events(
    courses: list[dict],
    num_weeks: int = 14,
    start_date: date | None = None,
) -> list[dict]:
    """Expand weekly slot definitions into individual FullCalendar events.

    Args:
        courses: List of dicts with code, title, subject, slots [(dow, start, end), ...]
        num_weeks: How many weeks of events to generate
        start_date: Starting Monday to begin generating (defaults to start of current month's week)

    Returns: List of FullCalendar-compatible event dicts
    """
    if start_date is None:
        today = date.today()
        # Go to start of current month, then find that week's Monday
        first_of_month = today.replace(day=1)
        # Find the Monday of the week containing the 1st
        start_date = first_of_month - timedelta(days=first_of_month.weekday())

    events = []
    event_id = 1

    for course in courses:
        code = course["code"]
        title = course["title"]
        subject = course.get("subject", "")
        colors = SUBJECT_COLORS.get(subject, DEFAULT_COLOR)

        for dow, start_time, end_time in course["slots"]:
            for week_offset in range(num_weeks):
                event_date = start_date + timedelta(weeks=week_offset, days=dow)

                events.append({
                    "id": str(event_id),
                    "title": f"{code}: {title}",
                    "start": f"{event_date.isoformat()}T{start_time}:00",
                    "end": f"{event_date.isoformat()}T{end_time}:00",
                    "backgroundColor": colors["bg"],
                    "borderColor": colors["border"],
                    "textColor": "#FFFFFF",
                    "extendedProps": {
                        "code": code,
                        "subject": subject,
                    },
                })
                event_id += 1

    return events


def _db_to_events(schedules: list[dict], slots: list[dict]) -> list[dict]:
    """Convert DB schedule/slot records to FullCalendar events.

    This takes the Supabase-style data and generates 14 weeks of events.
    """
    # Build course info lookup from schedules
    course_info = {}
    for sch in schedules:
        c = sch.get("courses", {})
        code = c.get("code", "")
        course_info[code] = {
            "code": code,
            "title": c.get("title", ""),
            "subject": c.get("subject", ""),
            "slots": [],
        }

    # Attach slots to their courses
    for s in slots:
        code = s.get("course_code", "")
        if code in course_info:
            course_info[code]["slots"].append((
                s.get("day_of_week", 0),
                str(s.get("start_time", "09:00"))[:5],
                str(s.get("end_time", "10:00"))[:5],
            ))

    return _weekly_slots_to_events(list(course_info.values()), num_weeks=14)


# ── Load events ──────────────────────────────────────────
use_demo = False
student_info = None

if student_id:
    try:
        from db.queries import (
            get_student,
            get_student_schedules,
            get_student_all_slots,
        )
        student_info = get_student(student_id)
        schedules = get_student_schedules(student_id, status="active")
        all_slots = get_student_all_slots(student_id)

        if schedules and all_slots:
            events = _db_to_events(schedules, all_slots)
        else:
            st.warning("No active courses found for this student. Showing **demo calendar**.")
            use_demo = True
    except Exception as e:
        st.warning(f"Could not load from database: {e}")
        use_demo = True
else:
    st.info("No student selected — showing **demo calendar** with sample data.")
    use_demo = True

if use_demo:
    events, student_info = _build_demo_events()

# ── Student header ───────────────────────────────────────
if student_info:
    name = f"{student_info['first_name']} {student_info['last_name']}"
    grade = student_info.get("grade_level", "")
    st.markdown(f"### {name} — Grade {grade}")

# ── Color legend ─────────────────────────────────────────
subjects_in_use = set()
for ev in events:
    subj = ev.get("extendedProps", {}).get("subject", "")
    if subj:
        subjects_in_use.add(subj)

if subjects_in_use:
    legend_html = '<div style="display:flex;gap:18px;flex-wrap:wrap;margin-bottom:12px;">'
    for subj in sorted(subjects_in_use):
        color = SUBJECT_COLORS.get(subj, DEFAULT_COLOR)["bg"]
        legend_html += (
            f'<span style="display:inline-flex;align-items:center;gap:5px;">'
            f'<span style="display:inline-block;width:14px;height:14px;background:{color};'
            f'border-radius:3px;"></span>'
            f'<span style="font-size:14px;">{subj}</span></span>'
        )
    legend_html += '</div>'
    st.markdown(legend_html, unsafe_allow_html=True)

# ── View selector ────────────────────────────────────────
col1, col2 = st.columns([2, 4])
with col1:
    view_mode = st.selectbox(
        "View",
        ["Month", "Week", "List"],
        index=0,
        label_visibility="collapsed",
    )

view_map = {
    "Month": "dayGridMonth",
    "Week": "timeGridWeek",
    "List": "listMonth",
}

# ── Calendar options ─────────────────────────────────────
calendar_options = {
    "initialView": view_map[view_mode],
    "initialDate": date.today().isoformat(),
    "headerToolbar": {
        "left": "prev,next today",
        "center": "title",
        "right": "dayGridMonth,timeGridWeek,listMonth",
    },
    "slotMinTime": "07:00:00",
    "slotMaxTime": "18:00:00",
    "allDaySlot": False,
    "expandRows": True,
    "height": 680,
    "dayMaxEvents": 3,
    "navLinks": True,
    "selectable": False,
    "editable": False,
    "eventDisplay": "block",
    "eventTimeFormat": {
        "hour": "2-digit",
        "minute": "2-digit",
        "hour12": False,
    },
}

# ── Custom CSS for the calendar ──────────────────────────
custom_css = """
    .fc-toolbar-title {
        font-size: 1.4em !important;
        color: #1B2A4A !important;
    }
    .fc-button-primary {
        background-color: #2E5090 !important;
        border-color: #2E5090 !important;
    }
    .fc-button-primary:hover {
        background-color: #1B2A4A !important;
    }
    .fc-button-primary.fc-button-active {
        background-color: #1B2A4A !important;
    }
    .fc-event {
        font-size: 0.85em !important;
        border-radius: 4px !important;
        padding: 1px 4px !important;
    }
    .fc-daygrid-event {
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }
    .fc-day-today {
        background-color: #FFF8E1 !important;
    }
"""

# ── Render calendar ──────────────────────────────────────
try:
    from streamlit_calendar import calendar as st_calendar

    cal_data = st_calendar(
        events=events,
        options=calendar_options,
        custom_css=custom_css,
        key="evlin_calendar",
    )

    # Show event details when clicked
    if cal_data and cal_data.get("eventClick"):
        ev = cal_data["eventClick"].get("event", {})
        ext = ev.get("extendedProps", {})
        with st.expander(f"📌 {ev.get('title', '')}", expanded=True):
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.write(f"**Course:** {ext.get('code', '')}")
            with col_b:
                st.write(f"**Subject:** {ext.get('subject', '')}")
            with col_c:
                start_str = ev.get("start", "")[:16].replace("T", " ")
                end_str = ev.get("end", "")[:16].replace("T", " ")
                st.write(f"**Time:** {start_str} → {end_str}")

except ImportError:
    st.error(
        "The `streamlit-calendar` package is not installed.\n\n"
        "Run: `pip install streamlit-calendar`"
    )
except Exception as e:
    st.error(f"Error rendering calendar: {e}")
    import traceback
    st.code(traceback.format_exc())

# ── Summary stats ────────────────────────────────────────
st.markdown("---")
total_events = len(events)
unique_courses = len({ev.get("extendedProps", {}).get("code") for ev in events if ev.get("extendedProps", {}).get("code")})
st.caption(f"Showing {total_events} class sessions for {unique_courses} courses across 14 weeks.")

if use_demo:
    st.info(
        "💡 This is demo data. To see your real schedule, set up the database:\n"
        "1. Run `setup_supabase.sql` in Supabase SQL Editor\n"
        "2. Run `python seed_data.py --supabase`\n"
        "3. Select a student from the sidebar"
    )
