"""
service/infrastructure/minio/object_store.py — MinIO read/write/delete helpers for Bronze, Silver, Gold tiers.
"""

import json
import logging
from io import BytesIO
from typing import Any

from service.infrastructure.minio.connection import BRONZE_BUCKET, GOLD_BUCKET, SILVER_BUCKET, client
from service.infrastructure.utils import db_safe

logger = logging.getLogger(__name__)


def _save(bucket: str, object_name: str, data: bytes, content_type: str = "application/octet-stream") -> bool:
    client.put_object(
        bucket_name=bucket,
        object_name=object_name,
        data=BytesIO(data),
        length=len(data),
        content_type=content_type,
    )
    return True


def _read(bucket: str, object_name: str) -> bytes | None:
    try:
        response = client.get_object(bucket, object_name)
        data = response.read()
        response.close()
        response.release_conn()
        return data
    except Exception:
        return None


def _read_json(bucket: str, object_name: str) -> dict[str, Any] | None:
    data = _read(bucket, object_name)
    if data:
        return json.loads(data.decode("utf-8"))
    return None


def _save_json(bucket: str, object_name: str, payload: dict[str, Any]) -> bool:
    data = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
    return _save(bucket, object_name, data, "application/json")


# ── Bronze Tier ───────────────────────────────────────────────────────────────


@db_safe(default_return=False)
def save_bronze_html(article_id: str, html_content: str) -> bool:
    path = f"bronze/{article_id}/raw.html"
    return _save(BRONZE_BUCKET, path, html_content.encode("utf-8"), "text/html")


@db_safe(default_return=False)
def save_bronze_meta(article_id: str, meta: dict[str, Any]) -> bool:
    path = f"bronze/{article_id}/meta.json"
    data = json.dumps(meta, ensure_ascii=False, default=str).encode("utf-8")
    return _save(BRONZE_BUCKET, path, data, "application/json")


@db_safe(default_return=None)
def read_bronze_meta(article_id: str) -> dict[str, Any] | None:
    path = f"bronze/{article_id}/meta.json"
    return _read_json(BRONZE_BUCKET, path)


# ── Silver Tier ───────────────────────────────────────────────────────────────


@db_safe(default_return=False)
def save_silver_clean(article_id: str, clean_doc: dict[str, Any]) -> bool:
    path = f"silver/{article_id}/clean.json"
    return _save_json(SILVER_BUCKET, path, clean_doc)


@db_safe(default_return=None)
def read_silver_clean(article_id: str) -> dict[str, Any] | None:
    path = f"silver/{article_id}/clean.json"
    return _read_json(SILVER_BUCKET, path)


# ── Gold Tier ─────────────────────────────────────────────────────────────────


@db_safe(default_return=False)
def save_gold_enriched(article_id: str, enriched_doc: dict[str, Any]) -> bool:
    path = f"gold/{article_id}/enriched.json"
    return _save_json(GOLD_BUCKET, path, enriched_doc)


@db_safe(default_return=None)
def read_gold_enriched(article_id: str) -> dict[str, Any] | None:
    path = f"gold/{article_id}/enriched.json"
    return _read_json(GOLD_BUCKET, path)


# ── Hard Delete ───────────────────────────────────────────────────────────────


@db_safe(default_return=False)
def delete_article_objects(article_id: str) -> bool:
    """Purge bronze, silver, and gold objects for article_id."""
    paths = [
        (BRONZE_BUCKET, f"bronze/{article_id}/raw.html"),
        (BRONZE_BUCKET, f"bronze/{article_id}/meta.json"),
        (SILVER_BUCKET, f"silver/{article_id}/clean.json"),
        (GOLD_BUCKET, f"gold/{article_id}/enriched.json"),
    ]
    for bucket, path in paths:
        try:
            client.remove_object(bucket, path)
        except Exception:
            pass
    return True
