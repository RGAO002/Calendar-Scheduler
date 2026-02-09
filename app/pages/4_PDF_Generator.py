import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.components.sidebar import render_student_selector, get_selected_student_id
from app.components.pdf_preview import render_pdf_preview

st.set_page_config(page_title="PDF Generator - Evlin", layout="wide")
st.title("📄 PDF Generator")

student_id = render_student_selector()
st.markdown("---")

# PDF type selector
pdf_type = st.selectbox(
    "What would you like to generate?",
    ["Semester Calendar (3+ Months)", "Practice Problems", "Course Overview", "Schedule Report"],
)

st.markdown("---")

if pdf_type == "Semester Calendar (3+ Months)":
    st.subheader("Generate Semester Course Calendar")
    st.markdown("Generate a wall-calendar style PDF with your course schedule marked on each day.")

    col1, col2 = st.columns(2)
    with col1:
        num_months = st.selectbox("Number of Months", [3, 4, 5, 6], index=0)
    with col2:
        from datetime import date
        start_date = st.date_input("Start Date", value=date.today().replace(day=1))

    # Determine data source
    use_demo = False
    if student_id:
        # Try to check if the student actually has active courses
        try:
            from db.queries import get_student_schedules, get_student_all_slots
            schedules = get_student_schedules(student_id, status="active")
            slots = get_student_all_slots(student_id)
            if schedules and slots:
                st.info(f"Will generate calendar with **{len(schedules)} active courses** for the selected student.")
            else:
                st.warning(
                    "Selected student has **no active courses**. "
                    "Using **demo data** (Emma Chen, Grade 5, 6 courses).\n\n"
                    "To use real data, seed the database: `python seed_data.py --supabase`"
                )
                use_demo = True
        except Exception:
            st.warning("Could not connect to database — will use **demo calendar** with sample data.")
            use_demo = True
    else:
        st.warning("No student selected — will generate a **demo calendar** with sample data.")
        use_demo = True

    if st.button("Generate Semester Calendar PDF", type="primary"):
        with st.spinner(f"Generating {num_months}-month calendar..."):
            try:
                if use_demo:
                    from pdf.generator import generate_demo_calendar_pdf
                    pdf_bytes = generate_demo_calendar_pdf(num_months=num_months)
                else:
                    from pdf.generator import generate_semester_calendar_pdf
                    pdf_bytes = generate_semester_calendar_pdf(
                        student_id=student_id,
                        num_months=num_months,
                        start_date=start_date,
                    )
                st.success(f"{num_months}-month calendar generated!")
                student_name = st.session_state.get("selected_student_name", "Demo")
                render_pdf_preview(
                    pdf_bytes,
                    filename=f"{student_name}_Calendar_{num_months}mo.pdf",
                )
            except Exception as e:
                st.error(f"Error: {e}")
                import traceback
                st.code(traceback.format_exc())

elif pdf_type == "Practice Problems":
    st.subheader("Generate Practice Problems")

    col1, col2, col3 = st.columns(3)
    with col1:
        subject = st.selectbox(
            "Subject",
            ["Math", "Science", "English", "History"],
        )
    with col2:
        grade = st.number_input("Grade Level", min_value=1, max_value=12, value=5)
    with col3:
        num_problems = st.number_input("Number of Problems", min_value=5, max_value=30, value=10)

    difficulty = st.selectbox("Difficulty", ["standard", "easy", "advanced"])
    include_answers = st.checkbox("Include Answer Key", value=True)

    if st.button("Generate Practice Problems PDF", type="primary"):
        with st.spinner("Generating practice problems..."):
            try:
                from agents.pdf_agent import generate_practice_problems_pdf

                pdf_bytes = generate_practice_problems_pdf(
                    subject=subject,
                    grade=grade,
                    num_problems=num_problems,
                    difficulty=difficulty,
                    include_answers=include_answers,
                    student_id=student_id,
                )
                st.success("PDF generated successfully!")
                render_pdf_preview(
                    pdf_bytes,
                    filename=f"{subject}_Grade{grade}_Practice.pdf",
                )
            except ImportError:
                # Fallback: use sample data to generate PDF without AI
                st.info("Gemini API not configured. Generating from sample data...")
                try:
                    from pdf.generator import generate_practice_pdf_from_sample
                    pdf_bytes = generate_practice_pdf_from_sample(subject, grade)
                    if pdf_bytes:
                        st.success("PDF generated from sample data!")
                        render_pdf_preview(
                            pdf_bytes,
                            filename=f"{subject}_Grade{grade}_Practice.pdf",
                        )
                    else:
                        st.warning("No sample data found for this subject/grade combination.")
                except Exception as e:
                    st.error(f"Error generating PDF: {e}")
            except Exception as e:
                st.error(f"Error: {e}")

elif pdf_type == "Course Overview":
    st.subheader("Generate Course Overview")
    try:
        from db.queries import get_all_courses
        courses = get_all_courses()
        course_options = {f"{c['code']} - {c['title']}": c for c in courses}
        selected_course = st.selectbox("Select Course", list(course_options.keys()))

        if st.button("Generate Course Overview PDF", type="primary"):
            with st.spinner("Generating course overview..."):
                try:
                    from pdf.generator import generate_course_overview_pdf
                    course = course_options[selected_course]
                    pdf_bytes = generate_course_overview_pdf(course)
                    st.success("PDF generated!")
                    render_pdf_preview(pdf_bytes, filename=f"{course['code']}_Overview.pdf")
                except Exception as e:
                    st.error(f"Error: {e}")
    except Exception as e:
        st.error(f"Error loading courses: {e}")

elif pdf_type == "Schedule Report":
    st.subheader("Generate Schedule Report")
    if not student_id:
        st.info("Select a student from the sidebar first.")
    elif st.button("Generate Schedule Report PDF", type="primary"):
        with st.spinner("Generating schedule report..."):
            try:
                from pdf.generator import generate_schedule_report_pdf
                pdf_bytes = generate_schedule_report_pdf(student_id)
                st.success("PDF generated!")
                student_name = st.session_state.get("selected_student_name", "Student")
                render_pdf_preview(pdf_bytes, filename=f"{student_name}_Schedule.pdf")
            except Exception as e:
                st.error(f"Error: {e}")

# PDF History
st.markdown("---")
st.subheader("📋 Recent PDFs")
try:
    from db.queries import get_generated_pdfs
    pdfs = get_generated_pdfs(student_id=student_id, limit=10)
    if pdfs:
        for pdf in pdfs:
            st.write(f"- **{pdf['title']}** ({pdf['pdf_type']}) — {pdf['created_at'][:10]}")
    else:
        st.caption("No PDFs generated yet.")
except Exception:
    st.caption("PDF history unavailable.")
