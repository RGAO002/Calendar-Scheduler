"""Pinecone vector operations for semantic course search."""
from __future__ import annotations
from typing import Optional
from services.pinecone_client import get_index


def upsert_course_embedding(course_id: str, embedding: list[float], metadata: dict):
    """Store a course embedding in Pinecone."""
    index = get_index()
    index.upsert(vectors=[{"id": course_id, "values": embedding, "metadata": metadata}])


def search_courses_by_embedding(
    query_embedding: list[float],
    top_k: int = 5,
    subject_filter: Optional[str] = None,
    grade_filter: Optional[int] = None,
) -> list[dict]:
    """Search for similar courses using a query embedding."""
    index = get_index()

    filter_dict = {}
    if subject_filter:
        filter_dict["subject"] = subject_filter
    if grade_filter:
        filter_dict["grade_level_min"] = {"$lte": grade_filter}
        filter_dict["grade_level_max"] = {"$gte": grade_filter}

    results = index.query(
        vector=query_embedding,
        top_k=top_k,
        include_metadata=True,
        filter=filter_dict if filter_dict else None,
    )

    return [
        {
            "course_id": match["id"],
            "score": match["score"],
            "metadata": match.get("metadata", {}),
        }
        for match in results.get("matches", [])
    ]


def delete_all_vectors():
    """Delete all vectors from the index. Use for re-seeding."""
    index = get_index()
    index.delete(delete_all=True)
