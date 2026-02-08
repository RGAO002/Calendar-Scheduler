"""Gemini-powered scheduling agent with function calling."""
from __future__ import annotations
import json
from google import genai
from google.genai import types
from app.config import settings

# Tool function implementations
from agents.tools.availability_checker import get_student_availability, get_current_schedule
from agents.tools.course_recommender import search_courses, check_prerequisites
from agents.tools.conflict_detector import detect_conflicts
from agents.tools.schedule_writer import propose_schedule, confirm_schedule

SCHEDULER_SYSTEM_PROMPT = """You are Evlin's AI scheduling assistant for homeschool families.

Your job is to help parents find the right courses and time slots for their children.

## How You Reason About Scheduling

For every scheduling decision, use YES / NO / MAYBE logic:

- **YES**: The time slot is available, the course fits the student's grade level, all prerequisites are met, and there are no conflicts. Recommend it confidently.
- **NO**: There is a hard conflict—time overlap with existing course, grade level mismatch, or missing prerequisite. Explain clearly why it won't work.
- **MAYBE**: The slot could technically work, but has soft concerns—the student marked that time as "avoid" in their preferences, or the day is already heavy with courses, or the difficulty might be challenging. Present it as an option with caveats.

## Your Workflow

1. When a parent asks about scheduling, first check the student's current schedule and availability.
2. Search for matching courses based on their request.
3. For each candidate course, check prerequisites and detect conflicts for possible time slots.
4. Present 1-3 ranked options with your YES/NO/MAYBE reasoning for each.
5. When the parent chooses an option, propose the schedule.
6. When the parent confirms, finalize it.

## Communication Style

- Be friendly and professional
- Explain your reasoning clearly
- When presenting options, use a structured format
- Always mention trade-offs (e.g., "This works but the day would be heavy")
- Ask for clarification if the request is ambiguous
- Use the student's first name

## Important Rules

- Never schedule during times marked as "avoid" without explicitly noting it
- Always verify prerequisites before recommending a course
- Consider total weekly hours—flag if a schedule seems too heavy
- Propose at most 3 options to avoid overwhelming the parent
"""

# Define function declarations for Gemini
TOOL_DECLARATIONS = [
    types.FunctionDeclaration(
        name="get_student_availability",
        description="Get the student's weekly availability slots organized by day. Shows preferred times, available times, and times to avoid.",
        parameters={
            "type": "object",
            "properties": {
                "student_id": {"type": "string", "description": "The student's UUID"},
            },
            "required": ["student_id"],
        },
    ),
    types.FunctionDeclaration(
        name="get_current_schedule",
        description="Get the student's current active schedule showing all enrolled courses and their weekly time slots.",
        parameters={
            "type": "object",
            "properties": {
                "student_id": {"type": "string", "description": "The student's UUID"},
            },
            "required": ["student_id"],
        },
    ),
    types.FunctionDeclaration(
        name="search_courses",
        description="Search the course catalog by subject, grade level, difficulty, or keyword. Returns matching courses with details.",
        parameters={
            "type": "object",
            "properties": {
                "subject": {"type": "string", "description": "Filter by subject: Math, Science, English, History, Art, PE"},
                "grade_level": {"type": "integer", "description": "Filter by grade level (1-12)"},
                "difficulty": {"type": "string", "description": "Filter by difficulty: easy, standard, advanced, honors"},
                "keyword": {"type": "string", "description": "Search keyword to match against course title, description, or tags"},
            },
        },
    ),
    types.FunctionDeclaration(
        name="check_prerequisites",
        description="Check if a student has completed all prerequisites for a specific course.",
        parameters={
            "type": "object",
            "properties": {
                "course_code": {"type": "string", "description": "The course code to check (e.g., 'MATH-5B')"},
                "student_id": {"type": "string", "description": "The student's UUID"},
            },
            "required": ["course_code", "student_id"],
        },
    ),
    types.FunctionDeclaration(
        name="detect_conflicts",
        description="Check if a proposed time slot conflicts with the student's existing schedule or availability. Returns YES/NO/MAYBE verdict.",
        parameters={
            "type": "object",
            "properties": {
                "student_id": {"type": "string", "description": "The student's UUID"},
                "proposed_day": {"type": "integer", "description": "Day of week: 0=Monday, 1=Tuesday, 2=Wednesday, 3=Thursday, 4=Friday"},
                "proposed_start": {"type": "string", "description": "Start time as HH:MM (e.g., '09:00')"},
                "proposed_end": {"type": "string", "description": "End time as HH:MM (e.g., '10:30')"},
            },
            "required": ["student_id", "proposed_day", "proposed_start", "proposed_end"],
        },
    ),
    types.FunctionDeclaration(
        name="propose_schedule",
        description="Create a proposed schedule for the student. The parent must confirm it before it becomes active.",
        parameters={
            "type": "object",
            "properties": {
                "student_id": {"type": "string", "description": "The student's UUID"},
                "course_code": {"type": "string", "description": "The course code (e.g., 'SCI-5A')"},
                "slots": {
                    "type": "array",
                    "description": "Time slots for the course",
                    "items": {
                        "type": "object",
                        "properties": {
                            "day_of_week": {"type": "integer", "description": "0=Monday through 6=Sunday"},
                            "start_time": {"type": "string", "description": "HH:MM format"},
                            "end_time": {"type": "string", "description": "HH:MM format"},
                        },
                        "required": ["day_of_week", "start_time", "end_time"],
                    },
                },
                "duration_weeks": {"type": "integer", "description": "Number of weeks (default 12)"},
            },
            "required": ["student_id", "course_code", "slots"],
        },
    ),
    types.FunctionDeclaration(
        name="confirm_schedule",
        description="Confirm a proposed schedule, making it active. Only call this when the parent explicitly agrees.",
        parameters={
            "type": "object",
            "properties": {
                "schedule_id": {"type": "string", "description": "The schedule UUID to confirm"},
            },
            "required": ["schedule_id"],
        },
    ),
]

