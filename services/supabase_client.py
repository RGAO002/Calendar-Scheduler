from typing import Optional
from supabase import create_client, Client
from app.config import settings

_client: Optional[Client] = None


def get_supabase() -> Client:
    global _client
    if _client is None:
        if not settings.supabase_url or not settings.supabase_key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_KEY must be set in .env"
            )
        _client = create_client(settings.supabase_url, settings.supabase_key)
    return _client
