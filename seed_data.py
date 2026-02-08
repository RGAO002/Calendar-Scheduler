#!/usr/bin/env python3
"""Seed all data stores with dummy data.

Usage:
    python seed_data.py              # Seed all stores
    python seed_data.py --supabase   # Seed only Supabase
    python seed_data.py --neo4j      # Seed only Neo4j
    python seed_data.py --minio      # Seed only MinIO buckets
"""
import json
import sys
from pathlib import Path
from datetime import date, timedelta

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

# Add project root to path
sys.path.insert(0, str(BASE_DIR))

from app.config import settings


def load_json(filename: str):
    with open(DATA_DIR / filename) as f:
        return json.load(f)


# ── Supabase Seeding ──────────────────────────────────────

def seed_supabase():
    from services.supabase_client import get_supabase
    sb = get_supabase()

    print("🔄 Seeding Supabase...")

    # Insert students
    students_data = load_json("dummy_students.json")
    print(f"  Inserting {len(students_data)} students...")
    result = sb.table("students").upsert(students_data, on_conflict="id").execute()
    students = result.data
    student_map = {f"{s['first_name']} {s['last_name']}": s["id"] for s in students}
    print(f"  ✅ Students inserted: {list(student_map.keys())}")

    # Insert courses
    courses_data = load_json("dummy_courses.json")
    print(f"  Inserting {len(courses_data)} courses...")
    result = sb.table("courses").upsert(courses_data, on_conflict="code").execute()
    courses = result.data
    course_map = {c["code"]: c["id"] for c in courses}
    print(f"  ✅ {len(courses)} courses inserted")

    # Insert availability
    availability_data = load_json("dummy_availability.json")
    all_avail = []
    for student_name, slots in availability_data.items():
        sid = student_map.get(student_name)
        if not sid:
            print(f"  ⚠️ Student '{student_name}' not found, skipping availability")
            continue
        for slot in slots:
            slot["student_id"] = sid
            all_avail.append(slot)

    # Clear existing availability first
    for sid in student_map.values():
        sb.table("availability").delete().eq("student_id", sid).execute()

    print(f"  Inserting {len(all_avail)} availability slots...")
    sb.table("availability").insert(all_avail).execute()
    print("  ✅ Availability inserted")

    # Insert sample schedules (Emma and Liam)
    today = date.today()
    semester_start = today - timedelta(days=today.weekday())  # Start of current week
    semester_end = semester_start + timedelta(weeks=12)

    sample_schedules = [
        # Emma: MATH-5A Mon/Wed 9-10, ELA-5A Tue/Thu 9-10
        {
            "student_name": "Emma Chen",
            "course_code": "MATH-5A",
            "status": "active",
            "slots": [
                {"day_of_week": 0, "start_time": "09:00", "end_time": "10:00"},
                {"day_of_week": 2, "start_time": "09:00", "end_time": "10:00"},
            ],
        },
        {
            "student_name": "Emma Chen",
            "course_code": "ELA-5A",
            "status": "active",
            "slots": [
                {"day_of_week": 1, "start_time": "09:00", "end_time": "10:00"},
                {"day_of_week": 3, "start_time": "09:00", "end_time": "10:00"},
            ],
        },
        # Liam: SCI-7A Mon/Wed 10-11:30, MATH-7A Tue/Thu 10-11
        {
            "student_name": "Liam O'Brien",
            "course_code": "SCI-7A",
            "status": "active",
            "slots": [
                {"day_of_week": 0, "start_time": "10:00", "end_time": "11:30"},
                {"day_of_week": 2, "start_time": "10:00", "end_time": "11:30"},
            ],
        },
        {
            "student_name": "Liam O'Brien",
            "course_code": "MATH-7A",
            "status": "active",
            "slots": [
                {"day_of_week": 1, "start_time": "10:00", "end_time": "11:00"},
                {"day_of_week": 3, "start_time": "10:00", "end_time": "11:00"},
            ],
        },
    ]

    print("  Inserting sample schedules...")
    for sched in sample_schedules:
        sid = student_map.get(sched["student_name"])
        cid = course_map.get(sched["course_code"])
        if not sid or not cid:
            print(f"  ⚠️ Skipping schedule: student/course not found")
            continue

        sch_result = sb.table("schedules").insert({
            "student_id": sid,
            "course_id": cid,
            "status": sched["status"],
            "start_date": str(semester_start),
            "end_date": str(semester_end),
        }).execute()

        schedule_id = sch_result.data[0]["id"]

        for slot in sched["slots"]:
            slot["schedule_id"] = schedule_id
            sb.table("schedule_slots").insert(slot).execute()

    print("  ✅ Sample schedules inserted")
    print("✅ Supabase seeding complete!\n")
    return student_map, course_map


