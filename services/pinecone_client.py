from typing import Optional
from pinecone import Pinecone
from app.config import settings

_client: Optional[Pinecone] = None


def get_pinecone() -> Pinecone:
    global _client
    if _client is None:
        if not settings.pinecone_api_key:
            raise ValueError("PINECONE_API_KEY must be set in .env")
        _client = Pinecone(api_key=settings.pinecone_api_key)
    return _client


def get_index():
    pc = get_pinecone()
    return pc.Index(settings.pinecone_index_name)
