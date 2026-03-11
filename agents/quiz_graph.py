"""LangGraph-based quiz generation agent.

Nodes:
  generate_concept    → Gemini produces concept explanation JSON
  search_video        → YouTube Data API finds best K-8 educational video
  generate_image      → Gemini Imagen generates concept illustration
  generate_animation  → Gemini produces JSON scene script for canvas animation
  generate_questions  → Gemini produces quiz questions JSON
  quality_check       → validates question count, format, answers
  build_html          → combines video + image + animation + quiz into HTML
  save_to_db          → persists to Supabase quiz_sessions table

Flow:
  concept → search_video → generate_image → generate_animation
  → generate_questions → quality_check →(retry?)→ build_html → save_to_db
"""
from __future__ import annotations

import json
import logging
from typing import Any, Literal, TypedDict

from google import genai
from google.genai import types
from langgraph.graph import END, StateGraph

from app.config import settings

log = logging.getLogger(__name__)


# ── State ──────────────────────────────────────────────────


class QuizState(TypedDict):
    # inputs
    student_id: str
    course_id: str
    course_title: str
    subject: str
    grade: int
    topic: str
    num_questions: int
    difficulty: str
    mode: str  # "template" | "surprise"
    supabase_url: str
    supabase_key: str
    # intermediate
    concept: dict
    video: dict          # {video_id, title, channel, thumbnail} or {}
    concept_image_b64: str  # base64 JPEG or ""
    animation_html: str
    questions: list[dict]
    quality_ok: bool
    retry_count: int
    # outputs
    quiz_id: str
    quiz_html: str
    error: str | None


# ── Helpers ────────────────────────────────────────────────


def _gemini_json(prompt: str, temperature: float = 0.8) -> dict:
    """Call Gemini and parse JSON response."""
    client = genai.Client(api_key=settings.gemini_api_key)
    resp = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=temperature,
            response_mime_type="application/json",
        ),
    )
    text = resp.text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        text = text.rsplit("```", 1)[0]
    return json.loads(text)


def _gemini_text(prompt: str, temperature: float = 0.9) -> str:
    """Call Gemini and return raw text (used for surprise HTML)."""
    client = genai.Client(api_key=settings.gemini_api_key)
    resp = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=temperature,
        ),
    )
    return resp.text.strip()


# ── Graph Nodes ────────────────────────────────────────────


def generate_concept(state: QuizState) -> dict:
    """Gemini generates concept explanation."""
    prompt = f"""Explain the concept "{state['topic']}" for a Grade {state['grade']} student
studying {state['subject']} ({state['course_title']}).
Difficulty: {state['difficulty']}.

Return a JSON object:
{{
  "title": "concise title for the concept",
  "explanation": "2-3 paragraph explanation using age-appropriate language and analogies",
  "key_points": ["point 1", "point 2", "point 3"],
  "example": "A worked example demonstrating the concept"
}}

Use simple language. Include a relatable analogy."""
    try:
        result = _gemini_json(prompt)
        return {"concept": result}
    except Exception as e:
        log.warning("generate_concept failed: %s", e)
        return {
            "concept": {
                "title": state["topic"],
                "explanation": f"Let's learn about {state['topic']}.",
                "key_points": [state["topic"]],
                "example": "",
            }
        }


def search_video(state: QuizState) -> dict:
    """Search YouTube for a relevant K-8 educational video."""
    from services.youtube_search import search_edu_videos

    results = search_edu_videos(
        topic=state["topic"],
        grade=state["grade"],
        subject=state["subject"],
        top_n=1,
    )
    return {"video": results[0] if results else {}}


def generate_image(state: QuizState) -> dict:
    """Generate a concept illustration via Gemini Imagen."""
    from services.image_gen import generate_concept_image

    b64 = generate_concept_image(
        topic=state["topic"],
        subject=state["subject"],
        grade=state["grade"],
    )
    return {"concept_image_b64": b64 or ""}


