import streamlit as st

st.set_page_config(
    page_title="Evlin Scheduler",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize session state
if "selected_student_id" not in st.session_state:
    st.session_state.selected_student_id = None
if "selected_student_name" not in st.session_state:
    st.session_state.selected_student_name = None

st.title("📚 Evlin Homeschool Calendar Scheduler")
st.markdown("---")

st.markdown("""
### Welcome to the Evlin Scheduling System

Use the sidebar to select a student, then navigate to the tools:

- **Dashboard** — View student overview and current schedule
- **Scheduler** — Chat with the AI scheduling assistant
- **Courses** — Browse the course catalog
- **PDF Generator** — Create textbook-quality practice materials
- **OCR Upload** — Extract text from uploaded documents
- **Calendar View** — Interactive monthly / weekly / list calendar
- **Daily Check-In** — Mark courses complete, reschedule missed sessions

Select a student from the sidebar to get started.
""")

# Sidebar: student selector
try:
    from db.queries import get_all_students

    students = get_all_students()
    if students:
        st.sidebar.markdown("### 👤 Select Student")
        options = {f"{s['first_name']} {s['last_name']} (Grade {s['grade_level']})": s["id"] for s in students}
        selected = st.sidebar.selectbox(
            "Student",
            options.keys(),
            index=0,
            label_visibility="collapsed",
        )
        st.session_state.selected_student_id = options[selected]
        st.session_state.selected_student_name = selected.split(" (")[0]
        st.sidebar.markdown(f"**Selected:** {st.session_state.selected_student_name}")
    else:
        st.sidebar.warning("No students found. Run `python seed_data.py` first.")
except Exception as e:
    st.sidebar.error(f"Database connection error: {e}")
    st.sidebar.info("Make sure .env is configured and Supabase is set up.")

# Quick stats on main page
if st.session_state.selected_student_id:
    try:
        from db.queries import get_student_schedules, get_student_availability

        col1, col2, col3 = st.columns(3)
        schedules = get_student_schedules(st.session_state.selected_student_id, status="active")
        availability = get_student_availability(st.session_state.selected_student_id)

        total_hours = sum(
            s.get("courses", {}).get("hours_per_week", 0) for s in schedules
        )

        with col1:
            st.metric("Active Courses", len(schedules))
        with col2:
            st.metric("Weekly Hours", f"{total_hours:.1f}")
        with col3:
            st.metric("Available Slots", len(availability))
    except Exception:
        pass
