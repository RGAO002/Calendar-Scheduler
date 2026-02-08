"""Weekly calendar grid component."""
from __future__ import annotations
import streamlit as st

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

SUBJECT_COLORS = {
    "Math": "#4A90D9",
    "Science": "#27AE60",
    "English": "#E67E22",
    "History": "#8E44AD",
    "Art": "#E74C3C",
    "PE": "#16A085",
}


def render_weekly_calendar(slots: list[dict], availability: list[dict] = None):
    """Render a weekly calendar grid showing schedule slots.

    Args:
        slots: List of dicts with day_of_week, start_time, end_time, course_title, course_code
        availability: Optional list of availability dicts for background shading
    """
    if not slots:
        st.info("No scheduled classes yet.")
        return

    # Build CSS
    css = """
    <style>
    .cal-grid { display: grid; grid-template-columns: 80px repeat(5, 1fr); gap: 2px; margin: 10px 0; }
    .cal-header { background: #1B2A4A; color: white; padding: 8px; text-align: center; font-weight: bold; font-size: 13px; border-radius: 4px; }
    .cal-time { background: #f0f0f0; padding: 6px; text-align: right; font-size: 12px; color: #666; border-radius: 4px; }
    .cal-slot { padding: 6px 8px; border-radius: 4px; font-size: 12px; color: white; margin: 1px 0; }
    .cal-empty { background: #fafafa; min-height: 30px; border-radius: 4px; }
    .cal-avail { background: #E8F5E9; min-height: 30px; border-radius: 4px; }
    .cal-avoid { background: #FFF3E0; min-height: 30px; border-radius: 4px; }
    </style>
    """

    # Build time slots from 7:00 to 17:00
    hours = list(range(7, 18))

    # Organize slots by day and hour
    slot_map = {}
    for s in slots:
        day = s.get("day_of_week", 0)
        start_h = int(str(s.get("start_time", "00:00"))[:2])
        end_h = int(str(s.get("end_time", "00:00"))[:2])
        end_m = int(str(s.get("end_time", "00:00"))[3:5])
        if end_m > 0:
            end_h += 1

        for h in range(start_h, end_h):
            key = (day, h)
            color = SUBJECT_COLORS.get(
                s.get("subject", ""),
                "#666"
            )
            slot_map[key] = {
                "label": f"{s.get('course_code', '')} {s.get('course_title', '')}",
                "time": f"{s.get('start_time', '')}-{s.get('end_time', '')}",
                "color": color,
            }

    # Build HTML grid
    html = css + '<div class="cal-grid">'

    # Header row
    html += '<div class="cal-header">Time</div>'
    for day in DAY_NAMES[:5]:
        html += f'<div class="cal-header">{day}</div>'

    # Time rows
    for hour in hours:
        time_label = f"{hour:02d}:00"
        html += f'<div class="cal-time">{time_label}</div>'

        for day in range(5):
            key = (day, hour)
            if key in slot_map:
                s = slot_map[key]
                html += f'<div class="cal-slot" style="background:{s["color"]}">{s["label"]}</div>'
            else:
                html += '<div class="cal-empty"></div>'

    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)
