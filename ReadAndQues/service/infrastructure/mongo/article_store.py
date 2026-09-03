"""
service/infrastructure/mongo/article_store.py — Storage operations for gold_content and homepage_sections.

Provides pure Gold layer operations against MongoDB collection 'gold_content':
- get_gold_content(article_id)
- get_gold_content_by_url(url)
- list_gold_articles(limit, skip, sort_by)
- search_gold_content_by_text(query, limit)
- count_gold_articles()
- homepage section caching
"""

import logging
import re
from datetime import UTC, datetime, timedelta
from typing import Any

from pymongo import DESCENDING
from pymongo.errors import PyMongoError

from service.infrastructure.mongo.connection import get_collection

logger = logging.getLogger(__name__)


def _gold_coll():
    """Returns the primary MongoDB 'gold_content' collection."""
    return get_collection("gold_content")


# ── Gold Content Operations ───────────────────────────────────────────────────


def get_gold_content(article_id: str) -> dict[str, Any] | None:
    """
    Fetch a single clean article document from 'gold_content' by article_id.
    """
    if not article_id:
        return None
    try:
        doc = _gold_coll().find_one({"$or": [{"article_id": article_id}, {"_id": article_id}]})
        if doc and "_id" in doc:
            doc["_id"] = str(doc["_id"])
        return doc
    except PyMongoError as e:
        logger.error(f"MongoDB error in get_gold_content({article_id}): {e}")
        return None


def get_gold_content_by_url(url: str) -> dict[str, Any] | None:
    """
    Fetch a single clean article document from 'gold_content' by canonical URL.
    """
    if not url:
        return None
    try:
        doc = _gold_coll().find_one({"url": url})
        if doc and "_id" in doc:
            doc["_id"] = str(doc["_id"])
        return doc
    except PyMongoError as e:
        logger.error(f"MongoDB error in get_gold_content_by_url({url}): {e}")
        return None


def list_gold_articles(
    limit: int = 50,
    skip: int = 0,
    sort_by: str = "published_at",
    sort_dir: int = DESCENDING,
) -> list[dict[str, Any]]:
    """
    Fetch articles from 'gold_content' with sorting and pagination.
    """
    try:
        cursor = _gold_coll().find({"title": {"$ne": ""}}).sort(sort_by, sort_dir).skip(skip).limit(limit)
        results = []
        for doc in cursor:
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])
            results.append(doc)
        return results
    except PyMongoError as e:
        logger.error(f"MongoDB error in list_gold_articles: {e}")
        return []


def search_gold_content_by_text(query: str, limit: int = 10) -> list[dict[str, Any]]:
    """
    Search articles in 'gold_content' by title, source, or URL using regex.
    """
    query_str = (query or "").strip()
    if not query_str:
        return []
    try:
        regex = re.compile(re.escape(query_str), re.IGNORECASE)
        cursor = (
            _gold_coll()
            .find(
                {
                    "$or": [
                        {"title": regex},
                        {"source": regex},
                        {"url": regex},
                    ],
                }
            )
            .sort("published_at", DESCENDING)
            .limit(limit)
        )
        results = []
        for doc in cursor:
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])
            results.append(doc)
        return results
    except PyMongoError as e:
        logger.error(f"MongoDB error in search_gold_content_by_text({query}): {e}")
        return []


def count_gold_articles() -> int:
    """
    Count total number of documents in 'gold_content'.
    """
    try:
        return _gold_coll().count_documents({"title": {"$ne": ""}})
    except PyMongoError as e:
        logger.error(f"MongoDB error in count_gold_articles: {e}")
        return 0


def save_gold_content(doc: dict[str, Any]) -> bool:
    """
    Insert or update a clean article document in MongoDB 'gold_content'.
    """
    article_id = doc.get("article_id") or doc.get("_id")
    if not article_id:
        return False
    try:
        result = _gold_coll().update_one(
            {"$or": [{"article_id": article_id}, {"_id": article_id}]},
            {"$set": doc},
            upsert=True,
        )
        return bool(result.acknowledged)
    except PyMongoError as e:
        logger.error(f"MongoDB error in save_gold_content({article_id}): {e}")
        return False


def delete_gold_content(article_id: str) -> bool:
    """
    Delete an article entry from 'gold_content' by article_id.
    """
    try:
        res = _gold_coll().delete_one({"$or": [{"article_id": article_id}, {"_id": article_id}]})
        return res.deleted_count > 0
    except PyMongoError as e:
        logger.error(f"MongoDB error in delete_gold_content({article_id}): {e}")
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

