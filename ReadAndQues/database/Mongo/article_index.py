"""
database/Mongo/article_index.py — CRUD for the `article_index` collection.

Design:
  - _id = article_id (deterministic, derived from SHA-256(url))
  - Contains only lightweight metadata: url, title, stage, ai_status, timestamps
  - Full content lives in MinIO (bronze/silver/gold buckets)
  - `stage` field replaces the old `distinct + $nin` anti-pattern for tracking pipeline progress
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional

from pymongo import ASCENDING, DESCENDING, ReturnDocument

from database.Mongo.connection import article_index_collection
from service.domain.enums import AIStatus, ArticleStage

logger = logging.getLogger(__name__)


def create_article_index(
    article_id: str,
    url: str,
    title: str = "",
    source_name: str = "",
    image_url: Optional[str] = None,
    published_at: Optional[datetime] = None,
) -> bool:
    """
    Insert a new article index document.
    Uses upsert to be idempotent — safe to call multiple times for the same URL.
    """
    now = datetime.now(timezone.utc)
    doc = {
        "_id": article_id,
        "url": url,
        "title": title,
        "source_name": source_name,
        "image_url": image_url,
        "published_at": published_at,
        "stage": ArticleStage.BRONZE.value,
        "ai_status": AIStatus.PENDING_GENERATION.value,
        "error_message": "",
        "created_at": now,
        "updated_at": now,
    }
    try:
        article_index_collection.update_one(
            {"_id": article_id},
            {"$setOnInsert": doc},
            upsert=True,
        )
        return True
    except Exception as e:
        logger.error(f"[article_index] create failed for {article_id}: {e}")
        return False


def get_article_index(article_id: str) -> Optional[dict]:
    """Fetch a single article index document by article_id."""
    try:
        return article_index_collection.find_one({"_id": article_id})
    except Exception as e:
        logger.error(f"[article_index] get failed for {article_id}: {e}")
        return None


def get_article_index_by_url(url: str) -> Optional[dict]:
    """Fetch a single article index document by URL."""
    try:
        return article_index_collection.find_one({"url": url})
    except Exception as e:
        logger.error(f"[article_index] get_by_url failed for {url}: {e}")
        return None


def update_article_stage(article_id: str, stage: ArticleStage) -> bool:
    """Advance an article to the next Medallion stage."""
    try:
        result = article_index_collection.update_one(
            {"_id": article_id},
            {"$set": {"stage": stage.value, "updated_at": datetime.now(timezone.utc)}},
        )
        return result.modified_count > 0
    except Exception as e:
        logger.error(f"[article_index] update_stage failed for {article_id}: {e}")
        return False


def update_ai_status(article_id: str, ai_status: AIStatus, error_message: str = "") -> bool:
    """Update the AI enrichment status and optional error message."""
    try:
        result = article_index_collection.update_one(
            {"_id": article_id},
            {
                "$set": {
                    "ai_status": ai_status.value,
                    "error_message": error_message,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )
        return result.modified_count > 0
    except Exception as e:
        logger.error(f"[article_index] update_ai_status failed for {article_id}: {e}")
        return False


def update_article_title(article_id: str, title: str) -> bool:
    """Update title — called after crawl extracts the real title."""
    try:
        article_index_collection.update_one(
            {"_id": article_id},
            {"$set": {"title": title, "updated_at": datetime.now(timezone.utc)}},
        )
        return True
    except Exception as e:
        logger.error(f"[article_index] update_title failed for {article_id}: {e}")
        return False


def list_by_stage(stage: ArticleStage, limit: int = 50) -> List[dict]:
    """
    Fetch articles at a given Medallion stage — O(1) index scan on `stage` field.
    Replaces the old `distinct(foreign_key) + $nin` anti-pattern.
    """
    try:
        cursor = (
            article_index_collection
            .find({"stage": stage.value})
            .sort("created_at", ASCENDING)
            .limit(limit)
        )
        return list(cursor)
    except Exception as e:
        logger.error(f"[article_index] list_by_stage failed for {stage}: {e}")
        return []


def list_completed_articles(
    theme: Optional[str] = None,
    genre: Optional[str] = None,
    limit: int = 100,
) -> List[dict]:
    """
    Fetch articles that have completed AI enrichment.
    theme/genre are stored in the `exams` collection — caller joins if needed.
    """
    query: dict = {"ai_status": AIStatus.COMPLETED.value}
    try:
        cursor = (
            article_index_collection
            .find(query)
            .sort("published_at", DESCENDING)
            .limit(limit)
        )
        return list(cursor)
    except Exception as e:
        logger.error(f"[article_index] list_completed failed: {e}")
        return []
