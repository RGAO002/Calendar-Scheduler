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


def generate_semester_calendar_pdf(
    student_id: str = None,
    num_months: int = 3,
    start_date=None,
    student: dict = None,
    schedules: list = None,
    slots: list = None,
) -> bytes:
    """Generate a multi-month semester calendar PDF.

    Can be called with just student_id (will query DB), or with
    pre-fetched student/schedules/slots data for offline use.
    """
    from pdf.templates.semester_calendar import build_semester_calendar_pdf

    if student is None:
        from db.queries import get_student, get_student_schedules, get_student_all_slots
        student = get_student(student_id)
        if not student:
            raise ValueError(f"Student {student_id} not found")
        schedules = get_student_schedules(student_id, status="active")
        slots = get_student_all_slots(student_id)

    return build_semester_calendar_pdf(
        student=student,
        schedules=schedules or [],
        slots=slots or [],
        num_months=num_months,
        start_date=start_date,
    )


def generate_demo_calendar_pdf(num_months: int = 3) -> bytes:
    """Generate a demo 3-month calendar with sample data. No DB needed."""
    from datetime import date
    from pdf.templates.semester_calendar import build_semester_calendar_pdf

    today = date.today()
    start = today.replace(day=1)

    # Demo student
    student = {
        "first_name": "Emma",
        "last_name": "Chen",
        "grade_level": 5,
        "parent_name": "Linda Chen",
    }

    # Demo schedules (mimic DB format)
    demo_schedules = [
        {"courses": {"code": "MATH-5A", "title": "Fractions & Decimals", "subject": "Math", "hours_per_week": 3.0}},
        {"courses": {"code": "ELA-5A", "title": "Grammar & Composition", "subject": "English", "hours_per_week": 3.0}},
        {"courses": {"code": "SCI-5A", "title": "Earth Science", "subject": "Science", "hours_per_week": 3.0}},
        {"courses": {"code": "HIST-5A", "title": "US History I", "subject": "History", "hours_per_week": 3.0}},
        {"courses": {"code": "ART-3A", "title": "Drawing Fundamentals", "subject": "Art", "hours_per_week": 2.0}},
        {"courses": {"code": "PE-3A", "title": "Movement & Fitness", "subject": "PE", "hours_per_week": 2.0}},
    ]

    # Demo weekly slots
    demo_slots = [
        # MATH-5A: Mon/Wed 9:00-10:00
        {"day_of_week": 0, "start_time": "09:00", "end_time": "10:00", "course_code": "MATH-5A", "course_title": "Fractions & Decimals"},
        {"day_of_week": 2, "start_time": "09:00", "end_time": "10:00", "course_code": "MATH-5A", "course_title": "Fractions & Decimals"},
        # ELA-5A: Tue/Thu 9:00-10:00
        {"day_of_week": 1, "start_time": "09:00", "end_time": "10:00", "course_code": "ELA-5A", "course_title": "Grammar & Composition"},
        {"day_of_week": 3, "start_time": "09:00", "end_time": "10:00", "course_code": "ELA-5A", "course_title": "Grammar & Composition"},
        # SCI-5A: Mon/Wed 10:30-11:30
        {"day_of_week": 0, "start_time": "10:30", "end_time": "11:30", "course_code": "SCI-5A", "course_title": "Earth Science"},
        {"day_of_week": 2, "start_time": "10:30", "end_time": "11:30", "course_code": "SCI-5A", "course_title": "Earth Science"},
        # HIST-5A: Tue/Thu 10:30-11:30
        {"day_of_week": 1, "start_time": "10:30", "end_time": "11:30", "course_code": "HIST-5A", "course_title": "US History I"},
        {"day_of_week": 3, "start_time": "10:30", "end_time": "11:30", "course_code": "HIST-5A", "course_title": "US History I"},
        # ART-3A: Fri 9:00-11:00
        {"day_of_week": 4, "start_time": "09:00", "end_time": "11:00", "course_code": "ART-3A", "course_title": "Drawing Fundamentals"},
        # PE-3A: Fri 13:00-14:00
        {"day_of_week": 4, "start_time": "13:00", "end_time": "14:00", "course_code": "PE-3A", "course_title": "Movement & Fitness"},
    ]

    return build_semester_calendar_pdf(
        student=student,
        schedules=demo_schedules,
        slots=demo_slots,
        num_months=num_months,
        start_date=start,
    )
