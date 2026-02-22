"""Supabase CRUD operations for all tables."""
from __future__ import annotations
from typing import Optional
from uuid import UUID
from services.supabase_client import get_supabase


# ── Students ──────────────────────────────────────────────

def get_all_students() -> list[dict]:
    return get_supabase().table("students").select("*").order("first_name").execute().data


def get_student(student_id: str) -> Optional[dict]:
    resp = get_supabase().table("students").select("*").eq("id", student_id).execute()
    return resp.data[0] if resp.data else None


def insert_student(data: dict) -> dict:
    return get_supabase().table("students").insert(data).execute().data[0]


# ── Courses ───────────────────────────────────────────────

def get_all_courses(active_only: bool = True) -> list[dict]:
    q = get_supabase().table("courses").select("*")
    if active_only:
        q = q.eq("is_active", True)
    return q.order("subject").order("code").execute().data


def get_course(course_id: str) -> Optional[dict]:
    resp = get_supabase().table("courses").select("*").eq("id", course_id).execute()
    return resp.data[0] if resp.data else None


def get_course_by_code(code: str) -> Optional[dict]:
    resp = get_supabase().table("courses").select("*").eq("code", code).execute()
    return resp.data[0] if resp.data else None


def search_courses(
    subject: Optional[str] = None,
    grade_level: Optional[int] = None,
    difficulty: Optional[str] = None,
) -> list[dict]:
    q = get_supabase().table("courses").select("*").eq("is_active", True)
    if subject:
        q = q.eq("subject", subject)
    if grade_level:
        q = q.lte("grade_level_min", grade_level).gte("grade_level_max", grade_level)
    if difficulty:
        q = q.eq("difficulty", difficulty)
    return q.order("code").execute().data


def insert_course(data: dict) -> dict:
    return get_supabase().table("courses").insert(data).execute().data[0]


# ── Availability ──────────────────────────────────────────

def get_student_availability(student_id: str) -> list[dict]:
    return (
        get_supabase()
        .table("availability")
        .select("*")
        .eq("student_id", student_id)
        .order("day_of_week")
        .order("start_time")
        .execute()
        .data
    )


def insert_availability(data: dict) -> dict:
    return get_supabase().table("availability").insert(data).execute().data[0]


# ── Schedules ─────────────────────────────────────────────

def get_student_schedules(student_id: str, status: Optional[str] = None) -> list[dict]:
    q = (
        get_supabase()
        .table("schedules")
        .select("*, courses(*)")
        .eq("student_id", student_id)
    )
    if status:
        q = q.eq("status", status)
    return q.order("start_date").execute().data


def get_schedule(schedule_id: str) -> Optional[dict]:
    resp = (
        get_supabase()
        .table("schedules")
        .select("*, courses(*), schedule_slots(*)")
        .eq("id", schedule_id)
        .execute()
    )
    return resp.data[0] if resp.data else None


def insert_schedule(data: dict) -> dict:
    return get_supabase().table("schedules").insert(data).execute().data[0]


def update_schedule_status(schedule_id: str, status: str) -> dict:
    return (
        get_supabase()
        .table("schedules")
        .update({"status": status})
        .eq("id", schedule_id)
        .execute()
        .data[0]
    )


# ── Schedule Slots ────────────────────────────────────────

def get_schedule_slots(schedule_id: str) -> list[dict]:
    return (
        get_supabase()
        .table("schedule_slots")
        .select("*")
        .eq("schedule_id", schedule_id)
        .order("day_of_week")
        .order("start_time")
        .execute()
        .data
    )


def get_student_all_slots(student_id: str) -> list[dict]:
    """Get all schedule slots for a student across all active schedules."""
    schedules = get_student_schedules(student_id, status="active")
    all_slots = []
    for sch in schedules:
        slots = get_schedule_slots(sch["id"])
        for s in slots:
            s["course_title"] = sch.get("courses", {}).get("title", "")
            s["course_code"] = sch.get("courses", {}).get("code", "")
        all_slots.extend(slots)
    return all_slots


def insert_schedule_slot(data: dict) -> dict:
    return get_supabase().table("schedule_slots").insert(data).execute().data[0]


