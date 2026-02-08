"""Tools for checking student availability and current schedule."""
from __future__ import annotations
import json


def get_student_availability(student_id: str) -> str:
    """Get weekly availability slots for a student.

    Returns JSON string with availability organized by day.
    """
    from db.queries import get_student_availability as _get_avail

    slots = _get_avail(student_id)
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    organized = {}
    for s in slots:
        day = day_names[s["day_of_week"]]
        if day not in organized:
            organized[day] = []
        organized[day].append({
            "start": str(s["start_time"])[:5],
            "end": str(s["end_time"])[:5],
            "preference": s.get("preference", "available"),
        })

    return json.dumps(organized, indent=2)


def get_current_schedule(student_id: str) -> str:
    """Get the student's current active schedule with time slots.

    Returns JSON string with active courses and their weekly time slots.
    """
    from db.queries import get_student_schedules, get_schedule_slots

    schedules = get_student_schedules(student_id, status="active")
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    result = []
    for sch in schedules:
        course = sch.get("courses", {})
        slots = get_schedule_slots(sch["id"])

        slot_list = []
        for s in slots:
            slot_list.append({
                "day": day_names[s["day_of_week"]],
                "start": str(s["start_time"])[:5],
                "end": str(s["end_time"])[:5],
                "location": s.get("location", "Home"),
            })

        result.append({
            "schedule_id": sch["id"],
            "course_code": course.get("code", ""),
            "course_title": course.get("title", ""),
            "subject": course.get("subject", ""),
            "hours_per_week": course.get("hours_per_week", 0),
            "status": sch["status"],
            "slots": slot_list,
        })

    return json.dumps(result, indent=2)
