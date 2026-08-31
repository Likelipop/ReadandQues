"""
service/infrastructure/minio/object_store.py — MinIO read/write/delete helpers for Bronze, Silver, Gold tiers.
Enforces standardized prefix naming: save_*, read_*, delete_*.
Uses native MinIO S3Error handling.
"""

import json
import logging
from io import BytesIO
from typing import Any

from minio.error import S3Error

from service.infrastructure.minio.connection import BRONZE_BUCKET, GOLD_BUCKET, SILVER_BUCKET, client

logger = logging.getLogger(__name__)


# ── Generic I/O Helpers ───────────────────────────────────────────────────────


def save_bytes(bucket: str, object_name: str, data: bytes, content_type: str = "application/octet-stream") -> bool:
    """Save raw bytes to a MinIO bucket object."""
    try:
        client.put_object(
            bucket_name=bucket,
            object_name=object_name,
            data=BytesIO(data),
            length=len(data),
            content_type=content_type,
        )
        return True
    except S3Error as e:
        logger.error(f"MinIO S3Error saving {bucket}/{object_name}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error saving {bucket}/{object_name}: {e}")
        return False


def read_bytes(bucket: str, object_name: str) -> bytes | None:
    """Read raw bytes from a MinIO bucket object."""
    try:
        response = client.get_object(bucket, object_name)
        data = response.read()
        response.close()
        response.release_conn()
        return data
    except S3Error as e:
        if e.code == "NoSuchKey":
            logger.debug(f"Object not found: {bucket}/{object_name}")
        else:
            logger.error(f"MinIO S3Error reading {bucket}/{object_name}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error reading {bucket}/{object_name}: {e}")
        return None


def save_text(bucket: str, object_name: str, text: str, content_type: str = "text/plain") -> bool:
    """Save a UTF-8 text string to MinIO."""
    return save_bytes(bucket, object_name, text.encode("utf-8"), content_type)


def read_text(bucket: str, object_name: str) -> str | None:
    """Read a UTF-8 text string from MinIO."""
    data = read_bytes(bucket, object_name)
    return data.decode("utf-8") if data is not None else None


def save_json(bucket: str, object_name: str, payload: dict[str, Any]) -> bool:
    """Serialize and save a JSON payload to MinIO."""
    try:
        data = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
        return save_bytes(bucket, object_name, data, "application/json")
    except Exception as e:
        logger.error(f"JSON serialization error for {bucket}/{object_name}: {e}")
        return False


def read_json(bucket: str, object_name: str) -> dict[str, Any] | None:
    """Read and deserialize a JSON document from MinIO."""
    raw = read_bytes(bucket, object_name)
    if raw is None:
        return None
    try:
        return json.loads(raw.decode("utf-8"))
    except Exception as e:
        logger.error(f"JSON deserialization error for {bucket}/{object_name}: {e}")
        return None


# ── Bronze Tier (Raw HTML & Metadata) ─────────────────────────────────────────


def save_bronze_html(article_id: str, html_content: str) -> bool:
    """Save raw crawled HTML for an article into Bronze bucket."""
    return save_text(BRONZE_BUCKET, f"bronze/{article_id}/raw.html", html_content, "text/html")


def save_bronze_meta(article_id: str, meta: dict[str, Any]) -> bool:
    """Save raw extraction metadata into Bronze bucket."""
    return save_json(BRONZE_BUCKET, f"bronze/{article_id}/meta.json", meta)


def read_bronze_meta(article_id: str) -> dict[str, Any] | None:
    """Read raw extraction metadata from Bronze bucket."""
    return read_json(BRONZE_BUCKET, f"bronze/{article_id}/meta.json")


# ── Silver Tier (Cleaned Text & Structural Metadata) ──────────────────────────


def save_silver_clean(article_id: str, clean_doc: dict[str, Any]) -> bool:
    """Save cleaned and validated article document into Silver bucket."""
    return save_json(SILVER_BUCKET, f"silver/{article_id}/clean.json", clean_doc)


def read_silver_clean(article_id: str) -> dict[str, Any] | None:
    """Read cleaned article document from Silver bucket."""
    return read_json(SILVER_BUCKET, f"silver/{article_id}/clean.json")


# ── Gold Tier (Enriched Article with Questions & Vocabulary) ──────────────────


def save_gold_enriched(article_id: str, enriched_doc: dict[str, Any]) -> bool:
    """Save fully AI-enriched article document into Gold bucket."""
    return save_json(GOLD_BUCKET, f"gold/{article_id}/enriched.json", enriched_doc)


def read_gold_enriched(article_id: str) -> dict[str, Any] | None:
    """Read fully AI-enriched article document from Gold bucket."""
    return read_json(GOLD_BUCKET, f"gold/{article_id}/enriched.json")


# ── Cleanup ───────────────────────────────────────────────────────────────────


def delete_article_objects(article_id: str) -> bool:
    """Purge all bronze, silver, and gold tier objects associated with an article_id."""
    paths = [
        (BRONZE_BUCKET, f"bronze/{article_id}/raw.html"),
        (BRONZE_BUCKET, f"bronze/{article_id}/meta.json"),
        (SILVER_BUCKET, f"silver/{article_id}/clean.json"),
        (GOLD_BUCKET, f"gold/{article_id}/enriched.json"),
    ]
    for bucket, path in paths:
        try:
            client.remove_object(bucket, path)
        except S3Error as e:
            if e.code != "NoSuchKey":
                logger.warning(f"MinIO S3Error deleting {bucket}/{path}: {e}")
        except Exception as e:
            logger.warning(f"Error deleting {bucket}/{path}: {e}")
    return True
