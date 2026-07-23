"""
worker_service/database/Mongo/crud.py — MongoDB CRUD operations & indexes.

Abstracts MongoDB interactions for Bronze, Silver, Gold, and Logs collections.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from bson import ObjectId
from pymongo import ASCENDING, DESCENDING

from worker_service.data_pipeline.pipeline_config import (ATTEMPTS_COLLECTION,
                                                          BRONZE_COLLECTION,
                                                          GOLD_COLLECTION,
                                                          LOGS_COLLECTION,
                                                          SILVER_COLLECTION)

from .connection import (attempts_col, bronze_col, db, gold_col, logs_col,
                         silver_col)

logger = logging.getLogger(__name__)


# ── Bronze Operations ─────────────────────────────────────────────────────────


def find_existing_bronze_urls(urls: List[str]) -> Set[str]:
    """Return set of URLs already present in bronze_articles collection."""
    if not urls:
        return set()
    existing = set()
    for doc in bronze_col.find({"url": {"$in": urls}}, {"url": 1}):
        existing.add(doc["url"])
    return existing


def get_bronze_by_url(url: str) -> Optional[Dict[str, Any]]:
    """Fetch a bronze document by URL."""
    return bronze_col.find_one({"url": url})


def get_bronze_by_id(bronze_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a bronze document by ObjectId string."""
    try:
        return bronze_col.find_one({"_id": ObjectId(bronze_id)})
    except Exception:
        return None


def insert_bronze_doc(doc: Dict[str, Any]) -> str:
    """Insert a raw document into bronze_articles and return string ID."""
    result = bronze_col.insert_one(doc)
    return str(result.inserted_id)


def get_unprocessed_bronze_docs() -> List[Dict[str, Any]]:
    """Find bronze documents that have not yet been cleaned into silver_articles."""
    existing_bronze_ids = set()
    for doc in silver_col.find({}, {"bronze_id": 1}):
        bid = doc.get("bronze_id")
        if bid:
            existing_bronze_ids.add(bid)

    new_docs = []
    for doc in bronze_col.find().sort("crawled_at", -1):
        doc_id = str(doc["_id"])
        if doc_id not in existing_bronze_ids:
            doc["_str_id"] = doc_id
            new_docs.append(doc)

    return new_docs


# ── Silver Operations ─────────────────────────────────────────────────────────


def save_silver_doc(doc: Dict[str, Any]) -> str:
    """Insert a clean document into silver_articles and return string ID."""
    result = silver_col.insert_one(doc)
    return str(result.inserted_id)


def get_silver_by_id(silver_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a silver document by ObjectId string."""
    try:
        return silver_col.find_one({"_id": ObjectId(silver_id)})
    except Exception:
        return None


def get_silver_by_bronze_id(bronze_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a silver document by its bronze_id reference."""
    return silver_col.find_one({"bronze_id": bronze_id})


def get_unprocessed_silver_docs() -> List[Dict[str, Any]]:
    """Find silver documents that have not yet been processed into gold_articles."""
    existing_silver_ids = set()
    for doc in gold_col.find({}, {"silver_id": 1}):
        sid = doc.get("silver_id")
        if sid:
            existing_silver_ids.add(sid)

    new_docs = []
    for doc in silver_col.find().sort("cleaned_at", -1):
        doc_id = str(doc["_id"])
        if doc_id not in existing_silver_ids:
            doc["_str_id"] = doc_id
            new_docs.append(doc)

    return new_docs


# ── Gold Operations ───────────────────────────────────────────────────────────


def insert_gold_doc(doc: Dict[str, Any]) -> str:
    """Insert an enriched document into gold_articles and return string ID."""
    result = gold_col.insert_one(doc)
    return str(result.inserted_id)


def get_gold_by_id(gold_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a gold document by ObjectId string."""
    try:
        return gold_col.find_one({"_id": ObjectId(gold_id)})
    except Exception:
        return None


def update_gold_doc(gold_id: str, update_data: Dict[str, Any]) -> bool:
    """Update fields of an existing gold document."""
    try:
        result = gold_col.update_one({"_id": ObjectId(gold_id)}, {"$set": update_data})
        return result.modified_count > 0 or result.matched_count > 0
    except Exception as e:
        logger.error(f"Error updating gold document {gold_id}: {e}")
        return False


# ── Logs & Attempts Operations ────────────────────────────────────────────────


def insert_pipeline_log(
    stage: str,
    status: str,
    message: str,
    document_id: Optional[str] = None,
    url: Optional[str] = None,
) -> str:
    """Log pipeline action or error to pipeline_logs collection."""
    log_doc = {
        "stage": stage,
        "document_id": document_id,
        "url": url,
        "status": status,
        "message": message,
        "timestamp": datetime.now(timezone.utc),
    }
    result = logs_col.insert_one(log_doc)
    return str(result.inserted_id)


# ── Database Initialization & Indexing ────────────────────────────────────────


def init_mongo_indexes():
    """Initialize collections and create appropriate indexes for efficiency."""
    existing = db.list_collection_names()

    if BRONZE_COLLECTION not in existing:
        db.create_collection(BRONZE_COLLECTION)
        print(f"  ✅ Created collection: {BRONZE_COLLECTION}")

    bronze_col.create_index(
        [("url", ASCENDING)], unique=True, name="idx_bronze_url_unique"
    )
    bronze_col.create_index([("crawled_at", DESCENDING)], name="idx_bronze_crawled_at")

    if SILVER_COLLECTION not in existing:
        db.create_collection(SILVER_COLLECTION)
        print(f"  ✅ Created collection: {SILVER_COLLECTION}")

    silver_col.create_index(
        [("bronze_id", ASCENDING)], unique=True, name="idx_silver_bronze_id"
    )
    silver_col.create_index([("cleaned_at", DESCENDING)], name="idx_silver_cleaned_at")
    silver_col.create_index([("url", ASCENDING)], name="idx_silver_url")

    if GOLD_COLLECTION not in existing:
        db.create_collection(GOLD_COLLECTION)
        print(f"  ✅ Created collection: {GOLD_COLLECTION}")

    gold_col.create_index(
        [("silver_id", ASCENDING)], unique=True, sparse=True, name="idx_gold_silver_id"
    )
    gold_col.create_index([("status", ASCENDING)], name="idx_gold_status")
    gold_col.create_index([("user_id", ASCENDING)], name="idx_gold_user_id")
    gold_col.create_index([("created_at", DESCENDING)], name="idx_gold_created_at")
    gold_col.create_index([("theme", ASCENDING)], name="idx_gold_theme")
    gold_col.create_index([("genre", ASCENDING)], name="idx_gold_genre")
    gold_col.create_index([("url", ASCENDING)], name="idx_gold_url")

    if LOGS_COLLECTION not in existing:
        db.create_collection(LOGS_COLLECTION)
        print(f"  ✅ Created collection: {LOGS_COLLECTION}")

    logs_col.create_index([("timestamp", DESCENDING)], name="idx_logs_timestamp")
    logs_col.create_index(
        [("stage", ASCENDING), ("status", ASCENDING)], name="idx_logs_stage_status"
    )

    if ATTEMPTS_COLLECTION not in existing:
        db.create_collection(ATTEMPTS_COLLECTION)
        print(f"  ✅ Created collection: {ATTEMPTS_COLLECTION}")

    attempts_col.create_index(
        [("user_id", ASCENDING), ("submitted_at", DESCENDING)], name="idx_attempts_user"
    )
    attempts_col.create_index(
        [("gold_article_id", ASCENDING)], name="idx_attempts_article"
    )
    print("  📇 All MongoDB indexes initialized successfully.")
