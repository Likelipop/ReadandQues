"""
database/Minio/crud.py — Pure MinIO read/write helpers for Medallion storage tiers.
Zero domain dependencies. Pure I/O thô.
"""

import hashlib
import json
import logging
from io import BytesIO
from typing import Any, Dict, Optional
import urllib3

from database.Minio.connection import BRONZE_BUCKET, GOLD_BUCKET, SILVER_BUCKET, client

logger = logging.getLogger(__name__)


# ── Generic helpers ───────────────────────────────────────────────────────────

def _save(bucket: str, object_name: str, data: bytes, content_type: str = "application/octet-stream") -> bool:
    client.put_object(
        bucket_name=bucket,
        object_name=object_name,
        data=BytesIO(data),
        length=len(data),
        content_type=content_type,
    )
    return True


def _read(bucket: str, object_name: str) -> Optional[bytes]:
    try:
        response = client.get_object(bucket, object_name)
        data = response.read()
        response.close()
        response.release_conn()
        return data
    except urllib3.exceptions.ResponseError:
        return None
    except Exception:
        return None


def _read_json(bucket: str, object_name: str) -> Optional[Dict[str, Any]]:
    data = _read(bucket, object_name)
    if data:
        return json.loads(data.decode("utf-8"))
    return None


def _save_json(bucket: str, object_name: str, payload: Dict[str, Any]) -> bool:
    data = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
    return _save(bucket, object_name, data, "application/json")


# ── Bronze Tier ───────────────────────────────────────────────────────────────

def save_bronze_html(article_id: str, html_content: str) -> bool:
    """Save raw HTML to bronze/{article_id}/raw.html"""
    path = f"bronze/{article_id}/raw.html"
    return _save(BRONZE_BUCKET, path, html_content.encode("utf-8"), "text/html")


def save_bronze_meta(article_id: str, meta: Dict[str, Any]) -> bool:
    """Save crawl metadata JSON to bronze/{article_id}/meta.json."""
    path = f"bronze/{article_id}/meta.json"
    data = json.dumps(meta, ensure_ascii=False, default=str).encode("utf-8")
    return _save(BRONZE_BUCKET, path, data, "application/json")


def read_bronze_meta(article_id: str) -> Optional[Dict[str, Any]]:
    """Read bronze/{article_id}/meta.json"""
    path = f"bronze/{article_id}/meta.json"
    return _read_json(BRONZE_BUCKET, path)


# ── Silver Tier ───────────────────────────────────────────────────────────────

def save_silver_clean(article_id: str, clean_doc: Dict[str, Any]) -> bool:
    """Save cleaned article data to silver/{article_id}/clean.json"""
    path = f"silver/{article_id}/clean.json"
    return _save_json(SILVER_BUCKET, path, clean_doc)


def read_silver_clean(article_id: str) -> Optional[Dict[str, Any]]:
    """Read silver/{article_id}/clean.json"""
    path = f"silver/{article_id}/clean.json"
    return _read_json(SILVER_BUCKET, path)


# ── Gold Tier ─────────────────────────────────────────────────────────────────

def save_gold_enriched(article_id: str, enriched_doc: Dict[str, Any]) -> bool:
    """Save AI-enriched data to gold/{article_id}/enriched.json"""
    path = f"gold/{article_id}/enriched.json"
    return _save_json(GOLD_BUCKET, path, enriched_doc)


def read_gold_enriched(article_id: str) -> Optional[Dict[str, Any]]:
    """Read gold/{article_id}/enriched.json"""
    path = f"gold/{article_id}/enriched.json"
    return _read_json(GOLD_BUCKET, path)


# ── Generic fallback ──────────────────────────────────────────────────────────

def read_json_from_minio(bucket_name: str, object_name: str) -> Optional[Dict[str, Any]]:
    """Generic JSON reader."""
    return _read_json(bucket_name, object_name)
