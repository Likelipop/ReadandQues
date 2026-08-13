"""
database/Mongo/crud.py — Shared CRUD helpers.

Scope: RSS tracking, pipeline logs, and smart paraphrase cache.
Pure atomic I/O. Exceptions propagate to Repository @db_safe boundary.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from database.Mongo.connection import get_collection

logger = logging.getLogger(__name__)


# ── RSS Tracking ──────────────────────────────────────────────────────────────

def filter_existing_rss_links(links: List[str]) -> set:
    """Check which links already exist in rss_links (last 30 days)."""
    if not links:
        return set()
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    cursor = get_collection("rss_links").find(
        {"link": {"$in": links}, "insert_date": {"$gte": thirty_days_ago}},
        {"link": 1},
    )
    return {doc["link"] for doc in cursor if "link" in doc}


def batch_insert_rss_links(docs: List[dict]) -> int:
    """Batch insert new RSS link documents. Skips duplicates (ordered=False)."""
    if not docs:
        return 0
    try:
        result = get_collection("rss_links").insert_many(docs, ordered=False)
        return len(result.inserted_ids)
    except Exception as e:
        logger.warning(f"[crud] batch_insert_rss_links partial failure (may be duplicates): {e}")
        return 0


def get_unprocessed_rss_links(limit: int = 50) -> List[dict]:
    """Fetch RSS links not yet crawled (is_extracted=False)."""
    cursor = get_collection("rss_links").find({"is_extracted": False}).limit(limit)
    docs = []
    for d in cursor:
        d["_str_id"] = str(d["_id"])
        docs.append(d)
    return docs


def mark_rss_link_extracted(link: str) -> bool:
    """Mark an RSS link as crawled."""
    result = get_collection("rss_links").update_one(
        {"link": link}, {"$set": {"is_extracted": True}}
    )
    return result.modified_count > 0


# ── Pipeline Logs ─────────────────────────────────────────────────────────────

def insert_pipeline_log(
    stage: str,
    status: str,
    message: str = "",
    document_id: Optional[str] = None,
    url: Optional[str] = None,
) -> str:
    log_doc = {
        "stage": stage,
        "status": status,
        "message": message,
        "document_id": document_id,
        "url": url,
        "created_at": datetime.now(timezone.utc),
    }
    result = get_collection("pipeline_logs").insert_one(log_doc)
    return str(result.inserted_id)


# ── Smart Paraphrase Cache ────────────────────────────────────────────────────

def find_exact_paraphrase(
    article_id: str, paragraph_hash: str, user_start_index: int, user_end_index: int
) -> Optional[dict]:
    query = {
        "article_id": article_id,
        "paragraph_hash": paragraph_hash,
        "user_start_index": user_start_index,
        "user_end_index": user_end_index,
    }
    doc = get_collection("smart_paraphrase_cache").find_one(query)
    if doc:
        doc["id"] = str(doc["_id"])
        del doc["_id"]
        return doc
    return None


def save_smart_paraphrase(data: dict) -> str:
    result = get_collection("smart_paraphrase_cache").insert_one(data)
    return str(result.inserted_id)
