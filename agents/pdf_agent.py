"""Gemini-powered PDF generation agent."""
from __future__ import annotations
import json
from app.config import settings


PDF_AGENT_SYSTEM_PROMPT = """You are Evlin's educational content generator. You create pedagogically sound
practice problems and course materials for homeschool students.

When asked to generate practice problems:
1. Consider the subject, grade level, and difficulty.
2. Create problems that are age-appropriate and aligned with the curriculum.
3. Include a mix of problem types (short answer, word problems, true/false, etc.).
4. Provide clear instructions for each problem.
5. Include detailed answer keys with explanations.
6. For math: include computation, word problems, and conceptual questions.
7. For science: include factual recall, application, and analysis questions.
8. For English: include grammar, reading comprehension, and writing prompts.
9. For history: include timeline, cause-effect, and critical thinking questions.

Return problems as a JSON array where each problem has:
- number: sequential integer
- instruction: what the student should do
- content: the actual question content (math expression, passage reference, etc.)
- type: one of "short_answer", "word_problem", "essay", "true_false", "multiple_choice"
- points: point value (1-5)
- answer: the correct answer
- explanation: why that's the answer
"""


def generate_practice_problems_pdf(
    subject: str,
    grade: int,
    num_problems: int = 10,
    difficulty: str = "standard",
    include_answers: bool = True,
    student_id: str = None,
) -> bytes:
    """Use Gemini to generate problems, then render as PDF.

    Args:
        subject: Math, Science, English, or History
        grade: Grade level 1-12
        num_problems: Number of problems to generate
        difficulty: easy, standard, or advanced
        include_answers: Include answer key section
        student_id: Optional student UUID for metadata

    Returns: PDF as bytes
    """
    if not settings.gemini_api_key:
        raise ImportError("GEMINI_API_KEY not set. Cannot generate AI content.")

    from google import genai
    from google.genai import types
    from pdf.templates.practice_problems import build_practice_problems_pdf

    client = genai.Client(api_key=settings.gemini_api_key)

    prompt = f"""Generate exactly {num_problems} practice problems for:
- Subject: {subject}
- Grade Level: {grade}
- Difficulty: {difficulty}

Return ONLY a JSON object with this structure:
{{
  "title": "descriptive title for this practice set",
  "problems": [
    {{
      "number": 1,
      "instruction": "what the student should do",
      "content": "the question content",
      "type": "short_answer",
      "points": 2,
      "answer": "the correct answer",
      "explanation": "why that's correct"
    }}
  ]
}}

Make problems progressively harder. Ensure variety in question types.
Return ONLY valid JSON, no markdown formatting."""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=PDF_AGENT_SYSTEM_PROMPT,
            temperature=0.8,
            response_mime_type="application/json",
        ),
    )

    # Parse the response
    response_text = response.text.strip()
    # Remove potential markdown code blocks
    if response_text.startswith("```"):
        response_text = response_text.split("\n", 1)[1]
        response_text = response_text.rsplit("```", 1)[0]

    data = json.loads(response_text)

    title = data.get("title", f"{subject} Grade {grade} Practice Set")
    problems = data.get("problems", [])

    # Generate PDF
    pdf_bytes = build_practice_problems_pdf(
        title=title,
        subject=subject,
        grade=grade,
        problems=problems,
        include_answers=include_answers,
    )

    # Optionally store in MinIO and record in DB
    try:
        _store_pdf(pdf_bytes, title, subject, student_id, "practice_problems")
    except Exception:
        pass  # Don't fail if storage is unavailable

    return pdf_bytes


def _store_pdf(pdf_bytes: bytes, title: str, subject: str, student_id: str, pdf_type: str):
    """Store generated PDF in MinIO and record in Supabase."""
    import io
    import uuid
    from services.minio_client import get_minio, ensure_bucket
    from db.queries import insert_generated_pdf

    ensure_bucket("evlin-pdfs")
    obj_key = f"{pdf_type}/{uuid.uuid4()}.pdf"

    get_minio().put_object(
        "evlin-pdfs",
        obj_key,
        io.BytesIO(pdf_bytes),
        len(pdf_bytes),
        content_type="application/pdf",
    )

    insert_generated_pdf({
        "student_id": student_id,
        "pdf_type": pdf_type,
        "title": title,
        "minio_bucket": "evlin-pdfs",
        "minio_key": obj_key,
        "file_size_kb": len(pdf_bytes) // 1024,
        "metadata": {"subject": subject},
    })
