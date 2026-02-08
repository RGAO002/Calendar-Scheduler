"""Tool for detecting scheduling conflicts."""
from __future__ import annotations
import json
from datetime import time


def _parse_time(t) -> time:
    """Parse a time string or time object."""
    if isinstance(t, time):
        return t
    if isinstance(t, str):
        parts = t.split(":")
        return time(int(parts[0]), int(parts[1]))
    return t


def _times_overlap(s1, e1, s2, e2) -> bool:
    """Check if two time ranges overlap."""
    return s1 < e2 and s2 < e1


def detect_conflicts(
    student_id: str,
    proposed_day: int,
    proposed_start: str,
    proposed_end: str,
) -> str:
    """Check if a proposed time slot conflicts with existing schedule.

    Args:
        student_id: The student's UUID
        proposed_day: Day of week (0=Monday, 6=Sunday)
        proposed_start: Start time as "HH:MM"
        proposed_end: End time as "HH:MM"

    Returns JSON with conflict analysis including yes/no/maybe reasoning.
    """
    from db.queries import get_student_all_slots, get_student_availability

    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    proposed_s = _parse_time(proposed_start)
    proposed_e = _parse_time(proposed_end)

    # Check against existing schedule
    existing_slots = get_student_all_slots(student_id)
    conflicts = []
    for slot in existing_slots:
        if slot["day_of_week"] != proposed_day:
            continue
        slot_s = _parse_time(slot["start_time"])
        slot_e = _parse_time(slot["end_time"])
        if _times_overlap(proposed_s, proposed_e, slot_s, slot_e):
            conflicts.append({
                "course": f"{slot.get('course_code', '')} {slot.get('course_title', '')}",
                "time": f"{slot['start_time']}-{slot['end_time']}",
            })

    # Check against availability
    avail_slots = get_student_availability(student_id)
    day_avail = [a for a in avail_slots if a["day_of_week"] == proposed_day]

    is_within_availability = False
    preference = "unavailable"
    for a in day_avail:
        a_start = _parse_time(a["start_time"])
        a_end = _parse_time(a["end_time"])
        if a_start <= proposed_s and proposed_e <= a_end:
            is_within_availability = True
            preference = a.get("preference", "available")
            break

    # Build verdict with yes/no/maybe reasoning
    if conflicts:
        verdict = "NO"
        reason = f"Hard conflict with existing course(s): {', '.join(c['course'] for c in conflicts)}"
    elif not is_within_availability:
        verdict = "NO"
        reason = f"Proposed time is outside the student's availability on {day_names[proposed_day]}"
    elif preference == "avoid":
        verdict = "MAYBE"
        reason = f"Student prefers to avoid this time slot on {day_names[proposed_day]}"
    elif preference == "preferred":
        verdict = "YES"
        reason = f"Slot is available and in a preferred time window on {day_names[proposed_day]}"
    else:
        verdict = "YES"
        reason = f"Slot is available on {day_names[proposed_day]}"

    result = {
        "verdict": verdict,
        "reason": reason,
        "proposed": {
            "day": day_names[proposed_day],
            "start": proposed_start,
            "end": proposed_end,
        },
        "conflicts": conflicts,
        "within_availability": is_within_availability,
        "preference": preference,
    }

    return json.dumps(result, indent=2)
