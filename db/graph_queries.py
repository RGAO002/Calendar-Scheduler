"""Neo4j Cypher queries for course prerequisite graph."""
from __future__ import annotations
from services.neo4j_client import run_query


def create_course_node(code: str, title: str, subject: str):
    run_query(
        "MERGE (c:Course {code: $code}) "
        "SET c.title = $title, c.subject = $subject",
        {"code": code, "title": title, "subject": subject},
    )


def create_prerequisite_edge(from_code: str, to_code: str):
    run_query(
        "MATCH (a:Course {code: $from_code}), (b:Course {code: $to_code}) "
        "MERGE (a)-[:PREREQUISITE_FOR]->(b)",
        {"from_code": from_code, "to_code": to_code},
    )


def create_related_edge(code_a: str, code_b: str, reason: str = ""):
    run_query(
        "MATCH (a:Course {code: $code_a}), (b:Course {code: $code_b}) "
        "MERGE (a)-[:RELATED_TO {reason: $reason}]->(b)",
        {"code_a": code_a, "code_b": code_b, "reason": reason},
    )


def get_prerequisites(course_code: str) -> list[dict]:
    """Get all direct prerequisites for a course."""
    return run_query(
        "MATCH (pre:Course)-[:PREREQUISITE_FOR]->(c:Course {code: $code}) "
        "RETURN pre.code AS code, pre.title AS title",
        {"code": course_code},
    )


def get_prerequisite_chain(course_code: str) -> list[dict]:
    """Get the full prerequisite chain (all ancestors) for a course."""
    return run_query(
        "MATCH path = (pre:Course)-[:PREREQUISITE_FOR*]->(c:Course {code: $code}) "
        "WITH nodes(path) AS chain "
        "UNWIND chain AS node "
        "WITH DISTINCT node "
        "WHERE node.code <> $code "
        "RETURN node.code AS code, node.title AS title",
        {"code": course_code},
    )


def check_prerequisites_met(course_code: str, completed_codes: list[str]) -> dict:
    """Check if a student has completed all prerequisites for a course.

    Returns: {"met": bool, "missing": [{"code", "title"}]}
    """
    prereqs = get_prerequisites(course_code)
    missing = [p for p in prereqs if p["code"] not in completed_codes]
    return {"met": len(missing) == 0, "missing": missing}


def get_related_courses(course_code: str) -> list[dict]:
    """Get courses related to a given course."""
    return run_query(
        "MATCH (c:Course {code: $code})-[:RELATED_TO]-(r:Course) "
        "RETURN r.code AS code, r.title AS title, r.subject AS subject",
        {"code": course_code},
    )


def get_next_courses(course_code: str) -> list[dict]:
    """Get courses that this course is a prerequisite for."""
    return run_query(
        "MATCH (c:Course {code: $code})-[:PREREQUISITE_FOR]->(next:Course) "
        "RETURN next.code AS code, next.title AS title",
        {"code": course_code},
    )


def clear_all_graph_data():
    """Remove all nodes and relationships. Use for re-seeding."""
    run_query("MATCH (n) DETACH DELETE n")