# ── Generated PDFs ────────────────────────────────────────

def get_generated_pdfs(student_id: Optional[str] = None, limit: int = 20) -> list[dict]:
    q = get_supabase().table("generated_pdfs").select("*")
    if student_id:
        q = q.eq("student_id", student_id)
    return q.order("created_at", desc=True).limit(limit).execute().data


def insert_generated_pdf(data: dict) -> dict:
    return get_supabase().table("generated_pdfs").insert(data).execute().data[0]


# ── OCR Documents ─────────────────────────────────────────

def get_ocr_documents(limit: int = 20) -> list[dict]:
    return (
        get_supabase()
        .table("ocr_documents")
        .select("*")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
        .data
    )


def insert_ocr_document(data: dict) -> dict:
    return get_supabase().table("ocr_documents").insert(data).execute().data[0]


def update_ocr_document(doc_id: str, data: dict) -> dict:
    return (
        get_supabase()
        .table("ocr_documents")
        .update(data)
        .eq("id", doc_id)
        .execute()
        .data[0]
    )


# ── Agent Conversations ──────────────────────────────────

def get_conversations(student_id: str, agent_type: str) -> list[dict]:
    return (
        get_supabase()
        .table("agent_conversations")
        .select("*")
        .eq("student_id", student_id)
        .eq("agent_type", agent_type)
        .order("updated_at", desc=True)
        .execute()
        .data
    )


def upsert_conversation(data: dict) -> dict:
    return get_supabase().table("agent_conversations").upsert(data).execute().data[0]


# ── Session Instances (Check-In / 打卡) ─────────────────

def generate_session_instances(schedule_id: str, start_date, end_date) -> list[dict]:
    """Expand weekly template slots into concrete dated session instances.

    For each schedule_slot, creates one session_instance row per week
    between start_date and end_date.
    """
    from datetime import date as _date, timedelta

    if isinstance(start_date, str):
        start_date = _date.fromisoformat(start_date)
    if isinstance(end_date, str):
        end_date = _date.fromisoformat(end_date)

    slots = get_schedule_slots(schedule_id)
    if not slots:
        return []

    sb = get_supabase()
    all_instances = []

    # Find the Monday of the week containing start_date
    week_start = start_date - timedelta(days=start_date.weekday())

    for slot in slots:
        dow = slot["day_of_week"]
        current = week_start + timedelta(days=dow)

        while current <= end_date:
            if current >= start_date:
                instance = {
                    "schedule_id": schedule_id,
                    "schedule_slot_id": slot["id"],
                    "session_date": str(current),
                    "start_time": str(slot["start_time"])[:5],
                    "end_time": str(slot["end_time"])[:5],
                    "status": "pending",
                }
                all_instances.append(instance)
            current += timedelta(weeks=1)

    if all_instances:
        result = sb.table("session_instances").upsert(
            all_instances, on_conflict="schedule_slot_id,session_date"
        ).execute()
        return result.data

    return []


def get_sessions_for_date(student_id: str, target_date) -> list[dict]:
    """Get all session instances for a student on a specific date, with course info."""
    from datetime import date as _date
    if isinstance(target_date, str):
        target_date = _date.fromisoformat(target_date)

    schedules = get_student_schedules(student_id, status="active")
    if not schedules:
        return []

    schedule_ids = [s["id"] for s in schedules]
    # Build course lookup
    course_lookup = {}
    for s in schedules:
        course_lookup[s["id"]] = s.get("courses", {})

    sb = get_supabase()
    all_sessions = []
    for sid in schedule_ids:
        resp = (
            sb.table("session_instances")
            .select("*")
            .eq("schedule_id", sid)
            .eq("session_date", str(target_date))
            .order("start_time")
            .execute()
        )
        for row in resp.data:
            course = course_lookup.get(row["schedule_id"], {})
            row["course_code"] = course.get("code", "")
            row["course_title"] = course.get("title", "")
            row["subject"] = course.get("subject", "")
            all_sessions.append(row)

    all_sessions.sort(key=lambda x: str(x.get("start_time", "")))
    return all_sessions


