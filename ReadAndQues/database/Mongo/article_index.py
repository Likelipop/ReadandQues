"""
database/Mongo/article_index.py — Pure atomic I/O for the `article_index` collection.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pymongo import ASCENDING, DESCENDING
from database.Mongo.connection import get_collection


def _coll():
    return get_collection("article_index")


def create_article_index(
    article_id: str,
    url: str,
    title: str = "",
    source_name: str = "",
    image_url: Optional[str] = None,
    published_at: Optional[datetime] = None,
    stage: str = "bronze",
    ai_status: str = "pending",
) -> bool:
    """Insert a new article index document (idempotent upsert)."""
    now = datetime.now(timezone.utc)
    doc = {
        "_id": article_id,
        "url": url,
        "title": title,
        "source_name": source_name,
        "image_url": image_url,
        "published_at": published_at,
        "stage": stage,
        "ai_status": ai_status,
        "error_message": "",
        "created_at": now,
        "updated_at": now,
    }
    result = _coll().update_one(
        {"_id": article_id},
        {"$setOnInsert": doc},
        upsert=True,
    )
    return result.acknowledged


def get_article_index(article_id: str) -> Optional[dict]:
    """Fetch a single article index document by article_id."""
    return _coll().find_one({"_id": article_id})


def get_article_index_by_url(url: str) -> Optional[dict]:
    """Fetch a single article index document by URL."""
    return _coll().find_one({"url": url})


def update_article_stage(article_id: str, stage: str) -> bool:
    """Advance an article to a new stage."""
    result = _coll().update_one(
        {"_id": article_id},
        {"$set": {"stage": stage, "updated_at": datetime.now(timezone.utc)}},
    )
    return result.modified_count > 0


def update_ai_status(article_id: str, ai_status: str, error_message: str = "") -> bool:
    """Update AI enrichment status and optional error message."""
    result = _coll().update_one(
        {"_id": article_id},
        {
            "$set": {
                "ai_status": ai_status,
                "error_message": error_message,
                "updated_at": datetime.now(timezone.utc),
            }
        },
    )
    return result.modified_count > 0


def update_article_title(article_id: str, title: str) -> bool:
    """Update title for an article."""
    result = _coll().update_one(
        {"_id": article_id},
        {"$set": {"title": title, "updated_at": datetime.now(timezone.utc)}},
    )
    return result.modified_count > 0


def list_by_stage(stage: str, limit: int = 50) -> List[dict]:
    """Fetch articles at a given stage."""
    cursor = (
        _coll()
        .find({"stage": stage})
        .sort("created_at", ASCENDING)
        .limit(limit)
    )
    return list(cursor)


def list_completed_articles(limit: int = 100) -> List[dict]:
    """Fetch articles that have completed AI enrichment."""
    cursor = (
        _coll()
        .find({"ai_status": "completed"})
        .sort("published_at", DESCENDING)
        .limit(limit)
    )
    return list(cursor)


def search_article_index_by_text(query: str, limit: int = 10) -> List[dict]:
    """Search articles in article_index by title, source_name, or url using regex."""
    import re
    query_str = (query or "").strip()
    if not query_str:
        return []
    regex = re.compile(re.escape(query_str), re.IGNORECASE)
    cursor = (
        _coll()
        .find({
            "$or": [
                {"title": regex},
                {"source_name": regex},
                {"url": regex},
            ]
        })
        .sort("created_at", DESCENDING)
        .limit(limit)
    )
    return list(cursor)