# ── Neo4j Seeding ─────────────────────────────────────────

def seed_neo4j():
    from db.graph_queries import (
        clear_all_graph_data,
        create_course_node,
        create_prerequisite_edge,
        create_related_edge,
    )

    print("🔄 Seeding Neo4j...")
    clear_all_graph_data()

    courses = load_json("dummy_courses.json")
    for c in courses:
        create_course_node(c["code"], c["title"], c["subject"])
    print(f"  ✅ {len(courses)} course nodes created")

    # Prerequisite edges
    prereq_pairs = []
    for c in courses:
        for prereq in c.get("prerequisites", []):
            prereq_pairs.append((prereq, c["code"]))

    for from_code, to_code in prereq_pairs:
        create_prerequisite_edge(from_code, to_code)
    print(f"  ✅ {len(prereq_pairs)} prerequisite edges created")

    # Related edges (cross-subject connections)
    related_pairs = [
        ("SCI-7B", "MATH-7A", "Physical science uses pre-algebra concepts"),
        ("SCI-10A", "MATH-8A", "Biology requires algebra for data analysis"),
        ("HIST-5A", "ELA-5A", "History reading requires grammar skills"),
        ("ELA-8A", "HIST-7A", "Essay writing often covers historical topics"),
        ("ART-8A", "MATH-8A", "Digital art uses geometric concepts"),
    ]
    for a, b, reason in related_pairs:
        create_related_edge(a, b, reason)
    print(f"  ✅ {len(related_pairs)} related edges created")
    print("✅ Neo4j seeding complete!\n")


# ── MinIO Seeding ─────────────────────────────────────────

def seed_minio():
    from services.minio_client import ensure_bucket

    print("🔄 Setting up MinIO buckets...")
    for bucket in ["evlin-pdfs", "evlin-uploads"]:
        ensure_bucket(bucket)
        print(f"  ✅ Bucket '{bucket}' ready")
    print("✅ MinIO setup complete!\n")


# ── Pinecone Seeding (requires Gemini API for embeddings) ─

def seed_pinecone():
    """Seed Pinecone with course embeddings. Requires GEMINI_API_KEY."""
    if not settings.gemini_api_key:
        print("⚠️ Skipping Pinecone seeding: GEMINI_API_KEY not set")
        return

    print("🔄 Seeding Pinecone...")
    try:
        from google import genai
        from db.vector_queries import upsert_course_embedding
        from services.supabase_client import get_supabase

        client = genai.Client(api_key=settings.gemini_api_key)
        courses = get_supabase().table("courses").select("*").execute().data

        for c in courses:
            text = f"{c['title']}. {c['subject']}. {c.get('description', '')}. " \
                   f"Grade {c['grade_level_min']}-{c['grade_level_max']}. " \
                   f"Difficulty: {c['difficulty']}. Tags: {', '.join(c.get('tags', []))}"

            response = client.models.embed_content(
                model="models/text-embedding-004",
                content=text,
            )
            embedding = response.embeddings[0].values

            upsert_course_embedding(
                course_id=c["id"],
                embedding=embedding,
                metadata={
                    "code": c["code"],
                    "title": c["title"],
                    "subject": c["subject"],
                    "grade_level_min": c["grade_level_min"],
                    "grade_level_max": c["grade_level_max"],
                    "difficulty": c["difficulty"],
                },
            )
            print(f"  ✅ Embedded: {c['code']} - {c['title']}")

        print(f"✅ Pinecone seeding complete ({len(courses)} courses)!\n")
    except Exception as e:
        print(f"⚠️ Pinecone seeding failed: {e}\n")


# ── Main ──────────────────────────────────────────────────

def main():
    args = set(sys.argv[1:])
    run_all = not args

    if run_all or "--supabase" in args:
        seed_supabase()

    if run_all or "--neo4j" in args:
        seed_neo4j()

    if run_all or "--minio" in args:
        seed_minio()

    if run_all or "--pinecone" in args:
        seed_pinecone()

    print("🎉 Seeding complete!")


if __name__ == "__main__":
    main()
