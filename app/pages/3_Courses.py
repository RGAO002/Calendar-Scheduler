import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.components.sidebar import render_student_selector

st.set_page_config(page_title="Courses - Evlin", layout="wide")
st.title("📖 Course Catalog")

render_student_selector()
st.markdown("---")

try:
    from db.queries import get_all_courses

    courses = get_all_courses()

    if not courses:
        st.warning("No courses found. Run `python seed_data.py --supabase` first.")
        st.stop()

    # Filters
    col1, col2, col3, col4 = st.columns(4)

    subjects = sorted(set(c["subject"] for c in courses))
    with col1:
        subject_filter = st.selectbox("Subject", ["All"] + subjects)

    grades = sorted(set(range(1, 13)))
    with col2:
        grade_filter = st.selectbox("Grade Level", ["All"] + list(range(1, 13)))

    difficulties = sorted(set(c["difficulty"] for c in courses))
    with col3:
        diff_filter = st.selectbox("Difficulty", ["All"] + difficulties)

    with col4:
        search_term = st.text_input("Search", placeholder="Search courses...")

    # Apply filters
    filtered = courses
    if subject_filter != "All":
        filtered = [c for c in filtered if c["subject"] == subject_filter]
    if grade_filter != "All":
        filtered = [
            c for c in filtered
            if c["grade_level_min"] <= grade_filter <= c["grade_level_max"]
        ]
    if diff_filter != "All":
        filtered = [c for c in filtered if c["difficulty"] == diff_filter]
    if search_term:
        term = search_term.lower()
        filtered = [
            c for c in filtered
            if term in c["title"].lower()
            or term in c.get("description", "").lower()
            or term in c["code"].lower()
        ]

    st.markdown(f"**Showing {len(filtered)} of {len(courses)} courses**")
    st.markdown("---")

    # Display courses in a grid
    for i in range(0, len(filtered), 2):
        cols = st.columns(2)
        for j, col in enumerate(cols):
            idx = i + j
            if idx >= len(filtered):
                break
            c = filtered[idx]
            with col:
                with st.container(border=True):
                    st.markdown(f"#### {c['code']} — {c['title']}")
                    tag_cols = st.columns(4)
                    with tag_cols[0]:
                        st.caption(f"📚 {c['subject']}")
                    with tag_cols[1]:
                        st.caption(f"📊 Grade {c['grade_level_min']}-{c['grade_level_max']}")
                    with tag_cols[2]:
                        st.caption(f"⏱️ {c['hours_per_week']}h/wk")
                    with tag_cols[3]:
                        st.caption(f"🎯 {c['difficulty']}")

                    st.write(c.get("description", ""))

                    if c.get("prerequisites"):
                        st.caption(f"Prerequisites: {', '.join(c['prerequisites'])}")
                    if c.get("tags"):
                        st.caption(f"Tags: {', '.join(c['tags'])}")

except Exception as e:
    st.error(f"Error loading courses: {e}")
    st.info("Make sure the database is seeded. Run: `python seed_data.py --supabase`")
