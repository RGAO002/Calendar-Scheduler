"""Daily Check-In page for marking course sessions as completed."""
from __future__ import annotations

import streamlit as st
import sys
from pathlib import Path
from datetime import date, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.components.sidebar import render_student_selector

st.set_page_config(page_title="Daily Check-In - Evlin", layout="wide")
st.title("Daily Check-In")

student_id = render_student_selector()
st.markdown("---")

if not student_id:
    st.info("Select a student from the sidebar to start checking in.")
    st.stop()

# ── Auto-mark missed sessions on page load ───────────────
try:
    from db.queries import (
        mark_missed_sessions,
        get_sessions_for_date,
        get_unresolved_missed,
        check_in_session,
        find_available_reschedule_slots,
        reschedule_session,
        get_checkin_stats,
        get_student,
        get_student_schedules,
    )

    result = mark_missed_sessions(student_id, auto_reschedule=True)
    newly_missed = result.get("missed", [])
    auto_rescheduled = result.get("rescheduled", [])

    if newly_missed:
        n_missed = len(newly_missed)
        n_resched = len(auto_rescheduled)
        if n_resched > 0:
            st.toast(
                f"{n_missed} past session(s) marked as missed. "
                f"{n_resched} auto-rescheduled to the next available slot."
            )
        else:
            st.toast(f"{n_missed} past session(s) marked as missed.")

except Exception as e:
    st.error(f"Error connecting to database: {e}")
    st.stop()

# ── Student header ───────────────────────────────────────
student = get_student(student_id)
if student:
    st.markdown(f"### {student['first_name']} {student['last_name']} — Grade {student['grade_level']}")

# ── Auto-reschedule summary ─────────────────────────────
if auto_rescheduled:
    with st.expander(f"🔄 Auto-Rescheduled ({len(auto_rescheduled)} sessions)", expanded=True):
        for r in auto_rescheduled:
            old = r["missed_session"]
            old_date = old.get("session_date", "")
            old_start = str(old.get("start_time", ""))[:5]
            code_info = ""
            # Get course code from schedule lookup
            for sch in get_student_schedules(student_id, status="active"):
                if sch["id"] == old.get("schedule_id"):
                    code_info = sch.get("courses", {}).get("code", "")
                    break
            st.markdown(
                f"**{code_info}** {old_date} {old_start} → "
                f"**{r['new_date']}** {r['new_start']}–{r['new_end']}"
            )

# ── Date navigation ──────────────────────────────────────
col_prev, col_date, col_next = st.columns([1, 3, 1])

if "checkin_date" not in st.session_state:
    st.session_state.checkin_date = date.today()

with col_prev:
    if st.button("< Prev Day"):
        st.session_state.checkin_date -= timedelta(days=1)
        st.rerun()

with col_date:
    selected_date = st.date_input(
        "Date",
        value=st.session_state.checkin_date,
        label_visibility="collapsed",
    )
    if selected_date != st.session_state.checkin_date:
        st.session_state.checkin_date = selected_date
        st.rerun()

with col_next:
    if st.button("Next Day >"):
        st.session_state.checkin_date += timedelta(days=1)
        st.rerun()

current_date = st.session_state.checkin_date
day_name = current_date.strftime("%A")
is_today = current_date == date.today()
is_past = current_date < date.today()

date_label = f"**{day_name}, {current_date.strftime('%b %d, %Y')}**"
if is_today:
    date_label += " (Today)"
st.markdown(date_label)

# ── Today's Sessions ─────────────────────────────────────
st.markdown("---")
st.subheader("Today's Sessions" if is_today else f"Sessions for {current_date.strftime('%b %d')}")

SUBJECT_COLORS = {
    "Math": "#4A90D9", "Science": "#27AE60", "English": "#E67E22",
    "History": "#8E44AD", "Art": "#E74C3C", "PE": "#16A085",
}

STATUS_ICONS = {
    "pending": "⏳", "completed": "✅", "missed": "❌",
    "rescheduled": "🔄", "cancelled": "🚫",
}

sessions = get_sessions_for_date(student_id, current_date)