# Map function names to implementations
TOOL_FUNCTIONS = {
    "get_student_availability": lambda args: get_student_availability(args["student_id"]),
    "get_current_schedule": lambda args: get_current_schedule(args["student_id"]),
    "search_courses": lambda args: search_courses(
        subject=args.get("subject"),
        grade_level=args.get("grade_level"),
        difficulty=args.get("difficulty"),
        keyword=args.get("keyword"),
    ),
    "check_prerequisites": lambda args: check_prerequisites(args["course_code"], args["student_id"]),
    "detect_conflicts": lambda args: detect_conflicts(
        args["student_id"],
        args["proposed_day"],
        args["proposed_start"],
        args["proposed_end"],
    ),
    "propose_schedule": lambda args: propose_schedule(
        args["student_id"],
        args["course_code"],
        args["slots"],
        args.get("duration_weeks", 12),
    ),
    "confirm_schedule": lambda args: confirm_schedule(args["schedule_id"]),
}


def run_scheduler_agent(messages: list[dict], student_id: str, max_turns: int = 10) -> str:
    """Run the scheduler agent with Gemini function calling.

    Args:
        messages: Chat history [{role, content}]
        student_id: Current student UUID
        max_turns: Max function-calling rounds to prevent infinite loops

    Returns: Agent's text response
    """
    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY not set in .env")

    client = genai.Client(api_key=settings.gemini_api_key)

    # Get student info for context
    from db.queries import get_student
    student = get_student(student_id)
    student_context = ""
    if student:
        student_context = (
            f"\n\nCurrent student: {student['first_name']} {student['last_name']}, "
            f"Grade {student['grade_level']}. Student ID: {student_id}"
        )
        if student.get("notes"):
            student_context += f"\nNotes: {student['notes']}"

    system_prompt = SCHEDULER_SYSTEM_PROMPT + student_context

    # Build Gemini conversation from message history
    contents = []
    for msg in messages:
        if msg["role"] == "user":
            contents.append(types.Content(
                role="user",
                parts=[types.Part.from_text(text=msg["content"])],
            ))
        elif msg["role"] == "assistant":
            contents.append(types.Content(
                role="model",
                parts=[types.Part.from_text(text=msg["content"])],
            ))

    # Function calling loop
    for _ in range(max_turns):
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                tools=[types.Tool(function_declarations=TOOL_DECLARATIONS)],
                temperature=0.7,
            ),
        )

        # Check if response has function calls
        candidate = response.candidates[0]
        parts = candidate.content.parts

        has_function_call = any(
            hasattr(part, "function_call") and part.function_call
            for part in parts
        )

        if not has_function_call:
            # No function calls - return the text response
            text_parts = [part.text for part in parts if hasattr(part, "text") and part.text]
            return "\n".join(text_parts) if text_parts else "I'm not sure how to help with that. Could you rephrase?"

        # Process function calls
        contents.append(candidate.content)

        function_response_parts = []
        for part in parts:
            if hasattr(part, "function_call") and part.function_call:
                fn_name = part.function_call.name
                fn_args = dict(part.function_call.args) if part.function_call.args else {}

                # Execute the function
                if fn_name in TOOL_FUNCTIONS:
                    try:
                        result = TOOL_FUNCTIONS[fn_name](fn_args)
                    except Exception as e:
                        result = json.dumps({"error": str(e)})
                else:
                    result = json.dumps({"error": f"Unknown function: {fn_name}"})

                function_response_parts.append(
                    types.Part.from_function_response(
                        name=fn_name,
                        response={"result": result},
                    )
                )

        contents.append(types.Content(
            role="user",
            parts=function_response_parts,
        ))

    return "I've reached my reasoning limit. Could you simplify your request?"