def generate_animation(state: QuizState) -> dict:
    """Gemini generates a JSON scene script; our engine renders it as a cartoon."""
    from quiz.animation_engine import build_animation_html

    concept = state["concept"]
    concept_json = json.dumps(concept, indent=2)

    prompt = f"""You are a cartoon storyboard artist. Create a short animated lesson
(3-5 scenes, 15-25 seconds total) that teaches "{state['topic']}" to a Grade {state['grade']}
{state['subject']} student, like a fun Flash cartoon for kids.

Concept data:
{concept_json}

Output a JSON array of scenes. Each scene has a duration and visual elements.
Our animation engine will render them — you just describe WHAT to show.

AVAILABLE ELEMENT TYPES and their properties:
- "pie"       → pie chart: x, y, r, slices (int), highlight (array of slice indices),
                fill, hlFill, label, enter, delay
- "fractionBar" → bar divided into parts: x, y, w, h, parts (int), highlight (indices),
                   fill, hlFill, label, enter, delay
- "circle"    → circle: x, y, r, fill, stroke, label, labelColor, enter, delay
- "rect"      → rectangle: x, y, w, h, fill, radius, label, labelColor, enter, delay
- "text"      → text: x, y, text, size (fraction), fill, bold, enter, delay
- "speechBubble" → bubble with text: x, y, w, h, text, fill, textColor, tail ("down"/"none"), enter, delay
- "arrow"     → arrow: x, y, x2, y2, fill, lineWidth, enter, delay
- "star"      → decorative star: x, y, r, fill, enter, delay
- "numberLine" → number line: x, y, w, min, max, marks (array of {{value, label, color}}), enter, delay
- "confetti"  → confetti burst: x, y, count, delay

POSITIONS: x, y are fractions of canvas (0.0 to 1.0). x=0.5,y=0.5 = center.
SIZES: r, w, h, size are also fractions. r=0.1 is 10% of canvas width.
ENTER ANIMATIONS: "slideLeft", "slideRight", "slideUp", "bounceIn", "pop", "scaleIn", "fadeIn"
EASING: add "easing": "bounce"/"elastic"/"back"/"easeOut"/"easeInOut" to any element
DELAY: seconds after scene start before element appears
WOBBLE: add "wobble": true for continuous wiggle after entering

EXAMPLE for "adding fractions 1/3 + 1/4":
[
  {{
    "duration": 5,
    "background": "#FFF8E1",
    "elements": [
      {{"type":"speechBubble","x":0.5,"y":0.12,"w":0.7,"h":0.12,"text":"Let's add 1/3 + 1/4!","tail":"none","enter":"fadeIn","delay":0}},
      {{"type":"pie","x":0.3,"y":0.5,"r":0.13,"slices":3,"highlight":[0],"fill":"#E8E8E8","hlFill":"#FF6B6B","label":"1/3","enter":"slideLeft","easing":"bounce","delay":0.5}},
      {{"type":"text","x":0.5,"y":0.5,"text":"+","size":0.08,"fill":"#666","bold":true,"enter":"pop","delay":1.2}},
      {{"type":"pie","x":0.7,"y":0.5,"r":0.13,"slices":4,"highlight":[0],"fill":"#E8E8E8","hlFill":"#4ECDC4","label":"1/4","enter":"slideRight","easing":"bounce","delay":0.5}}
    ]
  }},
  {{
    "duration": 5,
    "background": "#E8F5E9",
    "elements": [
      {{"type":"speechBubble","x":0.5,"y":0.12,"w":0.8,"h":0.12,"text":"Rewrite with common denominator 12!","tail":"none","enter":"fadeIn"}},
      {{"type":"fractionBar","x":0.5,"y":0.4,"w":0.7,"h":0.07,"parts":12,"highlight":[0,1,2,3],"fill":"#E8E8E8","hlFill":"#FF6B6B","label":"4/12","enter":"slideUp","delay":0.8}},
      {{"type":"fractionBar","x":0.5,"y":0.6,"w":0.7,"h":0.07,"parts":12,"highlight":[0,1,2],"fill":"#E8E8E8","hlFill":"#4ECDC4","label":"3/12","enter":"slideUp","delay":1.4}},
      {{"type":"arrow","x":0.15,"y":0.48,"x2":0.15,"y2":0.55,"fill":"#999","enter":"fadeIn","delay":2}}
    ]
  }},
  {{
    "duration": 5,
    "background": "#E3F2FD",
    "elements": [
      {{"type":"speechBubble","x":0.5,"y":0.12,"w":0.7,"h":0.12,"text":"4/12 + 3/12 = 7/12!","tail":"none","enter":"fadeIn"}},
      {{"type":"fractionBar","x":0.5,"y":0.45,"w":0.7,"h":0.09,"parts":12,"highlight":[0,1,2,3,4,5,6],"fill":"#E8E8E8","hlFill":"#FFD93D","label":"7/12","enter":"bounceIn","easing":"elastic","delay":0.5}},
      {{"type":"text","x":0.5,"y":0.72,"text":"7/12","size":0.12,"fill":"#FF6B6B","bold":true,"enter":"pop","easing":"elastic","delay":1.5}},
      {{"type":"confetti","x":0.5,"y":0.5,"count":60,"delay":2.5}},
      {{"type":"star","x":0.2,"y":0.75,"r":0.03,"fill":"#FFD93D","enter":"pop","delay":2.8}},
      {{"type":"star","x":0.8,"y":0.75,"r":0.03,"fill":"#FFD93D","enter":"pop","delay":3}}
    ]
  }}
]

RULES:
- Output ONLY the JSON array. No markdown fences, no explanation.
- 3-5 scenes. Each scene 3-6 seconds.
- Use bright, fun colors. This is for kids!
- Tell a visual STORY — don't just show text. Use pies, bars, shapes, arrows.
- Last scene should be celebratory (confetti, stars, big result text).
- Every scene needs a speechBubble explaining what's happening.
- Use varied enter animations and easing for energy and personality."""

    try:
        scene_data = _gemini_json(prompt, temperature=0.85)
        # Handle wrapped response
        if isinstance(scene_data, dict) and "scenes" in scene_data:
            scene_data = scene_data["scenes"]
        if not isinstance(scene_data, list) or len(scene_data) < 2:
            log.warning("Scene data invalid (not a list or too short), using fallback")
            return {"animation_html": _fallback_animation(concept)}
        html = build_animation_html(scene_data)
        return {"animation_html": html}
    except Exception as e:
        log.warning("generate_animation failed: %s", e)
        return {"animation_html": _fallback_animation(concept)}