if not sessions:
    st.caption("No classes scheduled for this day.")
else:
    for i, session in enumerate(sessions):
        code = session.get("course_code", "")
        title = session.get("course_title", "")
        subject = session.get("subject", "")
        start = str(session.get("start_time", ""))[:5]
        end = str(session.get("end_time", ""))[:5]
        status = session.get("status", "pending")
        icon = STATUS_ICONS.get(status, "")
        color = SUBJECT_COLORS.get(subject, "#666")

        with st.container():
            col_info, col_action = st.columns([3, 1])

            with col_info:
                st.markdown(
                    f'<span style="color:{color};font-size:1.1em;font-weight:bold;">'
                    f'{start}–{end}  {code}</span><br/>'
                    f'<span style="color:#666;">{title}</span>',
                    unsafe_allow_html=True,
                )

            with col_action:
                if status == "pending":
                    if is_today or is_past:
                        if st.button(f"✅ Check In", key=f"checkin_{session['id']}"):
                            check_in_session(session["id"])
                            st.toast(f"Checked in: {code} {start}")
                            st.rerun()
                    else:
                        st.caption("⏳ Upcoming")
                elif status == "completed":
                    checked_at = session.get("checked_in_at", "")
                    if checked_at:
                        time_str = str(checked_at)[11:16]
                        st.success(f"✅ {time_str}")
                    else:
                        st.success("✅ Done")
                elif status == "missed":
                    st.error("❌ Missed")
                elif status == "rescheduled":
                    st.warning("🔄 Rescheduled")

            st.divider()

# ── Unresolved Missed Sessions ───────────────────────────
st.markdown("---")
missed = get_unresolved_missed(student_id)

if missed:
    st.subheader(f"⚠️ Missed Sessions ({len(missed)})")
    st.caption("These sessions were not checked in and need to be rescheduled or skipped.")

    for m in missed:
        code = m.get("course_code", "")
        title = m.get("course_title", "")
        m_date = m.get("session_date", "")
        start = str(m.get("start_time", ""))[:5]
        end = str(m.get("end_time", ""))[:5]

        with st.expander(f"❌ {m_date} — {code} {start}–{end}: {title}", expanded=False):
            # Show reschedule options
            candidates = find_available_reschedule_slots(student_id, m["id"])

            if candidates:
                st.markdown("**Suggested reschedule options:**")
                for j, c in enumerate(candidates):
                    label = f"{c['day_name']} {c['date']}  {c['start_time']}–{c['end_time']}"
                    pref = c.get("preference", "")
                    if pref == "preferred":
                        label += " ⭐"

                    if st.button(
                        f"📅 {label}",
                        key=f"resched_{m['id']}_{j}",
                    ):
                        reschedule_session(
                            m["id"], c["date"], c["start_time"], c["end_time"]
                        )
                        st.toast(f"Rescheduled {code} to {c['date']}")
                        st.rerun()
            else:
                st.caption("No available slots found in the next 7 days.")

            if st.button("Skip (don't reschedule)", key=f"skip_{m['id']}"):
                from services.supabase_client import get_supabase
                get_supabase().table("session_instances").update(
                    {"status": "cancelled"}
                ).eq("id", m["id"]).execute()
                st.toast(f"Skipped {code} on {m_date}")
                st.rerun()

# ── Weekly Progress Strip ────────────────────────────────
st.markdown("---")
st.subheader("📊 Weekly Progress")

week_start = current_date - timedelta(days=current_date.weekday())
day_labels = ["Mon", "Tue", "Wed", "Thu", "Fri"]
cols = st.columns(5)

for i, col in enumerate(cols):
    day = week_start + timedelta(days=i)
    day_sessions = get_sessions_for_date(student_id, day)

    with col:
        st.markdown(f"**{day_labels[i]}**")
        st.caption(day.strftime("%b %d"))

        if not day_sessions:
            st.markdown("—")
        elif all(s["status"] == "completed" for s in day_sessions):
            st.markdown("✅")
        elif any(s["status"] == "missed" for s in day_sessions):
            st.markdown("❌")
        elif day >= date.today():
            pending = sum(1 for s in day_sessions if s["status"] == "pending")
            st.markdown(f"⏳ {pending}")
        else:
            st.markdown("⏳")

