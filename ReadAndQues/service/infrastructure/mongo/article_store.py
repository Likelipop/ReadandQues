"""
service/infrastructure/mongo/article_store.py — Atomic I/O for article_index, homepage_sections, smart_paraphrase_cache.
"""

import re
from datetime import UTC, datetime, timedelta

from pymongo import ASCENDING, DESCENDING

from service.infrastructure.mongo.connection import get_collection
from service.infrastructure.utils import db_safe


def _coll():
    return get_collection("article_index")


@db_safe(default_return=False)
def create_article_index(
    article_id: str,
    url: str,
    title: str = "",
    source_name: str = "",
    image_url: str | None = None,
    published_at: datetime | None = None,
    stage: str = "bronze",
    ai_status: str = "pending",
) -> bool:
    """Insert a new article index document (idempotent upsert)."""
    now = datetime.now(UTC)
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


@db_safe(default_return=None)
def get_article_index(article_id: str) -> dict | None:
    """Fetch a single article index document by article_id."""
    return _coll().find_one({"_id": article_id})


@db_safe(default_return=None)
def get_article_index_by_url(url: str) -> dict | None:
    """Fetch a single article index document by URL."""
    return _coll().find_one({"url": url})


@db_safe(default_return=False)
def update_article_stage(article_id: str, stage: str) -> bool:
    """Advance an article to a new stage."""
    result = _coll().update_one(
        {"_id": article_id},
        {"$set": {"stage": stage, "updated_at": datetime.now(UTC)}},
    )
    return result.modified_count > 0


@db_safe(default_return=False)
def update_ai_status(article_id: str, ai_status: str, error_message: str = "") -> bool:
    """Update AI enrichment status and optional error message."""
    result = _coll().update_one(
        {"_id": article_id},
        {
            "$set": {
                "ai_status": ai_status,
                "error_message": error_message,
                "updated_at": datetime.now(UTC),
            }
        },
    )
    return result.modified_count > 0


@db_safe(default_return=False)
def update_article_title(article_id: str, title: str) -> bool:
    """Update title for an article."""
    result = _coll().update_one(
        {"_id": article_id},
        {"$set": {"title": title, "updated_at": datetime.now(UTC)}},
    )
    return result.modified_count > 0


@db_safe(default_return=[])
def list_by_stage(stage: str, limit: int = 50) -> list[dict]:
    """Fetch articles at a given stage."""
    cursor = _coll().find({"stage": stage}).sort("created_at", ASCENDING).limit(limit)
    return list(cursor)


@db_safe(default_return=[])
def list_completed_articles(limit: int = 100) -> list[dict]:
    """Fetch articles that have completed AI enrichment."""
    cursor = _coll().find({"ai_status": "completed"}).sort("published_at", DESCENDING).limit(limit)
    return list(cursor)


@db_safe(default_return=[])
def search_article_index_by_text(query: str, limit: int = 10) -> list[dict]:
    """Search completed articles in article_index by title, source_name, or url using regex."""
    query_str = (query or "").strip()
    if not query_str:
        return []
    regex = re.compile(re.escape(query_str), re.IGNORECASE)
    cursor = (
        _coll()
        .find(
            {
                "ai_status": "completed",
                "$or": [
                    {"title": regex},
                    {"source_name": regex},
                    {"url": regex},
                ],
            }
        )
        .sort("created_at", DESCENDING)
        .limit(limit)
    )
    return list(cursor)


@db_safe(default_return=False)
def delete_article(article_id: str) -> bool:
    """Delete article_index entry by article_id."""
    res = _coll().delete_one({"_id": article_id})
    return res.deleted_count > 0


# ── Homepage Sections Cache ───────────────────────────────────────────────────


@db_safe(default_return=False)
def update_section_data(section_id: str, data: list, expires_in_hours: int = 24) -> bool:
    now = datetime.now(UTC)
    doc = {
        "section_id": section_id,
        "data": data,
        "updated_at": now,
        "expires_at": now + timedelta(hours=expires_in_hours),
    }
    result = get_collection("homepage_sections").update_one(
        {"section_id": section_id},
        {"$set": doc},
        upsert=True,
    )
    return result.acknowledged


@db_safe(default_return=None)
def get_section_data(section_id: str) -> list | None:
    doc = get_collection("homepage_sections").find_one({"section_id": section_id})
    if doc and doc.get("expires_at", datetime.min.replace(tzinfo=UTC)) > datetime.now(UTC):
        return doc.get("data", [])
    return None
