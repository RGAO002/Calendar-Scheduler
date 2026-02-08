import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.components.sidebar import render_student_selector, get_selected_student_id, get_selected_student_name
from app.components.chat_interface import init_chat_state, render_chat_history, add_message, get_chat_input

st.set_page_config(page_title="Scheduler - Evlin", layout="wide")
st.title("🗓️ AI Scheduling Assistant")

student_id = render_student_selector()

if not student_id:
    st.info("Select a student from the sidebar to start scheduling.")
    st.stop()

student_name = get_selected_student_name()
st.markdown(f"Scheduling for **{student_name}**")
st.markdown("---")

# Layout: sidebar context + main chat
col_info, col_chat = st.columns([1, 2])

with col_info:
    st.subheader("📋 Current Info")
    try:
        from db.queries import get_student_schedules, get_student_availability

        # Current schedule
        schedules = get_student_schedules(student_id, status="active")
        st.markdown("**Active Courses:**")
        if schedules:
            for sch in schedules:
                course = sch.get("courses", {})
                st.write(f"- {course.get('code', '')} {course.get('title', '')}")
        else:
            st.write("None yet")

        # Availability summary
        st.markdown("**Availability:**")
        avail = get_student_availability(student_id)
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        avail_by_day = {}
        for a in avail:
            d = a["day_of_week"]
            if d not in avail_by_day:
                avail_by_day[d] = []
            avail_by_day[d].append(a)

        for d in sorted(avail_by_day.keys()):
            slots = avail_by_day[d]
            parts = [f"{s['start_time'][:5]}-{s['end_time'][:5]}" for s in slots]
            st.write(f"**{day_names[d]}:** {', '.join(parts)}")

    except Exception as e:
        st.error(f"Error loading context: {e}")

with col_chat:
    st.subheader("💬 Chat with Scheduler")

    # Initialize chat
    chat_key = f"scheduler_chat_{student_id}"
    init_chat_state(chat_key)

    # Welcome message
    if not st.session_state[chat_key]:
        welcome = (
            f"Hello! I'm the Evlin scheduling assistant. I'm here to help find the best "
            f"courses and time slots for {student_name}.\n\n"
            f"You can ask me things like:\n"
            f"- 'What science classes are available?'\n"
            f"- 'Can we fit a math class on Monday mornings?'\n"
            f"- 'Recommend a balanced schedule for this semester'\n\n"
            f"What would you like to do?"
        )
        add_message("assistant", welcome, chat_key)

    render_chat_history(chat_key)

    user_input = get_chat_input("Ask about scheduling...")

    if user_input:
        add_message("user", user_input, chat_key)
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    from agents.scheduler_agent import run_scheduler_agent

                    response = run_scheduler_agent(
                        messages=st.session_state[chat_key],
                        student_id=student_id,
                    )
                    st.markdown(response)
                    add_message("assistant", response, chat_key)
                except ImportError:
                    # Fallback if agent not yet configured
                    fallback = (
                        "The scheduling agent requires a Gemini API key to function. "
                        "Please add your `GEMINI_API_KEY` to the `.env` file.\n\n"
                        "In the meantime, you can browse courses on the Courses page."
                    )
                    st.markdown(fallback)
                    add_message("assistant", fallback, chat_key)
                except Exception as e:
                    error_msg = f"Agent error: {str(e)}"
                    st.error(error_msg)
                    add_message("assistant", error_msg, chat_key)
