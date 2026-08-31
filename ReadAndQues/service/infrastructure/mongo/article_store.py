"""
service/infrastructure/mongo/article_store.py — Storage operations for article_index and homepage_sections.
Enforces standard naming conventions: create_*, get_*, list_*, update_*, delete_*.
"""

import logging
import re
from datetime import UTC, datetime, timedelta

from pymongo import ASCENDING, DESCENDING
from pymongo.errors import PyMongoError

from service.infrastructure.mongo.connection import get_collection

logger = logging.getLogger(__name__)


def _coll():
    return get_collection("article_index")


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
    """
    Insert a new article document into article_index if it does not already exist.
    """
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
    try:
        result = _coll().update_one(
            {"_id": article_id},
            {"$setOnInsert": doc},
            upsert=True,
        )
        return bool(result.acknowledged)
    except PyMongoError as e:
        logger.error(f"MongoDB error in create_article_index({article_id}): {e}")
        return False


def get_article_index(article_id: str) -> dict | None:
    """
    Fetch a single article index record by its unique article_id.
    """
    try:
        return _coll().find_one({"_id": article_id})
    except PyMongoError as e:
        logger.error(f"MongoDB error in get_article_index({article_id}): {e}")
        return None


def get_article_index_by_url(url: str) -> dict | None:
    """
    Fetch a single article index record by its canonical URL.
    """
    try:
        return _coll().find_one({"url": url})
    except PyMongoError as e:
        logger.error(f"MongoDB error in get_article_index_by_url({url}): {e}")
        return None


def update_article_stage(article_id: str, stage: str) -> bool:
    """
    Update the processing pipeline stage for an article (bronze, silver, gold).
    """
    try:
        result = _coll().update_one(
            {"_id": article_id},
            {"$set": {"stage": stage, "updated_at": datetime.now(UTC)}},
        )
        return result.modified_count > 0
    except PyMongoError as e:
        logger.error(f"MongoDB error in update_article_stage({article_id}, {stage}): {e}")
        return False


def update_ai_status(article_id: str, ai_status: str, error_message: str = "") -> bool:
    """
    Update AI enrichment status (e.g. pending, completed, failed) and error detail.
    """
    try:
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
    except PyMongoError as e:
        logger.error(f"MongoDB error in update_ai_status({article_id}, {ai_status}): {e}")
        return False


def update_article_title(article_id: str, title: str) -> bool:
    """
    Update the title for an article in article_index.
    """
    try:
        result = _coll().update_one(
            {"_id": article_id},
            {"$set": {"title": title, "updated_at": datetime.now(UTC)}},
        )
        return result.modified_count > 0
    except PyMongoError as e:
        logger.error(f"MongoDB error in update_article_title({article_id}): {e}")
        return False


def list_by_stage(stage: str, limit: int = 50) -> list[dict]:
    """
    Fetch articles currently queued at a specific pipeline stage.
    """
    try:
        cursor = _coll().find({"stage": stage}).sort("created_at", ASCENDING).limit(limit)
        return list(cursor)
    except PyMongoError as e:
        logger.error(f"MongoDB error in list_by_stage({stage}): {e}")
        return []


def list_completed_articles(limit: int = 100) -> list[dict]:
    """
    Fetch articles that have completed AI question generation, ordered by publish date.
    """
    try:
        cursor = _coll().find({"ai_status": "completed"}).sort("published_at", DESCENDING).limit(limit)
        return list(cursor)
    except PyMongoError as e:
        logger.error(f"MongoDB error in list_completed_articles: {e}")
        return []


def search_article_index_by_text(query: str, limit: int = 10) -> list[dict]:
    """
    Search completed articles in article_index by title, source_name, or URL.
    """
    query_str = (query or "").strip()
    if not query_str:
        return []
    try:
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
    except PyMongoError as e:
        logger.error(f"MongoDB error in search_article_index_by_text({query}): {e}")
        return []


def delete_article(article_id: str) -> bool:
    """
    Delete an article entry from article_index by article_id.
    """
    try:
        res = _coll().delete_one({"_id": article_id})
        return res.deleted_count > 0
    except PyMongoError as e:
        logger.error(f"MongoDB error in delete_article({article_id}): {e}")
        return False


# ── Homepage Sections Cache ───────────────────────────────────────────────────


def update_section_data(section_id: str, data: list, expires_in_hours: int = 24) -> bool:
    """
    Cache homepage section items with an expiration timestamp.
    """
    now = datetime.now(UTC)
    doc = {
        "section_id": section_id,
        "data": data,
        "updated_at": now,
        "expires_at": now + timedelta(hours=expires_in_hours),
    }
    try:
        result = get_collection("homepage_sections").update_one(
            {"section_id": section_id},
            {"$set": doc},
            upsert=True,
        )
        return bool(result.acknowledged)
    except PyMongoError as e:
        logger.error(f"MongoDB error in update_section_data({section_id}): {e}")
        return False


def get_section_data(section_id: str) -> list | None:
    """
    Retrieve cached homepage section data if not yet expired.
    """
    try:
        doc = get_collection("homepage_sections").find_one({"section_id": section_id})
        if doc and doc.get("expires_at", datetime.min.replace(tzinfo=UTC)) > datetime.now(UTC):
            return doc.get("data", [])
        return None
    except PyMongoError as e:
        logger.error(f"MongoDB error in get_section_data({section_id}): {e}")
        return None