def get_sessions_for_range(student_id: str, start_date, end_date) -> list[dict]:
    """Get all sessions in a date range for the calendar view."""
    from datetime import date as _date
    if isinstance(start_date, str):
        start_date = _date.fromisoformat(start_date)
    if isinstance(end_date, str):
        end_date = _date.fromisoformat(end_date)

    schedules = get_student_schedules(student_id, status="active")
    if not schedules:
        return []

    course_lookup = {}
    for s in schedules:
        course_lookup[s["id"]] = s.get("courses", {})

    sb = get_supabase()
    all_sessions = []
    for sch in schedules:
        resp = (
            sb.table("session_instances")
            .select("*")
            .eq("schedule_id", sch["id"])
            .gte("session_date", str(start_date))
            .lte("session_date", str(end_date))
            .order("session_date")
            .order("start_time")
            .execute()
        )
        for row in resp.data:
            course = course_lookup.get(row["schedule_id"], {})
            row["course_code"] = course.get("code", "")
            row["course_title"] = course.get("title", "")
            row["subject"] = course.get("subject", "")
            all_sessions.append(row)

    return all_sessions


def get_pending_sessions_today(student_id: str) -> list[dict]:
    """Get sessions with status='pending' for today."""
    from datetime import date as _date
    today = _date.today()
    sessions = get_sessions_for_date(student_id, today)
    return [s for s in sessions if s.get("status") == "pending"]


def check_in_session(session_id: str, notes: str = None) -> dict:
    """Mark a session as completed (打卡)."""
    from datetime import datetime, timezone
    sb = get_supabase()
    now = datetime.now(timezone.utc).isoformat()

    result = (
        sb.table("session_instances")
        .update({"status": "completed", "checked_in_at": now, "notes": notes})
        .eq("id", session_id)
        .execute()
    )

    # Log the action
    sb.table("checkin_log").insert({
        "session_instance_id": session_id,
        "action": "check_in",
        "performed_by": "parent",
        "details": {"notes": notes} if notes else {},
    }).execute()

    return result.data[0] if result.data else {}


def mark_missed_sessions(
    student_id: str = None, auto_reschedule: bool = True
) -> dict:
    """Auto-mark past pending sessions as 'missed', optionally auto-reschedule.

    Called on page load to catch any sessions that weren't checked in.
    If student_id is provided, only marks that student's sessions.
    If auto_reschedule is True, each missed session is automatically rescheduled
    to the earliest available slot (within 7 days).

    Returns dict with 'missed' and 'rescheduled' lists.
    """
    from datetime import date as _date
    sb = get_supabase()
    today = str(_date.today())

    q = (
        sb.table("session_instances")
        .select("*")
        .eq("status", "pending")
        .lt("session_date", today)
    )

    if student_id:
        # Filter by student's schedule IDs
        schedules = get_student_schedules(student_id, status="active")
        schedule_ids = [s["id"] for s in schedules]
        if not schedule_ids:
            return {"missed": [], "rescheduled": []}
        q = q.in_("schedule_id", schedule_ids)

    pending_past = q.execute().data

    missed = []
    rescheduled = []
    for session in pending_past:
        sb.table("session_instances").update(
            {"status": "missed"}
        ).eq("id", session["id"]).execute()

        sb.table("checkin_log").insert({
            "session_instance_id": session["id"],
            "action": "auto_miss",
            "performed_by": "system",
        }).execute()

        session["status"] = "missed"
        missed.append(session)

        # Auto-reschedule: pick the best available slot
        if auto_reschedule and student_id:
            try:
                candidates = find_available_reschedule_slots(
                    student_id, session["id"], days_ahead=7
                )
                if candidates:
                    best = candidates[0]  # first = highest preference, earliest date
                    new_inst = reschedule_session(
                        session["id"], best["date"], best["start_time"], best["end_time"]
                    )
                    if new_inst and "error" not in new_inst:
                        # Update the log entry to reflect auto-reschedule
                        sb.table("checkin_log").insert({
                            "session_instance_id": session["id"],
                            "action": "reschedule",
                            "performed_by": "system",
                            "details": {
                                "auto": True,
                                "new_date": best["date"],
                                "new_time": f"{best['start_time']}–{best['end_time']}",
                            },
                        }).execute()
                        rescheduled.append({
                            "missed_session": session,
                            "new_date": best["date"],
                            "new_start": best["start_time"],
                            "new_end": best["end_time"],
                            "new_session_id": new_inst.get("id"),
                        })
            except Exception:
                pass  # reschedule failure shouldn't block marking as missed

    return {"missed": missed, "rescheduled": rescheduled}


