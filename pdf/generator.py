"""PDF generation orchestrator."""
from __future__ import annotations
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def generate_practice_pdf_from_sample(subject: str, grade: int) -> bytes | None:
    """Generate a practice problems PDF from sample data files.

    This is the fallback when Gemini API is not available.
    """
    from pdf.templates.practice_problems import build_practice_problems_pdf

    # Map subject to sample file
    subject_file_map = {
        "Math": "math_grade5.json",
        "Science": "science_grade6.json",
        "English": "english_grade7.json",
    }

    filename = subject_file_map.get(subject)
    if not filename:
        return None

    sample_path = DATA_DIR / "sample_problems" / filename
    if not sample_path.exists():
        return None

    with open(sample_path) as f:
        data = json.load(f)

    return build_practice_problems_pdf(
        title=data.get("title", f"{subject} Practice Set"),
        subject=data.get("subject", subject),
        grade=data.get("grade", grade),
        problems=data.get("problems", []),
        include_answers=True,
    )


def generate_course_overview_pdf(course: dict) -> bytes:
    """Generate a course overview PDF."""
    from pdf.templates.course_overview import build_course_overview_pdf
    return build_course_overview_pdf(course)


def generate_schedule_report_pdf(student_id: str) -> bytes:
    """Generate a schedule report PDF for a student."""
    from db.queries import get_student, get_student_schedules, get_student_all_slots
    from pdf.templates.schedule_report import build_schedule_report_pdf

    student = get_student(student_id)
    if not student:
        raise ValueError(f"Student {student_id} not found")

    schedules = get_student_schedules(student_id, status="active")
    slots = get_student_all_slots(student_id)

    return build_schedule_report_pdf(student, schedules, slots)
