"""
database/Minio/crud.py — MinIO read/write helpers for all three Medallion tiers.

Path convention (deterministic, no DB lookup needed):
  bronze/{article_id}/raw.html
  bronze/{article_id}/meta.json
  bronze/{article_id}/meta.json.manifest.json   (optional)
  silver/{article_id}/clean.json
  gold/{article_id}/enriched.json
"""

import hashlib
import json
import logging
from io import BytesIO
from typing import Any, Dict, Optional

import urllib3

from database.Minio.connection import BRONZE_BUCKET, GOLD_BUCKET, SILVER_BUCKET, client
from service.domain.contracts import (
    RawSourceManifestContract,
    minio_bronze_prefix,
    minio_gold_prefix,
    minio_silver_prefix,
)
from service.domain.enums import MedallionStage

logger = logging.getLogger(__name__)


# ── Generic helpers ───────────────────────────────────────────────────────────

def _save(bucket: str, object_name: str, data: bytes, content_type: str = "application/octet-stream") -> bool:
    try:
        client.put_object(
            bucket_name=bucket,
            object_name=object_name,
            data=BytesIO(data),
            length=len(data),
            content_type=content_type,
        )
        return True
    except Exception as e:
        logger.error(f"MinIO save error [{bucket}/{object_name}]: {e}")
        return False


def _read(bucket: str, object_name: str) -> Optional[bytes]:
    try:
        response = client.get_object(bucket, object_name)
        data = response.read()
        response.close()
        response.release_conn()
        return data
    except urllib3.exceptions.ResponseError as err:
        logger.error(f"MinIO read ResponseError [{bucket}/{object_name}]: {err}")
    except Exception as e:
        logger.error(f"MinIO read error [{bucket}/{object_name}]: {e}")
    return None


def _read_json(bucket: str, object_name: str) -> Optional[Dict[str, Any]]:
    data = _read(bucket, object_name)
    if data:
        try:
            return json.loads(data.decode("utf-8"))
        except json.JSONDecodeError as e:
            logger.error(f"MinIO JSON decode error [{bucket}/{object_name}]: {e}")
    return None


def _save_json(bucket: str, object_name: str, payload: Dict[str, Any]) -> bool:
    data = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
    return _save(bucket, object_name, data, "application/json")


# ── Bronze ────────────────────────────────────────────────────────────────────

def save_bronze_html(article_id: str, html_content: str) -> bool:
    """Save raw HTML to bronze/{article_id}/raw.html"""
    path = f"{minio_bronze_prefix(article_id)}/raw.html"
    return _save(BRONZE_BUCKET, path, html_content.encode("utf-8"), "text/html")


def save_bronze_meta(article_id: str, meta: Dict[str, Any]) -> bool:
    """
    Save crawl metadata JSON to bronze/{article_id}/meta.json.
    Also writes a SHA-256 manifest alongside it.
    """
    path = f"{minio_bronze_prefix(article_id)}/meta.json"
    data = json.dumps(meta, ensure_ascii=False, default=str).encode("utf-8")
    success = _save(BRONZE_BUCKET, path, data, "application/json")

    if success:
        sha256_hash = hashlib.sha256(data).hexdigest()
        manifest = RawSourceManifestContract(
            article_id=article_id,
            url=meta.get("url", ""),
            sha256_hash=sha256_hash,
            raw_size_bytes=len(data),
            stage=MedallionStage.BRONZE,
        )
        manifest_path = f"{path}.manifest.json"
        _save(
            BRONZE_BUCKET,
            manifest_path,
            json.dumps(manifest.model_dump(mode="json")).encode("utf-8"),
            "application/json",
        )
    return success


def read_bronze_meta(article_id: str) -> Optional[Dict[str, Any]]:
    """Read bronze/{article_id}/meta.json"""
    path = f"{minio_bronze_prefix(article_id)}/meta.json"
    return _read_json(BRONZE_BUCKET, path)


# ── Silver ────────────────────────────────────────────────────────────────────

def save_silver_clean(article_id: str, clean_doc: Dict[str, Any]) -> bool:
    """Save cleaned article data to silver/{article_id}/clean.json"""
    path = f"{minio_silver_prefix(article_id)}/clean.json"
    return _save_json(SILVER_BUCKET, path, clean_doc)


def read_silver_clean(article_id: str) -> Optional[Dict[str, Any]]:
    """Read silver/{article_id}/clean.json"""
    path = f"{minio_silver_prefix(article_id)}/clean.json"
    return _read_json(SILVER_BUCKET, path)


# ── Gold ──────────────────────────────────────────────────────────────────────

def save_gold_enriched(article_id: str, enriched_doc: Dict[str, Any]) -> bool:
    """Save AI-enriched data to gold/{article_id}/enriched.json"""
    path = f"{minio_gold_prefix(article_id)}/enriched.json"
    return _save_json(GOLD_BUCKET, path, enriched_doc)


def read_gold_enriched(article_id: str) -> Optional[Dict[str, Any]]:
    """Read gold/{article_id}/enriched.json"""
    path = f"{minio_gold_prefix(article_id)}/enriched.json"
    return _read_json(GOLD_BUCKET, path)


# ── Generic fallback (for backward compat) ────────────────────────────────────

def read_json_from_minio(bucket_name: str, object_name: str) -> Optional[Dict[str, Any]]:
    """Generic JSON reader — use specific helpers when possible."""
    return _read_json(bucket_name, object_name)