def get_unresolved_missed(student_id: str) -> list[dict]:
    """Get missed sessions that haven't been rescheduled yet."""
    schedules = get_student_schedules(student_id, status="active")
    if not schedules:
        return []

    course_lookup = {}
    for s in schedules:
        course_lookup[s["id"]] = s.get("courses", {})

    sb = get_supabase()
    all_missed = []
    for sch in schedules:
        resp = (
            sb.table("session_instances")
            .select("*")
            .eq("schedule_id", sch["id"])
            .eq("status", "missed")
            .is_("rescheduled_to", "null")
            .order("session_date")
            .execute()
        )
        for row in resp.data:
            course = course_lookup.get(row["schedule_id"], {})
            row["course_code"] = course.get("code", "")
            row["course_title"] = course.get("title", "")
            row["subject"] = course.get("subject", "")
            all_missed.append(row)

    return all_missed


def find_available_reschedule_slots(
    student_id: str, missed_session_id: str, days_ahead: int = 7
) -> list[dict]:
    """Find available dates/times to reschedule a missed session.

    Returns up to 5 candidate slots sorted by preference.
    """
    from datetime import date as _date, timedelta, time as _time

    sb = get_supabase()
    session = sb.table("session_instances").select("*").eq("id", missed_session_id).execute()
    if not session.data:
        return []
    missed = session.data[0]

    # Session duration
    start_parts = str(missed["start_time"])[:5].split(":")
    end_parts = str(missed["end_time"])[:5].split(":")
    start_t = _time(int(start_parts[0]), int(start_parts[1]))
    end_t = _time(int(end_parts[0]), int(end_parts[1]))
    duration_min = (int(end_parts[0]) * 60 + int(end_parts[1])) - (int(start_parts[0]) * 60 + int(start_parts[1]))

    today = _date.today()
    tomorrow = today + timedelta(days=1)
    end_search = today + timedelta(days=days_ahead)

    # Student availability
    avail = get_student_availability(student_id)
    avail_by_dow = {}
    for a in avail:
        dow = a["day_of_week"]
        if dow not in avail_by_dow:
            avail_by_dow[dow] = []
        avail_by_dow[dow].append(a)

    # Existing sessions in the search range
    existing = get_sessions_for_range(student_id, tomorrow, end_search)
    existing_by_date = {}
    for e in existing:
        d = e["session_date"]
        if d not in existing_by_date:
            existing_by_date[d] = []
        existing_by_date[d].append(e)

    candidates = []
    current = tomorrow
    while current <= end_search:
        dow = current.weekday()
        if dow not in avail_by_dow:
            current += timedelta(days=1)
            continue

        day_existing = existing_by_date.get(str(current), [])

        for window in avail_by_dow[dow]:
            w_start = str(window["start_time"])[:5]
            w_end = str(window["end_time"])[:5]
            w_s_min = int(w_start[:2]) * 60 + int(w_start[3:5])
            w_e_min = int(w_end[:2]) * 60 + int(w_end[3:5])

            if w_e_min - w_s_min < duration_min:
                continue

            # Try placing at window start
            candidate_start = w_s_min
            candidate_end = candidate_start + duration_min

            # Check for conflicts
            conflict = False
            for ex in day_existing:
                ex_s = str(ex["start_time"])[:5]
                ex_e = str(ex["end_time"])[:5]
                ex_s_min = int(ex_s[:2]) * 60 + int(ex_s[3:5])
                ex_e_min = int(ex_e[:2]) * 60 + int(ex_e[3:5])
                if candidate_start < ex_e_min and ex_s_min < candidate_end:
                    conflict = True
                    break

            if not conflict and candidate_end <= w_e_min:
                candidates.append({
                    "date": str(current),
                    "day_name": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][dow],
                    "start_time": f"{candidate_start // 60:02d}:{candidate_start % 60:02d}",
                    "end_time": f"{candidate_end // 60:02d}:{candidate_end % 60:02d}",
                    "preference": window.get("preference", "available"),
                    "same_dow": dow == missed.get("session_date", ""),
                })

        current += timedelta(days=1)

    # Sort: preferred > available, then earliest date
    pref_order = {"preferred": 0, "available": 1, "avoid": 2}
    candidates.sort(key=lambda c: (pref_order.get(c["preference"], 9), c["date"]))

    return candidates[:5]


