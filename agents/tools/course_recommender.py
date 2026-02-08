"""Tools for searching and recommending courses."""
from __future__ import annotations
import json
from typing import Optional


def search_courses(
    subject: Optional[str] = None,
    grade_level: Optional[int] = None,
    difficulty: Optional[str] = None,
    keyword: Optional[str] = None,
) -> str:
    """Search courses by subject, grade level, difficulty, or keyword.

    Returns JSON string with matching courses.
    """
    from db.queries import get_all_courses

    courses = get_all_courses(active_only=True)

    if subject:
        courses = [c for c in courses if c["subject"].lower() == subject.lower()]
    if grade_level:
        courses = [
            c for c in courses
            if c["grade_level_min"] <= grade_level <= c["grade_level_max"]
        ]
    if difficulty:
        courses = [c for c in courses if c["difficulty"] == difficulty]
    if keyword:
        kw = keyword.lower()
        courses = [
            c for c in courses
            if kw in c["title"].lower()
            or kw in c.get("description", "").lower()
            or kw in c["code"].lower()
            or any(kw in t.lower() for t in c.get("tags", []))
        ]

    results = []
    for c in courses:
        results.append({
            "code": c["code"],
            "title": c["title"],
            "subject": c["subject"],
            "grade_range": f"{c['grade_level_min']}-{c['grade_level_max']}",
            "hours_per_week": c["hours_per_week"],
            "duration_weeks": c["duration_weeks"],
            "difficulty": c["difficulty"],
            "prerequisites": c.get("prerequisites", []),
            "tags": c.get("tags", []),
            "description": c.get("description", ""),
        })

    return json.dumps(results, indent=2)


def check_prerequisites(course_code: str, student_id: str) -> str:
    """Check if a student has completed prerequisites for a course.

    Returns JSON with met status and any missing prerequisites.
    """
    from db.queries import get_student_schedules

    # Get completed/active courses for the student
    all_schedules = get_student_schedules(student_id)
    completed_codes = [
        s.get("courses", {}).get("code", "")
        for s in all_schedules
        if s["status"] in ("active", "completed")
    ]

    try:
        from db.graph_queries import check_prerequisites_met
        result = check_prerequisites_met(course_code, completed_codes)
    except Exception:
        # Fallback if Neo4j is not available
        from db.queries import get_course_by_code
        course = get_course_by_code(course_code)
        if not course:
            return json.dumps({"error": f"Course {course_code} not found"})

        prereqs = course.get("prerequisites", [])
        missing = [p for p in prereqs if p not in completed_codes]
        result = {"met": len(missing) == 0, "missing": [{"code": m} for m in missing]}

    result["course_code"] = course_code
    result["student_completed_courses"] = completed_codes
    return json.dumps(result, indent=2)
