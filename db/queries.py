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
