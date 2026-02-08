"""PDF generation tool for agent use."""
from __future__ import annotations
import json


def generate_pdf(
    pdf_type: str,
    subject: str = None,
    grade: int = None,
    num_problems: int = 10,
    difficulty: str = "standard",
    course_code: str = None,
    student_id: str = None,
) -> str:
    """Generate a PDF document.

    Args:
        pdf_type: "practice_problems", "course_overview", or "schedule_report"
        subject: Subject for practice problems
        grade: Grade level for practice problems
        num_problems: Number of problems (practice_problems only)
        difficulty: Difficulty level (practice_problems only)
        course_code: Course code (course_overview only)
        student_id: Student UUID (schedule_report only)

    Returns: JSON string with status and download info
    """
    try:
        if pdf_type == "practice_problems":
            from agents.pdf_agent import generate_practice_problems_pdf
            pdf_bytes = generate_practice_problems_pdf(
                subject=subject or "Math",
                grade=grade or 5,
                num_problems=num_problems,
                difficulty=difficulty,
                student_id=student_id,
            )
            return json.dumps({
                "status": "success",
                "type": "practice_problems",
                "size_kb": len(pdf_bytes) // 1024,
                "message": f"Generated {num_problems} {subject} problems for grade {grade}",
            })

        elif pdf_type == "course_overview":
            from db.queries import get_course_by_code
            from pdf.generator import generate_course_overview_pdf

            course = get_course_by_code(course_code)
            if not course:
                return json.dumps({"error": f"Course {course_code} not found"})
            pdf_bytes = generate_course_overview_pdf(course)
            return json.dumps({
                "status": "success",
                "type": "course_overview",
                "course": f"{course['code']} - {course['title']}",
                "size_kb": len(pdf_bytes) // 1024,
            })

        elif pdf_type == "schedule_report":
            from pdf.generator import generate_schedule_report_pdf
            pdf_bytes = generate_schedule_report_pdf(student_id)
            return json.dumps({
                "status": "success",
                "type": "schedule_report",
                "size_kb": len(pdf_bytes) // 1024,
            })

        else:
            return json.dumps({"error": f"Unknown PDF type: {pdf_type}"})

    except Exception as e:
        return json.dumps({"error": str(e)})
