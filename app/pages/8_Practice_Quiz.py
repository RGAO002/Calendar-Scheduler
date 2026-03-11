"""Practice Quiz page — generate interactive concept quizzes via LangGraph."""
from __future__ import annotations

import base64
import streamlit as st
import streamlit.components.v1 as components
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.components.sidebar import render_student_selector
from app.config import settings

st.set_page_config(page_title="Practice Quiz - Evlin", layout="wide")
st.title("Practice Quiz")

student_id = render_student_selector()
st.markdown("---")

if not student_id:
    st.info("Select a student from the sidebar to start.")
    st.stop()

# ── Imports ──
try:
    from db.queries import (
        get_student,
        get_student_schedules,
        get_quiz_session,
        get_quiz_history,
    )
except Exception as e:
    st.error(f"Database connection error: {e}")
    st.stop()

student = get_student(student_id)
student_grade = student["grade_level"] if student else 5

# ── Course selection ──
schedules = get_student_schedules(student_id, status="active")
if not schedules:
    st.warning("This student has no active courses. Enroll in a course first.")
    st.stop()

course_map = {}
for s in schedules:
    c = s.get("courses", {})
    if c and c.get("title"):
        course_map[c["title"]] = c

# Support query params for pre-filling from Check-In page
params = st.query_params
prefill_course = params.get("course", None)
prefill_topic = params.get("topic", "")

course_titles = list(course_map.keys())
default_idx = 0
if prefill_course:
    for i, title in enumerate(course_titles):
        if course_map[title].get("code") == prefill_course:
            default_idx = i
            break

selected_title = st.selectbox("Course", course_titles, index=default_idx)
course = course_map[selected_title]

# ── Topic + config ──
col1, col2 = st.columns([3, 1])
with col1:
    topic = st.text_input(
        "Topic / Concept",
        value=prefill_topic,
        placeholder="e.g. Adding fractions with unlike denominators",
    )
with col2:
    num_questions = st.number_input("Questions", min_value=3, max_value=15, value=5)

has_topic = bool(topic.strip())

# ── Resource buttons row ──
st.markdown("#### 📚 Learning Resources")
rc1, rc2, rc3 = st.columns(3)
with rc1:
    btn_video = st.button("📺 Find Videos", disabled=not has_topic, use_container_width=True)
with rc2:
    btn_image = st.button("🖼️ Explain with Images", disabled=not has_topic, use_container_width=True)
with rc3:
    btn_game = st.button("🎮 Generate Game", disabled=not has_topic, use_container_width=True)

# ── Handle: Find Videos (multiple options) ──
if btn_video:
    # Clear only video results
    st.session_state.pop("yt_videos", None)
    st.session_state.pop("yt_selected", None)
    with st.spinner("Searching YouTube..."):
        from services.youtube_search import search_edu_videos
        results = search_edu_videos(
            topic=topic.strip(),
            grade=student_grade,
            subject=course.get("subject", ""),
            top_n=3,
        )
        if results:
            st.session_state["yt_videos"] = results
        else:
            st.warning("No educational videos found. Try a different topic or check YOUTUBE_API_KEY in .env.")

if "yt_videos" in st.session_state:
    videos = st.session_state["yt_videos"]
    st.markdown("**📺 Choose a video:**")

    vid_cols = st.columns(len(videos))
    for i, vid in enumerate(videos):
        with vid_cols[i]:
            # Show thumbnail if available
            if vid.get("thumbnail"):
                st.image(vid["thumbnail"], use_container_width=True)
            st.caption(f"**{vid['title']}**")
            st.caption(f"🎥 {vid['channel']}")
            if st.button(f"▶ Watch", key=f"vid_{i}", use_container_width=True):
                st.session_state["yt_selected"] = vid

    # Display selected video
    if "yt_selected" in st.session_state:
        sel = st.session_state["yt_selected"]
        st.video(f"https://www.youtube.com/watch?v={sel['video_id']}")

# ── Handle: Generate Step-by-Step Images ──
if btn_image:
    # Clear only image results
    st.session_state.pop("concept_steps", None)
    with st.spinner("Generating step-by-step illustrations (this may take a minute)..."):
        from services.image_gen import generate_concept_images
        results = generate_concept_images(
            topic=topic.strip(),
            subject=course.get("subject", ""),
            grade=student_grade,
            num_steps=4,
        )
        if results:
            st.session_state["concept_steps"] = results
        else:
            st.warning("Image generation failed. Gemini Imagen may be temporarily unavailable.")