# ── Statistics ───────────────────────────────────────────
st.markdown("---")
st.subheader("📈 Check-In Statistics")

stats = get_checkin_stats(student_id)

col1, col2, col3, col4 = st.columns(4)
with col1:
    rate = stats.get("completion_rate", 0)
    st.metric("Completion Rate", f"{rate:.0%}")
with col2:
    st.metric("Current Streak", f"{stats.get('streak', 0)} days")
with col3:
    wc = stats.get("week_completed", 0)
    wt = stats.get("week_total", 0)
    st.metric("This Week", f"{wc}/{wt}")
with col4:
    st.metric("Missed (Unresolved)", len(missed))

# ── Simulate Missed Day ─────────────────────────────────
st.markdown("---")
st.subheader("🧪 Simulate Missed Day")
st.caption(
    "Pick a date with completed sessions. Clicking the button will reset them "
    "to 'pending', then immediately run auto-reschedule so you can see the "
    "courses move to new dates."
)

from services.supabase_client import get_supabase as _get_sb

sim_col1, sim_col2 = st.columns([2, 3])

with sim_col1:
    sim_date = st.date_input(
        "Simulate date",
        value=date.today() - timedelta(days=1),
        max_value=date.today() - timedelta(days=1),
        key="sim_date",
    )

# Show what sessions exist on that date
sim_sessions = get_sessions_for_date(student_id, sim_date)
completed_on_day = [s for s in sim_sessions if s["status"] in ("completed", "missed")]
pending_on_day = [s for s in sim_sessions if s["status"] == "pending"]

with sim_col2:
    st.markdown(f"**{sim_date.strftime('%A, %b %d')}** — {len(sim_sessions)} sessions")
    for s in sim_sessions:
        icon = STATUS_ICONS.get(s["status"], "")
        st.caption(f"{icon} {str(s.get('start_time',''))[:5]} {s.get('course_code','')} — {s['status']}")

if not sim_sessions:
    st.info("No sessions on this date. Pick a date that has classes.")
elif not completed_on_day and not pending_on_day:
    st.info("No completed/pending sessions to simulate on this date.")
else:
    resettable = completed_on_day if completed_on_day else pending_on_day
    if st.button(
        f"⚡ Simulate: mark {len(resettable)} session(s) as missed & auto-reschedule",
        type="primary",
    ):
        sb = _get_sb()

        # Step 1: Reset to pending (so mark_missed_sessions can pick them up)
        for s in resettable:
            sb.table("session_instances").update({
                "status": "pending",
                "checked_in_at": None,
            }).eq("id", s["id"]).execute()

        # Step 2: Run auto-reschedule
        sim_result = mark_missed_sessions(student_id, auto_reschedule=True)
        sim_missed = sim_result.get("missed", [])
        sim_resched = sim_result.get("rescheduled", [])

        # Step 3: Show results
        if sim_resched:
            st.success(f"✅ {len(sim_missed)} session(s) marked missed → {len(sim_resched)} auto-rescheduled!")
            # Build a lookup for course codes
            schedules_lookup = {
                sch["id"]: sch.get("courses", {}).get("code", "")
                for sch in get_student_schedules(student_id, status="active")
            }
            for r in sim_resched:
                old = r["missed_session"]
                code = schedules_lookup.get(old.get("schedule_id", ""), "")
                st.markdown(
                    f"- **{code}** ~~{old.get('session_date','')} "
                    f"{str(old.get('start_time',''))[:5]}~~ → "
                    f"**{r['new_date']} {r['new_start']}–{r['new_end']}**"
                )
        elif sim_missed:
            st.warning(
                f"{len(sim_missed)} session(s) marked missed, but no available "
                f"slots found in the next 7 days to reschedule."
            )
        else:
            st.info("No sessions were affected.")

        st.info("Refresh the page or switch dates above to see the updated schedule.")
