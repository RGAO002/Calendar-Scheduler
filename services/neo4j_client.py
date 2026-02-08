from neo4j import GraphDatabase
from app.config import settings

_driver = None


def get_neo4j_driver():
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
    return _driver


def close_neo4j():
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None


def run_query(query: str, parameters: dict = None):
    driver = get_neo4j_driver()
    with driver.session() as session:
        result = session.run(query, parameters or {})
        return [record.data() for record in result]
