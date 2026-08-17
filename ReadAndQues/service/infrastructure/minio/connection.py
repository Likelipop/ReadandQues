"""
service/infrastructure/minio/connection.py — MinIO client singleton.
"""

import logging
import os

from django.conf import settings
from minio import Minio

logger = logging.getLogger(__name__)

_minio_client: Minio | None = None


def get_setting(name: str, default: str) -> str:
    try:
        if settings.configured:
            val = getattr(settings, name, None)
            if val:
                return str(val)
    except Exception:
        pass
    return os.getenv(name, default)


BRONZE_BUCKET = get_setting("MINIO_BRONZE_BUCKET", "bronze")
SILVER_BUCKET = get_setting("MINIO_SILVER_BUCKET", "silver")
GOLD_BUCKET = get_setting("MINIO_GOLD_BUCKET", "gold")


def get_minio_client() -> Minio:
    global _minio_client
    if _minio_client is None:
        endpoint = get_setting("MINIO_ENDPOINT", "minio:9000")
        access_key = get_setting("MINIO_ACCESS_KEY", "minioadmin")
        secret_key = get_setting("MINIO_SECRET_KEY", "minioadmin")
        secure_str = get_setting("MINIO_SECURE", "false")
        secure = str(secure_str).lower() == "true"

        _minio_client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure
        )
    return _minio_client


class LazyMinioClient:
    """Proxy object that delays MinIO client initialization until first attribute access."""

    def __getattr__(self, name: str):
        return getattr(get_minio_client(), name)


client = LazyMinioClient()


def init_buckets():
    """Explicit initializer for MinIO buckets (called on demand, not on import)."""
    c = get_minio_client()
    for bucket in [BRONZE_BUCKET, SILVER_BUCKET, GOLD_BUCKET]:
        try:
            if not c.bucket_exists(bucket):
                c.make_bucket(bucket)
                logger.info(f"Created MinIO bucket: '{bucket}'")
        except Exception as e:
            logger.warning(f"Could not initialize MinIO bucket '{bucket}': {e}")
