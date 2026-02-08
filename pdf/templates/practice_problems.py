"""Practice problems PDF template - textbook quality layout."""
from __future__ import annotations
from io import BytesIO
from reportlab.platypus import (
    Paragraph, Spacer, PageBreak, HRFlowable, Table, TableStyle,
)
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor

from pdf.styles import (
    get_evlin_styles, EVLIN_NAVY, EVLIN_BLUE, EVLIN_LIGHT_BLUE,
    EVLIN_ACCENT, EVLIN_GRAY, EVLIN_GREEN, EVLIN_DARK_GRAY,
)
from pdf.templates.textbook_base import EvlinTextbookDoc


def build_practice_problems_pdf(
    title: str,
    subject: str,
    grade: int,
    problems: list[dict],
    include_answers: bool = True,
) -> bytes:
    """Generate a textbook-quality practice problems PDF.

    Args:
        title: Document title
        subject: Subject name
        grade: Grade level
        problems: List of problem dicts with keys:
            number, instruction, content, type, points, answer, explanation
        include_answers: Whether to include answer key section

    Returns: PDF as bytes
    """
    buffer = BytesIO()
    styles = get_evlin_styles()

    doc = EvlinTextbookDoc(
        buffer,
        title=title,
        subtitle=f"{subject} | Grade {grade}",
    )

    story = []

    # ── Cover Section ─────────────────────────────────────
    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph(title, styles["EvlinTitle"]))
    story.append(Paragraph(f"{subject} — Grade {grade}", styles["EvlinSubtitle"]))

    # Info box
    total_points = sum(p.get("points", 0) for p in problems)
    info_data = [
        ["Total Questions", str(len(problems))],
        ["Total Points", str(total_points)],
        ["Subject", subject],
        ["Grade Level", str(grade)],
    ]
    info_table = Table(info_data, colWidths=[1.5 * inch, 2 * inch])
    info_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), EVLIN_LIGHT_BLUE),
        ("TEXTCOLOR", (0, 0), (0, -1), EVLIN_NAVY),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("PADDING", (0, 0), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -1), 0.5, EVLIN_LIGHT_BLUE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(Spacer(1, 0.2 * inch))
    story.append(info_table)

    # Name/Date line
    story.append(Spacer(1, 0.3 * inch))
    story.append(HRFlowable(width="100%", thickness=0.5, color=EVLIN_DARK_GRAY))
    story.append(Spacer(1, 0.05 * inch))
    story.append(Paragraph(
        "Name: ________________________________    Date: ________________",
        styles["EvlinBody"],
    ))
    story.append(Spacer(1, 0.2 * inch))
    story.append(HRFlowable(width="100%", thickness=1, color=EVLIN_BLUE))

    # ── Problems Section ──────────────────────────────────
    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph("Problems", styles["EvlinH2"]))

    for p in problems:
        num = p.get("number", "?")
        instruction = p.get("instruction", "")
        content = p.get("content", "")
        points = p.get("points", 0)
        prob_type = p.get("type", "short_answer")

        # Problem number + points
        story.append(Paragraph(
            f"<b>Problem {num}</b>",
            styles["ProblemNumber"],
        ))
        story.append(Paragraph(
            f"[{points} point{'s' if points != 1 else ''}]",
            styles["PointsLabel"],
        ))

        # Instruction
        if instruction:
            story.append(Paragraph(instruction, styles["ProblemInstruction"]))

        # Content (the actual question/expression)
        if content:
            story.append(Paragraph(
                f"<b>{content}</b>",
                styles["ProblemContent"],
            ))

        # Answer space based on problem type
        if prob_type == "essay":
            # Large answer box
            for _ in range(6):
                story.append(Spacer(1, 0.05 * inch))
                story.append(HRFlowable(
                    width="90%", thickness=0.3, color=EVLIN_LIGHT_BLUE,
                    spaceAfter=8,
                ))
        elif prob_type == "true_false":
            story.append(Spacer(1, 0.05 * inch))
            story.append(Paragraph(
                "&nbsp;&nbsp;&nbsp;&nbsp;☐ True&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;☐ False",
                styles["ProblemInstruction"],
            ))
        else:
            # Short answer line
            story.append(Spacer(1, 0.1 * inch))
            story.append(Paragraph(
                "Answer: _____________________________________________",
                styles["ProblemInstruction"],
            ))

        story.append(Spacer(1, 0.1 * inch))

    # ── Answer Key Section ────────────────────────────────
    if include_answers:
        story.append(PageBreak())
        story.append(Paragraph("Answer Key", styles["AnswerHeader"]))
        story.append(HRFlowable(width="100%", thickness=1, color=EVLIN_GREEN))
        story.append(Spacer(1, 0.15 * inch))

        for p in problems:
            num = p.get("number", "?")
            answer = p.get("answer", "")
            explanation = p.get("explanation", "")
            points = p.get("points", 0)

            # Answer with green accent
            story.append(Paragraph(
                f"<b>Problem {num}</b> [{points} pts]",
                styles["ProblemNumber"],
            ))
            story.append(Paragraph(
                f"<b>Answer:</b> {answer}",
                styles["AnswerText"],
            ))
            if explanation:
                story.append(Paragraph(
                    f"<i>Explanation:</i> {explanation}",
                    styles["ExplanationText"],
                ))

    # Build
    doc.build(story)
    return buffer.getvalue()
