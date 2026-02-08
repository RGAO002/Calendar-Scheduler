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
    ["Practice Problems", "Course Overview", "Schedule Report"],
)

st.markdown("---")

if pdf_type == "Practice Problems":
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
