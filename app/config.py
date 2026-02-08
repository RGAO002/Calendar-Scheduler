from __future__ import annotations
import os
from pathlib import Path
from pydantic_settings import BaseSettings

# Load .env from project root
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    # Supabase
    supabase_url: str = ""
    supabase_key: str = ""

    # Gemini
    gemini_api_key: str = ""

    # Pinecone
    pinecone_api_key: str = ""
    pinecone_index_name: str = "evlin-courses"

    # MinIO
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "evlin_admin"
    minio_secret_key: str = "evlin_secret_key_123"
    minio_secure: bool = False

    # Neo4j
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "evlin_graph_123"

    class Config:
        env_file = str(ENV_PATH)
        env_file_encoding = "utf-8"


settings = Settings()