if "concept_steps" in st.session_state:
    steps = st.session_state["concept_steps"]
    st.markdown(f"**🖼️ {topic} — Step by Step**")

    for i, (label, img_b64) in enumerate(steps):
        img_bytes = base64.b64decode(img_b64)
        st.image(img_bytes, caption=label, use_container_width=True)

# ── Handle: Generate Game (placeholder) ──
if btn_game:
    st.info("🎮 Game generation coming soon! Godot-based educational mini-games are planned for a future release.")

# ── Quiz generation buttons ──
st.markdown("---")
st.markdown("#### 📝 Quiz")
col_btn1, col_btn2 = st.columns(2)
with col_btn1:
    generate_normal = st.button("🎯 Generate Quiz", type="primary", disabled=not has_topic)
with col_btn2:
    generate_surprise = st.button("✨ Surprise Me", disabled=not has_topic)

if generate_normal or generate_surprise:
    mode = "surprise" if generate_surprise else "template"
    spinner_text = "✨ Creating something unique..." if generate_surprise else "Generating quiz..."

    with st.spinner(spinner_text):
        try:
            from agents.quiz_graph import quiz_graph

            result = quiz_graph.invoke({
                "student_id": student_id,
                "course_id": course.get("id", ""),
                "course_title": course.get("title", ""),
                "subject": course.get("subject", ""),
                "grade": student_grade,
                "topic": topic.strip(),
                "num_questions": num_questions,
                "difficulty": "standard",
                "mode": mode,
                "supabase_url": settings.supabase_url,
                "supabase_key": settings.supabase_key,
                # initial state
                "concept": {},
                "video": {},
                "concept_image_b64": "",
                "animation_html": "",
                "questions": [],
                "quality_ok": False,
                "retry_count": 0,
                "quiz_id": "",
                "quiz_html": "",
                "error": None,
            })

            if result.get("error"):
                err = str(result["error"])
                if "PGRST205" in err:
                    st.error("⚠️ Quiz table not found. Please run `scripts/add_quiz_tables.sql` in the Supabase SQL editor first.")
                else:
                    st.error(f"Quiz generation failed: {err}")
            else:
                st.session_state["quiz_result"] = result
                st.session_state["quiz_id"] = result.get("quiz_id", "")
        except Exception as e:
            st.error(f"Error generating quiz: {e}")

# ── Render quiz ──
if "quiz_result" in st.session_state:
    result = st.session_state["quiz_result"]
    quiz_html = result.get("quiz_html", "")

    if quiz_html:
        components.html(quiz_html, height=800, scrolling=True)

        # Check if results have been saved
        col_r1, col_r2 = st.columns([1, 3])
        with col_r1:
            if st.button("🔄 Refresh Results"):
                st.rerun()

        quiz_id = st.session_state.get("quiz_id")
        if quiz_id:
            try:
                record = get_quiz_session(quiz_id)
            except Exception:
                record = None
            if record and record.get("status") == "completed":
                score = record.get("score", 0)
                total = record.get("total", 0)
                pct = round(score / total * 100) if total else 0
                with col_r2:
                    if pct >= 70:
                        st.success(f"Score: {score}/{total} ({pct}%)")
                    elif pct >= 40:
                        st.warning(f"Score: {score}/{total} ({pct}%)")
                    else:
                        st.error(f"Score: {score}/{total} ({pct}%)")

# ── Quiz History ──
st.markdown("---")
st.subheader("Quiz History")

try:
    history = get_quiz_history(student_id, limit=15)
except Exception:
    history = []
    st.warning("Quiz history table not found. Run `scripts/add_quiz_tables.sql` in the Supabase SQL editor.")
if not history:
    st.caption("No quizzes taken yet. Generate one above!")
else:
    for q in history:
        course_info = q.get("courses") or {}
        course_code = course_info.get("code", "")
        score_text = f"{q.get('score', '?')}/{q.get('total', '?')}" if q.get("status") == "completed" else "In progress"
        date_text = (q.get("created_at") or "")[:10]

        with st.expander(f"{q['topic']} — {score_text} ({date_text})"):
            cols = st.columns(3)
            cols[0].metric("Course", course_code or "N/A")
            cols[1].metric("Difficulty", q.get("difficulty", "standard"))
            cols[2].metric("Status", q.get("status", ""))
            if q.get("status") == "completed" and q.get("answers"):
                st.caption("Per-question results:")
                for ans in q["answers"]:
                    icon = "✅" if ans.get("isCorrect") else "❌"
                    st.text(f"  {icon} Q{ans.get('qid', '?')}: {ans.get('selected', 'skipped')} (correct: {ans.get('correct', '')})")
