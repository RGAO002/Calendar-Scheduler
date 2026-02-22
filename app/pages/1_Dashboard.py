import streamlit as st
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.components.sidebar import render_student_selector, get_selected_student_id
from app.components.schedule_calendar import render_weekly_calendar

st.set_page_config(page_title="Dashboard - Evlin", layout="wide")
st.title("📊 Student Dashboard")

student_id = render_student_selector()

if not student_id:
    st.info("Select a student from the sidebar to view their dashboard.")
    st.stop()

try:
    from db.queries import (
        get_student,
        get_student_schedules,
        get_student_availability,
        get_student_all_slots,
    )

    student = get_student(student_id)

    if not student:
        st.error("Student not found.")
        st.stop()

    # Student info header
    st.markdown(f"### {student['first_name']} {student['last_name']} — Grade {student['grade_level']}")
    if student.get("notes"):
        st.caption(student["notes"])
    st.markdown("---")

    # Metrics
    schedules = get_student_schedules(student_id, status="active")
    availability = get_student_availability(student_id)

    total_hours = sum(s.get("courses", {}).get("hours_per_week", 0) for s in schedules)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Active Courses", len(schedules))
    with col2:
        st.metric("Weekly Hours", f"{total_hours:.1f}")
    with col3:
        st.metric("Available Slots", len(availability))
    with col4:
        preferred = sum(1 for a in availability if a.get("preference") == "preferred")
        st.metric("Preferred Slots", preferred)

    # Check-In Progress
    try:
        from db.queries import get_checkin_stats, get_unresolved_missed

        stats = get_checkin_stats(student_id)
        missed = get_unresolved_missed(student_id)

        st.markdown("---")
        st.subheader("📈 Check-In Progress")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            rate = stats.get("completion_rate", 0)
            st.metric("Completion Rate", f"{rate:.0%}")
        with c2:
            st.metric("Current Streak", f"{stats.get('streak', 0)} days")
        with c3:
            wc = stats.get("week_completed", 0)
            wt = stats.get("week_total", 0)
            st.metric("This Week", f"{wc}/{wt}")
        with c4:
            st.metric("Missed (Unresolved)", len(missed))
    except Exception:
        pass  # check-in tables may not exist yet

    st.markdown("---")

    # Weekly Calendar
    st.subheader("📅 Weekly Schedule")
    all_slots = get_student_all_slots(student_id)

    # Enrich slots with subject info for coloring
    for slot in all_slots:
        for sch in schedules:
            if sch.get("courses", {}).get("code") == slot.get("course_code"):
                slot["subject"] = sch["courses"].get("subject", "")
                break

    render_weekly_calendar(all_slots, availability)

    # Active courses table
    st.markdown("---")
    st.subheader("📚 Active Courses")
    if schedules:
        for sch in schedules:
            course = sch.get("courses", {})
            with st.expander(f"**{course.get('code', '')}** — {course.get('title', '')}"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.write(f"**Subject:** {course.get('subject', '')}")
                with col2:
                    st.write(f"**Hours/week:** {course.get('hours_per_week', 0)}")
                with col3:
                    st.write(f"**Difficulty:** {course.get('difficulty', 'standard')}")
                st.write(course.get("description", ""))
                st.caption(f"Status: {sch.get('status', '')} | Started: {sch.get('start_date', '')}")
    else:
        st.info("No active courses. Use the Scheduler to add courses.")

    # Availability summary
    st.markdown("---")
    st.subheader("🕐 Weekly Availability")
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    avail_by_day = {}
    for a in availability:
        day = a.get("day_of_week", 0)
        if day not in avail_by_day:
            avail_by_day[day] = []
        avail_by_day[day].append(a)

    for day_idx in sorted(avail_by_day.keys()):
        day_slots = avail_by_day[day_idx]
        slots_str = ", ".join(
            f"{s['start_time']}-{s['end_time']} ({s.get('preference', 'available')})"
            for s in day_slots
        )
        st.write(f"**{day_names[day_idx]}:** {slots_str}")

except Exception as e:
    st.error(f"Error loading dashboard: {e}")
    st.info("Make sure the database is seeded. Run: `python seed_data.py --supabase`")
