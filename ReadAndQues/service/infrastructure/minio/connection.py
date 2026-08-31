"""
service/infrastructure/minio/connection.py — MinIO Client and Bucket Configuration.
Provides clean initialization for MinIO object storage.
"""

import logging
import os

from django.conf import settings
from minio import Minio

logger = logging.getLogger(__name__)

BRONZE_BUCKET = "bronze"
SILVER_BUCKET = "silver"
GOLD_BUCKET = "gold"

_minio_client: Minio | None = None


def get_minio_client() -> Minio:
    """
    Return singleton Minio client configured from Django settings or environment variables.
    """
    global _minio_client
    if _minio_client is None:
        try:
            endpoint = getattr(settings, "MINIO_ENDPOINT", None) if settings.configured else None
            access_key = getattr(settings, "MINIO_ACCESS_KEY", None) if settings.configured else None
            secret_key = getattr(settings, "MINIO_SECRET_KEY", None) if settings.configured else None
            secure_val = getattr(settings, "MINIO_SECURE", None) if settings.configured else None
        except Exception:
            endpoint = access_key = secret_key = secure_val = None

        endpoint = endpoint or os.getenv("MINIO_ENDPOINT", "minio:9000")
        access_key = access_key or os.getenv("MINIO_ACCESS_KEY", "minioadmin")
        secret_key = secret_key or os.getenv("MINIO_SECRET_KEY", "minioadmin")
        secure = str(secure_val or os.getenv("MINIO_SECURE", "false")).lower() == "true"

        _minio_client = Minio(
            endpoint=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
        )
    return _minio_client


class _LazyMinioProxy:
    """Proxy object that delegates attribute calls to get_minio_client()."""

    def __getattr__(self, name: str):
        return getattr(get_minio_client(), name)


client = _LazyMinioProxy()


def init_buckets():
    """
    Ensure the standard Bronze, Silver, and Gold buckets exist.
    """
    c = get_minio_client()
    for bucket in [BRONZE_BUCKET, SILVER_BUCKET, GOLD_BUCKET]:
        try:
            if not c.bucket_exists(bucket):
                c.make_bucket(bucket)
                logger.info(f"Created MinIO bucket: '{bucket}'")
        except Exception as e:
            logger.warning(f"Could not initialize MinIO bucket '{bucket}': {e}")
