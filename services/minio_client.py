from typing import Optional
from minio import Minio
from app.config import settings

_client: Optional[Minio] = None


def get_minio() -> Minio:
    global _client
    if _client is None:
        _client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
    return _client


def ensure_bucket(bucket_name: str):
    client = get_minio()
    if not client.bucket_exists(bucket_name):
        client.make_bucket(bucket_name)