def _fallback_animation(concept: dict) -> str:
    """Simple CSS-animated fallback when Gemini animation fails."""
    title = concept.get("title", "")
    points = concept.get("key_points", [])
    example = concept.get("example", "")
    points_html = "".join(
        f'<li style="animation:fadeSlide 0.5s ease {i*0.2}s both">{p}</li>'
        for i, p in enumerate(points)
    )
    return f"""<div id="animation-root">
<style>
#animation-root {{ font-family: -apple-system, sans-serif; padding: 20px;
  max-width: 600px; margin: 0 auto; }}
#animation-root h3 {{ font-size: 1.3em; margin-bottom: 12px; }}
#animation-root ul {{ padding-left: 20px; }}
#animation-root li {{ margin: 8px 0; opacity: 0; }}
#animation-root .example {{ background: #f0f9ff; border-left: 3px solid #3b82f6;
  padding: 12px; border-radius: 0 8px 8px 0; margin-top: 16px;
  white-space: pre-wrap; font-size: 0.95em; }}
@keyframes fadeSlide {{
  from {{ opacity: 0; transform: translateX(-20px); }}
  to {{ opacity: 1; transform: translateX(0); }}
}}
</style>
<h3>{title}</h3>
<ul>{points_html}</ul>
{f'<div class="example">{example}</div>' if example else ''}
</div>"""


