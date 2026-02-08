"""Shared sidebar component for student selection."""
from __future__ import annotations
import streamlit as st


def render_student_selector():
    """Render student selector in sidebar. Returns selected student_id or None."""
    try:
        from db.queries import get_all_students

        students = get_all_students()
        if not students:
            st.sidebar.warning("No students found. Run seed_data.py first.")
            return None

        st.sidebar.markdown("### 👤 Select Student")
        options = {
            f"{s['first_name']} {s['last_name']} (Grade {s['grade_level']})": s
            for s in students
        }
        selected_label = st.sidebar.selectbox(
            "Student",
            options.keys(),
            index=0,
            label_visibility="collapsed",
        )
        student = options[selected_label]
        st.session_state.selected_student_id = student["id"]
        st.session_state.selected_student_name = f"{student['first_name']} {student['last_name']}"

        st.sidebar.markdown(f"**Grade:** {student['grade_level']}")
        if student.get("parent_name"):
            st.sidebar.markdown(f"**Parent:** {student['parent_name']}")
        if student.get("notes"):
            st.sidebar.caption(student["notes"])

        return student["id"]
    except Exception as e:
        st.sidebar.error(f"Error loading students: {e}")
        return None


def get_selected_student_id() -> str | None:
    return st.session_state.get("selected_student_id")


def get_selected_student_name() -> str | None:
    return st.session_state.get("selected_student_name")
