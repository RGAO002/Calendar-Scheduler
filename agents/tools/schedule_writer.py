"""Tools for writing and confirming schedules."""
from __future__ import annotations
import json
from datetime import date, timedelta


def propose_schedule(
    student_id: str,
    course_code: str,
    slots: list[dict],
    duration_weeks: int = 12,
) -> str:
    """Create a proposed schedule for a student.

    Args:
        student_id: Student UUID
        course_code: Course code (e.g., "MATH-5A")
        slots: List of time slots, each with day_of_week (0-6), start_time, end_time
        duration_weeks: How many weeks the course runs

    Returns JSON with the created schedule.
    """
    from db.queries import get_course_by_code, insert_schedule, insert_schedule_slot

    course = get_course_by_code(course_code)
    if not course:
        return json.dumps({"error": f"Course '{course_code}' not found"})

    today = date.today()
    start = today - timedelta(days=today.weekday())  # Next Monday
    if today.weekday() > 0:
        start += timedelta(weeks=1)
    end = start + timedelta(weeks=duration_weeks)

    schedule = insert_schedule({
        "student_id": student_id,
        "course_id": course["id"],
        "status": "proposed",
        "start_date": str(start),
        "end_date": str(end),
    })

    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    created_slots = []
    for s in slots:
        slot = insert_schedule_slot({
            "schedule_id": schedule["id"],
            "day_of_week": s["day_of_week"],
            "start_time": s["start_time"],
            "end_time": s["end_time"],
            "location": s.get("location", "Home"),
        })
        created_slots.append({
            "day": day_names[s["day_of_week"]],
            "start": s["start_time"],
            "end": s["end_time"],
        })

    result = {
        "status": "proposed",
        "schedule_id": schedule["id"],
        "course": f"{course['code']} - {course['title']}",
        "start_date": str(start),
        "end_date": str(end),
        "slots": created_slots,
        "message": "Schedule proposed! Ask the parent to confirm.",
    }

    return json.dumps(result, indent=2)


def confirm_schedule(schedule_id: str) -> str:
    """Confirm a proposed schedule, making it active.

    Args:
        schedule_id: UUID of the schedule to confirm

    Returns JSON with updated schedule status.
    """
    from db.queries import update_schedule_status, get_schedule, generate_session_instances

    try:
        update_schedule_status(schedule_id, "active")
        schedule = get_schedule(schedule_id)

        # Generate concrete session instances for check-in tracking
        if schedule.get("start_date") and schedule.get("end_date"):
            try:
                instances = generate_session_instances(
                    schedule_id, schedule["start_date"], schedule["end_date"]
                )
                instance_count = len(instances) if instances else 0
            except Exception:
                instance_count = 0
        else:
            instance_count = 0

        course = schedule.get("courses", {})
        return json.dumps({
            "status": "confirmed",
            "schedule_id": schedule_id,
            "course": f"{course.get('code', '')} - {course.get('title', '')}",
            "sessions_created": instance_count,
            "message": f"Schedule confirmed and now active! {instance_count} class sessions created for check-in tracking.",
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})
