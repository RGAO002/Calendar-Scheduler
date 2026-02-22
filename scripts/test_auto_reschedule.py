"""Test script for auto-reschedule functionality.

Usage:
    python scripts/test_auto_reschedule.py

What it does:
1. Picks a student
2. Finds 2 past sessions that are already 'completed' or 'missed'
3. Resets them to 'pending' (simulating "forgot to check in")
4. Calls mark_missed_sessions(auto_reschedule=True)
5. Shows which sessions were auto-missed and auto-rescheduled

After running this, open the Daily Check-In page to see the results.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import date, timedelta
from services.supabase_client import get_supabase
from db.queries import (
    get_all_students,
    get_student_schedules,
    mark_missed_sessions,
)


def main() -> None:
    sb = get_supabase()
    today = date.today()

    # Pick first student
    students = get_all_students()
    if not students:
        print("No students found. Run seed_data.py first.")
        return

    student = students[0]
    sid = student["id"]
    print(f"Student: {student['first_name']} {student['last_name']} ({sid})")

    # Find past sessions (completed or missed) to reset to 'pending'
    # This avoids unique-constraint issues since the date stays the same
    schedules = get_student_schedules(sid, status="active")
    schedule_ids = [s["id"] for s in schedules]
    if not schedule_ids:
        print("No active schedules.")
        return

    past_sessions = []
    for sch_id in schedule_ids:
        resp = (
            sb.table("session_instances")
            .select("*")
            .eq("schedule_id", sch_id)
            .in_("status", ["completed", "missed"])
            .lt("session_date", str(today))
            .is_("rescheduled_to", "null")
            .order("session_date", desc=True)
            .limit(3)
            .execute()
        )
        past_sessions.extend(resp.data)

    if len(past_sessions) < 2:
        print(f"Only {len(past_sessions)} past non-rescheduled sessions found. Need at least 2.")
        print("Run seed_data.py first to generate historical data.")
        return

    # Reset 2 past sessions back to 'pending'
    test_sessions = past_sessions[:2]
    print(f"\n--- Resetting {len(test_sessions)} past sessions to 'pending' ---")
    for s in test_sessions:
        print(f"  ID:   {s['id']}")
        print(f"  Date: {s['session_date']}  {str(s['start_time'])[:5]}-{str(s['end_time'])[:5]}")
        print(f"  Was:  {s['status']}")
        sb.table("session_instances").update({
            "status": "pending",
            "checked_in_at": None,
        }).eq("id", s["id"]).execute()
        print(f"  Now:  pending")

    # Now call mark_missed_sessions with auto_reschedule=True
    print(f"\n--- Calling mark_missed_sessions(auto_reschedule=True) ---")
    result = mark_missed_sessions(sid, auto_reschedule=True)

    missed = result.get("missed", [])
    rescheduled = result.get("rescheduled", [])

    print(f"\nResults:")
    print(f"  Missed:           {len(missed)}")
    for m in missed:
        print(f"    {m['session_date']} {str(m['start_time'])[:5]} -> status={m['status']}")

    print(f"  Auto-rescheduled: {len(rescheduled)}")
    for r in rescheduled:
        old = r["missed_session"]
        print(
            f"    {old['session_date']} {str(old['start_time'])[:5]} "
            f"-> {r['new_date']} {r['new_start']}-{r['new_end']}"
        )

    if rescheduled:
        print("\n✅ Auto-reschedule is working!")
        print("Open Daily Check-In page in Streamlit to see the summary banner.")
    elif missed:
        print("\n⚠️  Sessions were marked missed but no reschedule slots found.")
        print("This means no available time windows in the next 7 days.")
    else:
        print("\n❌ No sessions were processed.")


if __name__ == "__main__":
    main()