def reschedule_session(
    missed_session_id: str, new_date: str, new_start: str, new_end: str
) -> dict:
    """Create a new session instance to replace a missed one."""
    sb = get_supabase()

    # Get the missed session
    missed = sb.table("session_instances").select("*").eq("id", missed_session_id).execute()
    if not missed.data:
        return {"error": "Session not found"}
    missed = missed.data[0]

    # Create new instance
    from datetime import date as _date
    new_d = _date.fromisoformat(new_date)
    new_instance = sb.table("session_instances").insert({
        "schedule_id": missed["schedule_id"],
        "schedule_slot_id": missed["schedule_slot_id"],
        "session_date": new_date,
        "start_time": new_start,
        "end_time": new_end,
        "status": "pending",
        "rescheduled_from": missed_session_id,
    }).execute().data[0]

    # Update missed session to point to new one
    sb.table("session_instances").update({
        "status": "rescheduled",
        "rescheduled_to": new_instance["id"],
    }).eq("id", missed_session_id).execute()

    # Log
    sb.table("checkin_log").insert({
        "session_instance_id": missed_session_id,
        "action": "reschedule",
        "performed_by": "parent",
        "details": {"new_session_id": new_instance["id"], "new_date": new_date},
    }).execute()

    return new_instance


def get_checkin_stats(student_id: str) -> dict:
    """Return check-in completion statistics."""
    from datetime import date as _date, timedelta

    schedules = get_student_schedules(student_id, status="active")
    if not schedules:
        return {
            "total": 0, "completed": 0, "missed": 0,
            "pending": 0, "rescheduled": 0,
            "completion_rate": 0.0, "streak": 0,
        }

    sb = get_supabase()
    today = _date.today()

    # All sessions up to and including today
    all_sessions = []
    for sch in schedules:
        resp = (
            sb.table("session_instances")
            .select("*")
            .eq("schedule_id", sch["id"])
            .lte("session_date", str(today))
            .order("session_date", desc=True)
            .execute()
        )
        all_sessions.extend(resp.data)

    total = len(all_sessions)
    completed = sum(1 for s in all_sessions if s["status"] == "completed")
    missed = sum(1 for s in all_sessions if s["status"] == "missed")
    rescheduled = sum(1 for s in all_sessions if s["status"] == "rescheduled")
    pending = sum(1 for s in all_sessions if s["status"] == "pending")

    # Completion rate (exclude pending today)
    past_total = total - pending
    completion_rate = completed / past_total if past_total > 0 else 0.0

    # Current streak: consecutive days with all sessions completed
    streak = 0
    check_date = today - timedelta(days=1)  # Start from yesterday
    while True:
        day_sessions = [s for s in all_sessions if s["session_date"] == str(check_date)]
        if not day_sessions:
            # No sessions on this day, skip (weekends etc.)
            check_date -= timedelta(days=1)
            if check_date < today - timedelta(days=30):
                break
            continue
        if all(s["status"] == "completed" for s in day_sessions):
            streak += 1
            check_date -= timedelta(days=1)
        else:
            break

    # This week stats
    week_start = today - timedelta(days=today.weekday())
    week_sessions = [s for s in all_sessions if s["session_date"] >= str(week_start)]
    week_completed = sum(1 for s in week_sessions if s["status"] == "completed")
    week_total = len(week_sessions)

    return {
        "total": total,
        "completed": completed,
        "missed": missed,
        "rescheduled": rescheduled,
        "pending": pending,
        "completion_rate": completion_rate,
        "streak": streak,
        "week_completed": week_completed,
        "week_total": week_total,
    }