def generate_questions(state: QuizState) -> dict:
    """Gemini generates quiz questions."""
    concept_ctx = json.dumps(state["concept"], indent=2)
    prompt = f"""Generate exactly {state['num_questions']} quiz questions on: "{state['topic']}"
Course: {state['course_title']} ({state['subject']}), Grade {state['grade']}
Difficulty: {state['difficulty']}

Use this concept context for question design:
{concept_ctx}

Return JSON:
{{
  "questions": [
    {{
      "id": 1,
      "type": "multiple_choice",
      "question": "...",
      "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
      "correct_answer": "A",
      "explanation": "Why this is correct",
      "hint": "Optional hint"
    }}
  ]
}}

Rules:
- Mix types: ~60% multiple_choice, ~20% true_false, ~20% fill_blank
- For true_false: options should be ["True", "False"], correct_answer is "True" or "False"
- For fill_blank: options should be null, correct_answer is the text answer
- Questions progress from easy to hard
- All content in English
- Exactly {state['num_questions']} questions"""
    try:
        result = _gemini_json(prompt)
        questions = result.get("questions", result if isinstance(result, list) else [])
        return {"questions": questions}
    except Exception as e:
        log.warning("generate_questions failed: %s", e)
        return {"questions": []}


def quality_check(state: QuizState) -> dict:
    """Validate question count, types, and answer completeness."""
    questions = state.get("questions", [])
    valid_types = {"multiple_choice", "true_false", "fill_blank"}

    ok = (
        len(questions) >= state["num_questions"]
        and all(q.get("correct_answer") for q in questions)
        and all(q.get("type") in valid_types for q in questions)
        and all(q.get("question") for q in questions)
    )
    retry = state.get("retry_count", 0) + (0 if ok else 1)
    return {"quality_ok": ok, "retry_count": retry}


def build_html(state: QuizState) -> dict:
    """Combine animation (Phase 1) + quiz (Phase 2) into one HTML page."""
    from quiz.templates import build_quiz_html

    # ── Build the quiz part ──
    if state["mode"] == "surprise":
        quiz_inner = _build_surprise_html(state)
        if not quiz_inner or "<script>" not in quiz_inner:
            log.warning("Surprise HTML invalid, falling back to template")
            quiz_inner = build_quiz_html(
                concept=state["concept"],
                questions=state["questions"],
                quiz_id=state.get("quiz_id", ""),
                supabase_url=state["supabase_url"],
                supabase_key=state["supabase_key"],
                template="random",
            )
    else:
        quiz_inner = build_quiz_html(
            concept=state["concept"],
            questions=state["questions"],
            quiz_id=state.get("quiz_id", ""),
            supabase_url=state["supabase_url"],
            supabase_key=state["supabase_key"],
            template="random",
        )

    animation_html = state.get("animation_html", "")

    # ── Build video + image HTML for learn phase ──
    video_html = ""
    video = state.get("video") or {}
    if video.get("video_id"):
        from services.youtube_search import build_youtube_embed
        video_html = build_youtube_embed(video["video_id"])

    image_html = ""
    img_b64 = state.get("concept_image_b64", "")
    if img_b64:
        from services.image_gen import build_image_html
        image_html = build_image_html(img_b64, alt=state.get("topic", ""))

    if not animation_html and not video_html and not image_html:
        return {"quiz_html": quiz_inner}

    html = _build_two_phase_html(
        video_html=video_html,
        image_html=image_html,
        animation_html=animation_html,
        quiz_full_html=quiz_inner,
        video_title=video.get("title", ""),
        video_channel=video.get("channel", ""),
    )
    return {"quiz_html": html}


