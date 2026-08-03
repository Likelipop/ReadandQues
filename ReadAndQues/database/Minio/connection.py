import os
from minio import Minio
from django.conf import settings

def get_minio_client() -> Minio:
    # Read from settings or env
    endpoint = os.getenv("MINIO_ENDPOINT", getattr(settings, "MINIO_ENDPOINT", "localhost:9000"))
    access_key = os.getenv("MINIO_ACCESS_KEY", getattr(settings, "MINIO_ACCESS_KEY", "minioadmin"))
    secret_key = os.getenv("MINIO_SECRET_KEY", getattr(settings, "MINIO_SECRET_KEY", "minioadmin"))
    secure = os.getenv("MINIO_SECURE", "false").lower() == "true"
    
    if "@minio:" in endpoint:
        endpoint = endpoint.replace("@minio:", "localhost:")
        
    client = Minio(
        endpoint,
        access_key=access_key,
        secret_key=secret_key,
        secure=secure
    )
    return client

client = get_minio_client()

BRONZE_BUCKET = getattr(settings, "MINIO_BRONZE_BUCKET", "bronze")
SILVER_BUCKET = getattr(settings, "MINIO_SILVER_BUCKET", "silver")

# Initialize buckets
def init_buckets():
    for bucket in [BRONZE_BUCKET, SILVER_BUCKET]:
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)

try:
    init_buckets()
except Exception as e:
    import logging
    logging.getLogger(__name__).warning(f"Could not initialize MinIO buckets: {e}")
