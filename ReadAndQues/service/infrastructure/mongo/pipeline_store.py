"""
service/infrastructure/mongo/pipeline_store.py — Atomic I/O for rss_links and pipeline_logs.
"""

import logging
from datetime import UTC, datetime, timedelta

from service.infrastructure.mongo.connection import get_collection
from service.infrastructure.utils import db_safe

logger = logging.getLogger(__name__)


# ── RSS Tracking ──────────────────────────────────────────────────────────────


@db_safe(default_return=set())
def filter_existing_rss_links(links: list[str]) -> set:
    """Check which links already exist in rss_links (last 30 days)."""
    if not links:
        return set()
    thirty_days_ago = datetime.now(UTC) - timedelta(days=30)
    cursor = get_collection("rss_links").find(
        {"link": {"$in": links}, "insert_date": {"$gte": thirty_days_ago}},
        {"link": 1},
    )
    return {doc["link"] for doc in cursor if "link" in doc}


@db_safe(default_return=0)
def batch_insert_rss_links(docs: list[dict]) -> int:
    """Batch insert new RSS link documents. Skips duplicates (ordered=False)."""
    if not docs:
        return 0
    try:
        result = get_collection("rss_links").insert_many(docs, ordered=False)
        return len(result.inserted_ids)
    except Exception as e:
        logger.warning(f"[pipeline_store] batch_insert_rss_links partial failure: {e}")
        return 0


@db_safe(default_return=[])
def get_unprocessed_rss_links(limit: int = 50) -> list[dict]:
    """Fetch RSS links not yet crawled (is_extracted=False)."""
    cursor = get_collection("rss_links").find({"is_extracted": False}).limit(limit)
    docs = []
    for d in cursor:
        d["_str_id"] = str(d["_id"])
        docs.append(d)
    return docs


@db_safe(default_return=False)
def mark_rss_link_extracted(link: str) -> bool:
    """Mark an RSS link as crawled."""
    result = get_collection("rss_links").update_one({"link": link}, {"$set": {"is_extracted": True}})
    return result.modified_count > 0


# ── Pipeline Logs ─────────────────────────────────────────────────────────────


@db_safe(default_return="")
def insert_pipeline_log(
    stage: str,
    status: str,
    message: str = "",
    document_id: str | None = None,
    url: str | None = None,
) -> str:
    log_doc = {
        "stage": stage,
        "status": status,
        "message": message,
        "document_id": document_id,
        "url": url,
        "created_at": datetime.now(UTC),
    }
    result = get_collection("pipeline_logs").insert_one(log_doc)
    return str(result.inserted_id)