def _build_two_phase_html(
    video_html: str,
    image_html: str,
    animation_html: str,
    quiz_full_html: str,
    video_title: str = "",
    video_channel: str = "",
) -> str:
    """Wrap learn resources + quiz into a single page with phase transition."""
    import re
    body_match = re.search(
        r"<body[^>]*>(.*)</body>", quiz_full_html, re.DOTALL | re.IGNORECASE
    )
    head_match = re.search(
        r"<head[^>]*>(.*)</head>", quiz_full_html, re.DOTALL | re.IGNORECASE
    )
    quiz_body = body_match.group(1) if body_match else quiz_full_html
    quiz_head = head_match.group(1) if head_match else ""

    # Build learn section pieces
    video_section = ""
    if video_html:
        title_esc = video_title.replace('"', '&quot;').replace('<', '&lt;')
        channel_esc = video_channel.replace('"', '&quot;').replace('<', '&lt;')
        video_section = f"""
    <div class="learn-card">
      <div class="learn-label">📺 Watch</div>
      <div style="text-align:center">{video_html}</div>
      <div class="vid-meta">{title_esc}<br><span style="color:#999">{channel_esc}</span></div>
    </div>"""

    image_section = ""
    if image_html:
        image_section = f"""
    <div class="learn-card">
      <div class="learn-label">🖼️ Visualize</div>
      {image_html}
    </div>"""

    animation_section = ""
    if animation_html:
        animation_section = f"""
    <div class="learn-card">
      <div class="learn-label">🎬 Animation</div>
      {animation_html}
    </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
{quiz_head}
<style>
* {{ box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; padding: 0; }}
#phase-learn {{ max-width: 680px; margin: 0 auto; padding: 16px; animation: fadeIn 0.4s ease; }}
#phase-quiz {{ display: none; animation: fadeIn 0.4s ease; }}
.learn-card {{
  background: #fff; border-radius: 16px; padding: 20px; margin-bottom: 16px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
}}
.learn-label {{
  font-size: 0.85em; font-weight: 700; text-transform: uppercase;
  letter-spacing: 1px; color: #6366f1; margin-bottom: 12px;
}}
.vid-meta {{
  text-align: center; font-size: 0.85em; color: #555; margin-top: 10px; line-height: 1.4;
}}
.phase-btn {{
  display: block; margin: 24px auto; padding: 16px 40px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6); color: white;
  border: none; border-radius: 14px; font-size: 1.15em; font-weight: 700;
  cursor: pointer; box-shadow: 0 4px 20px rgba(99,102,241,0.35);
  transition: all 0.2s; letter-spacing: 0.5px;
}}
.phase-btn:hover {{ transform: translateY(-2px); box-shadow: 0 6px 28px rgba(99,102,241,0.45); }}
@keyframes fadeIn {{ from {{ opacity:0; transform:translateY(16px); }}
  to {{ opacity:1; transform:translateY(0); }} }}
</style>
</head>
<body>
<!-- ═══ Phase 1: Learn ═══ -->
<div id="phase-learn">
  {video_section}
  {image_section}
  {animation_section}
  <button class="phase-btn" onclick="startQuiz()">I'm ready for the quiz &rarr;</button>
</div>

<!-- ═══ Phase 2: Quiz ═══ -->
<div id="phase-quiz">
  {quiz_body}
</div>

<script>
function startQuiz() {{
  document.getElementById('phase-learn').style.display = 'none';
  document.getElementById('phase-quiz').style.display = 'block';
  window.scrollTo(0, 0);
}}
</script>
</body>
</html>"""


def save_to_db(state: QuizState) -> dict:
    """Persist quiz session to Supabase."""
    from db.queries import save_quiz_session

    try:
        row = save_quiz_session(
            student_id=state["student_id"],
            course_id=state.get("course_id") or None,
            topic=state["topic"],
            concept=state["concept"],
            questions=state["questions"],
            quiz_html=state["quiz_html"],
            difficulty=state["difficulty"],
        )
        quiz_id = row["id"]
        # Re-render HTML with the real quiz_id for Supabase submission
        html = state["quiz_html"].replace("__QUIZ_ID__", quiz_id)
        # Best-effort update — RLS may block non-completion updates
        try:
            from services.supabase_client import get_supabase
            get_supabase().table("quiz_sessions").update(
                {"quiz_html": html}
            ).eq("id", quiz_id).execute()
        except Exception:
            log.debug("quiz_html DB update skipped (RLS); display HTML has correct ID")
        return {"quiz_id": quiz_id, "quiz_html": html}
    except Exception as e:
        log.error("save_to_db failed: %s", e)
        return {"error": str(e)}


