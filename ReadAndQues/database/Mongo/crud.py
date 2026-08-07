"""
database/Mongo/crud.py — Shared CRUD helpers.

Scope: RSS tracking, pipeline logs, exam attempts, user paraphrase cache,
       and article lookups (via new article_index + exams collections).

Legacy Medallion pipeline helpers (bronze_docs, silver_docs, gold_docs) have
been moved to article_index.py and exams.py. This file no longer contains
any `distinct + $nin` patterns.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId

from .connection import (
    attempts_collection,
    pipeline_logs_collection,
    rss_links_collection,
    smart_paraphrase_collection,
)

logger = logging.getLogger(__name__)


# ── Article lookups (new schema) ──────────────────────────────────────────────

def get_article_document_by_id(pk: str) -> Optional[dict]:
    """
    Fetch a merged article view: article_index metadata + exam data.
    pk can be either an article_id (art_xxx) or a legacy ObjectId string.
    """
    from .article_index import get_article_index
    from .exams import get_exam

    # Try new schema first
    doc = get_article_index(pk)
    if doc:
        exam = get_exam(pk) or {}
        merged = {**exam, **doc}
        merged["id"] = pk
        merged["article_id"] = pk
        # UI compat: expose original_text from exam doc if present
        if "original_text" not in merged and "full_text" in merged:
            merged["original_text"] = merged["full_text"]
        return merged

    # Fallback to legacy collection for data not yet migrated
    from .connection import article_collection
    try:
        if ObjectId.is_valid(pk):
            legacy = article_collection.find_one({"_id": ObjectId(pk)})
            if legacy:
                legacy["id"] = str(legacy["_id"])
                return legacy
    except Exception as e:
        logger.error(f"[crud] get_article_document_by_id fallback failed for {pk}: {e}")
    return None


def get_article_document_by_url(url: str) -> Optional[dict]:
    """Fetch the most recent article document by URL."""
    from .article_index import get_article_index_by_url
    doc = get_article_index_by_url(url)
    if doc:
        doc["id"] = doc["_id"]
        doc["article_id"] = doc["_id"]
        return doc

    # Fallback to legacy
    from .connection import article_collection
    try:
        legacy = article_collection.find_one({"url": url}, sort=[("created_at", -1)])
        if legacy:
            legacy["id"] = str(legacy["_id"])
            return legacy
    except Exception as e:
        logger.error(f"[crud] get_article_document_by_url fallback failed: {e}")
    return None


def get_completed_articles(limit: int = None, theme: str = None, genre: str = None) -> list:
    """
    Fetch articles that completed AI enrichment.
    Uses exams collection for theme/genre filtering.
    """
    from .exams import list_exams
    from .article_index import get_article_index

    exam_docs = list_exams(theme=theme, genre=genre, limit=limit or 100)
    results = []
    for exam in exam_docs:
        article_id = exam.get("article_id")
        index_doc = get_article_index(article_id) or {}
        merged = {**exam, **index_doc}
        merged["id"] = article_id
        results.append(merged)
    return results


def update_article_document(pk: str, updates: dict) -> bool:
    """
    Update article metadata. Routes to article_index for stage/status fields,
    falls back to legacy collection for unrecognized documents.
    """
    from .article_index import get_article_index
    from .connection import article_index_collection

    doc = get_article_index(pk)
    if doc:
        updates["updated_at"] = datetime.now(timezone.utc)
        try:
            result = article_index_collection.update_one(
                {"_id": pk}, {"$set": updates}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"[crud] update_article_document failed for {pk}: {e}")
            return False

    # Fallback for legacy documents
    from .connection import article_collection
    try:
        if ObjectId.is_valid(pk):
            result = article_collection.update_one(
                {"_id": ObjectId(pk)}, {"$set": updates}
            )
            return result.modified_count > 0
    except Exception as e:
        logger.error(f"[crud] update_article_document legacy fallback failed: {e}")
    return False


def insert_article_document(data: dict) -> str:
    """
    Legacy insert — used by readspace/services.py import_article().
    Will be replaced by article_index.create_article_index() in Phase 7.
    """
    from .connection import article_collection
    try:
        result = article_collection.insert_one(data)
        return str(result.inserted_id)
    except Exception as e:
        logger.error(f"[crud] insert_article_document failed: {e}")
        return ""


def get_articles_by_ids(ids: List[str]) -> List[dict]:
    """Fetch multiple article index docs by list of article_ids. Preserves order."""
    from .article_index import get_article_index
    from .exams import get_exams_by_article_ids

    if not ids:
        return []

    exam_map = get_exams_by_article_ids(ids)
    results = []
    for article_id in ids:
        index_doc = get_article_index(article_id)
        if index_doc:
            exam = exam_map.get(article_id, {})
            merged = {**exam, **index_doc}
            merged["id"] = article_id
            results.append(merged)
    return results


# ── RSS Tracking ──────────────────────────────────────────────────────────────

def filter_existing_rss_links(links: List[str]) -> set:
    """Check which links already exist in rss_links (last 30 days)."""
    if not links:
        return set()
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    try:
        cursor = rss_links_collection.find(
            {"link": {"$in": links}, "insert_date": {"$gte": thirty_days_ago}},
            {"link": 1},
        )
        return {doc["link"] for doc in cursor if "link" in doc}
    except Exception as e:
        logger.error(f"[crud] filter_existing_rss_links failed: {e}")
        return set()


def batch_insert_rss_links(docs: List[dict]) -> int:
    """Batch insert new RSS link documents. Skips duplicates (ordered=False)."""
    if not docs:
        return 0
    try:
        result = rss_links_collection.insert_many(docs, ordered=False)
        return len(result.inserted_ids)
    except Exception as e:
        logger.warning(f"[crud] batch_insert_rss_links partial failure (may be duplicates): {e}")
        return 0


def get_unprocessed_rss_links(limit: int = 50) -> List[dict]:
    """Fetch RSS links not yet crawled (is_extracted=False)."""
    try:
        cursor = rss_links_collection.find({"is_extracted": False}).limit(limit)
        docs = []
        for d in cursor:
            d["_str_id"] = str(d["_id"])
            docs.append(d)
        return docs
    except Exception as e:
        logger.error(f"[crud] get_unprocessed_rss_links failed: {e}")
        return []


def mark_rss_link_extracted(link: str) -> bool:
    """Mark an RSS link as crawled."""
    try:
        result = rss_links_collection.update_one(
            {"link": link}, {"$set": {"is_extracted": True}}
        )
        return result.modified_count > 0
    except Exception as e:
        logger.error(f"[crud] mark_rss_link_extracted failed for {link}: {e}")
        return False


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
    try:
        result = pipeline_logs_collection.insert_one(log_doc)
        return str(result.inserted_id)
    except Exception as e:
        logger.error(f"[crud] insert_pipeline_log failed: {e}")
        return ""


# ── Exam Attempts ─────────────────────────────────────────────────────────────

def save_exam_attempt(data: dict) -> str:
    try:
        result = attempts_collection.insert_one(data)
        return str(result.inserted_id)
    except Exception as e:
        logger.error(f"[crud] save_exam_attempt failed: {e}")
        return ""


def get_user_attempted_article_ids(user_id: int) -> set:
    """Return a set of article_id strings for which user has at least one attempt."""
    if not user_id:
        return set()
    try:
        cursor = attempts_collection.find({"user_id": user_id}, {"article_id": 1})
        return {str(doc["article_id"]) for doc in cursor if "article_id" in doc}
    except Exception as e:
        logger.error(f"[crud] get_user_attempted_article_ids failed: {e}")
        return set()


# ── Smart Paraphrase Cache ────────────────────────────────────────────────────

def find_exact_paraphrase(
    article_id: str, paragraph_hash: str, user_start_index: int, user_end_index: int
) -> Optional[dict]:
    try:
        query = {
            "article_id": article_id,
            "paragraph_hash": paragraph_hash,
            "user_start_index": user_start_index,
            "user_end_index": user_end_index,
        }
        doc = smart_paraphrase_collection.find_one(query)
        if doc:
            doc["id"] = str(doc["_id"])
            del doc["_id"]
            return doc
        return None
    except Exception as e:
        logger.error(f"[crud] find_exact_paraphrase failed: {e}")
        return None


def save_smart_paraphrase(data: dict) -> str:
    try:
        result = smart_paraphrase_collection.insert_one(data)
        return str(result.inserted_id)
    except Exception as e:
        logger.error(f"[crud] save_smart_paraphrase failed: {e}")
        return ""
