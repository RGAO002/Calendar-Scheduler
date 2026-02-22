"""Tools for the scheduling agent to query and manage check-in (打卡) data."""
from __future__ import annotations
import json
from datetime import date


def get_pending_sessions(student_id: str, target_date: str | None = None) -> str:
    """Get pending (unchecked) sessions for a student on a given date.

    Args:
        student_id: Student UUID
        target_date: ISO date string (YYYY-MM-DD). Defaults to today.

    Returns JSON list of pending sessions.
    """
    from db.queries import get_sessions_for_date

    d = date.fromisoformat(target_date) if target_date else date.today()
    sessions = get_sessions_for_date(student_id, d)
    pending = [s for s in sessions if s.get("status") == "pending"]

    if not pending:
        return json.dumps({"message": f"No pending sessions for {d.isoformat()}.", "sessions": []})

    result = []
    for s in pending:
        result.append({
            "session_id": s["id"],
            "course_code": s.get("course_code", ""),
            "course_title": s.get("course_title", ""),
            "start_time": str(s.get("start_time", ""))[:5],
            "end_time": str(s.get("end_time", ""))[:5],
            "status": s["status"],
        })

    return json.dumps({"date": d.isoformat(), "pending_count": len(result), "sessions": result}, indent=2)


def agent_check_in_session(session_id: str) -> str:
    """Check in (打卡) a session, marking it as completed.

    Args:
        session_id: UUID of the session instance to check in.

    Returns JSON confirmation.
    """
    from db.queries import check_in_session

    try:
        updated = check_in_session(session_id)
        return json.dumps({
            "status": "success",
            "session_id": session_id,
            "message": f"Checked in! {updated.get('course_code', '')} marked as completed.",
        }, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


def suggest_reschedule(student_id: str, missed_session_id: str) -> str:
    """Find available reschedule options for a missed session.

    Args:
        student_id: Student UUID
        missed_session_id: UUID of the missed session instance.

    Returns JSON list of suggested reschedule slots.
    """
    from db.queries import find_available_reschedule_slots

    try:
        candidates = find_available_reschedule_slots(student_id, missed_session_id)
        if not candidates:
            return json.dumps({"message": "No available reschedule slots found in the next 7 days.", "options": []})

        options = []
        for c in candidates:
            label = f"{c['day_name']} {c['date']}  {c['start_time']}–{c['end_time']}"
            pref = c.get("preference", "")
            options.append({
                "date": c["date"],
                "day_name": c["day_name"],
                "start_time": c["start_time"],
                "end_time": c["end_time"],
                "preference": pref,
                "label": label + (" ⭐" if pref == "preferred" else ""),
            })

        return json.dumps({
            "missed_session_id": missed_session_id,
            "options_count": len(options),
            "options": options,
        }, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})