# ── Surprise HTML Generator ───────────────────────────────


def _build_surprise_html(state: QuizState) -> str:
    """Let Gemini generate a complete HTML quiz page from scratch."""
    from quiz.templates.base import SUPABASE_SUBMIT_JS

    submit_js = SUPABASE_SUBMIT_JS.replace(
        "{{SUPABASE_URL}}", state["supabase_url"]
    ).replace(
        "{{SUPABASE_KEY}}", state["supabase_key"]
    ).replace(
        "{{QUIZ_ID}}", "__QUIZ_ID__"
    )

    questions_json = json.dumps(state["questions"], indent=2)
    concept_json = json.dumps(state["concept"], indent=2)

    prompt = f"""Generate a COMPLETE, self-contained HTML page for an interactive quiz.

CREATIVE FREEDOM: Design a unique, visually stunning quiz experience.
Pick ONE creative theme. Examples of themes you could choose:
- Space exploration with floating asteroids
- Underwater adventure
- Medieval quest / RPG
- Pixel art retro game
- Nature / garden growing
- Cooking challenge
- Mystery detective

MUST include ALL of the following:
1. A concept explanation section (collapsible) using this data:
{concept_json}

2. Interactive questions using this data:
{questions_json}

3. Self-grading logic that compares user answers to correct_answer field
4. Animated result reveal showing score and per-question feedback
5. THIS EXACT JavaScript function (copy it exactly, do not modify):

{submit_js}

6. Call submitResults() after showing the results

Technical rules:
- Output ONLY the HTML. No markdown code fences.
- Single HTML file, zero external dependencies (NO CDN links, NO imports)
- All CSS in <style> tags, all JS in <script> tags
- Responsive design, works on mobile (min-width: 320px)
- Use modern CSS (gradients, box-shadow, border-radius, transitions)
- Smooth animations between question transitions
"""
    try:
        html = _gemini_text(prompt, temperature=0.95)
        # Strip markdown fences if present
        if html.startswith("```"):
            html = html.split("\n", 1)[1]
            html = html.rsplit("```", 1)[0]
        return html
    except Exception as e:
        log.warning("Surprise HTML generation failed: %s", e)
        return ""


# ── Conditional Edge ───────────────────────────────────────


def _should_retry(state: QuizState) -> str:
    if state.get("quality_ok"):
        return "build_html"
    if state.get("retry_count", 0) < 2:
        return "generate_questions"
    return "build_html"  # give up retrying, use what we have


# ── Build Graph ────────────────────────────────────────────


def _build_graph() -> Any:
    g = StateGraph(QuizState)

    g.add_node("generate_concept", generate_concept)
    g.add_node("search_video", search_video)
    g.add_node("generate_image", generate_image)
    g.add_node("generate_animation", generate_animation)
    g.add_node("generate_questions", generate_questions)
    g.add_node("quality_check", quality_check)
    g.add_node("build_html", build_html)
    g.add_node("save_to_db", save_to_db)

    g.set_entry_point("generate_concept")
    g.add_edge("generate_concept", "search_video")
    g.add_edge("search_video", "generate_image")
    g.add_edge("generate_image", "generate_animation")
    g.add_edge("generate_animation", "generate_questions")
    g.add_edge("generate_questions", "quality_check")
    g.add_conditional_edges("quality_check", _should_retry)
    g.add_edge("build_html", "save_to_db")
    g.add_edge("save_to_db", END)

    return g.compile()


quiz_graph = _build_graph()
