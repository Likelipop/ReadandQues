"""
service/infrastructure/mongo/activity_store.py — Storage operations for user reading history, highlights, and vocabulary.
Manages user activity data across `reading_history`, `user_highlights`, and `vocab_tracking` collections.
"""

import logging
from datetime import UTC, datetime
from typing import Any

from pymongo.errors import PyMongoError

from service.infrastructure.mongo.connection import get_collection

logger = logging.getLogger(__name__)


# ── Reading History ───────────────────────────────────────────────────────────


def log_reading_session(user_id: int, article_id: str, duration_sec: int, completion_rate: float) -> bool:
    """
    Log or update a user's reading session progress for an article.
    """
    if not user_id or not article_id:
        return False

    doc = {
        "user_id": user_id,
        "article_id": str(article_id),
        "read_duration_sec": duration_sec,
        "completion_rate": completion_rate,
        "last_read_at": datetime.now(UTC),
    }

    try:
        result = get_collection("reading_history").update_one(
            {"user_id": user_id, "article_id": str(article_id)},
            {"$set": doc, "$setOnInsert": {"created_at": datetime.now(UTC)}},
            upsert=True,
        )
        return bool(result.acknowledged)
    except PyMongoError as e:
        logger.error(f"MongoDB error in log_reading_session(user={user_id}, article={article_id}): {e}")
        return False


def get_user_reading_history(user_id: int, limit: int = 20) -> list[dict[str, Any]]:
    """
    Fetch recent reading history documents for a user, sorted by last read date descending.
    """
    try:
        cursor = get_collection("reading_history").find({"user_id": user_id}).sort("last_read_at", -1).limit(limit)
        return list(cursor)
    except PyMongoError as e:
        logger.error(f"MongoDB error in get_user_reading_history(user={user_id}): {e}")
        return []


# ── User Highlights ───────────────────────────────────────────────────────────


def add_highlight(user_id: int, article_id: str, highlighted_text: str, note: str = "") -> bool:
    """
    Record an annotation or highlight made by a user on an article.
    """
    if not user_id or not article_id or not highlighted_text:
        return False

    doc = {
        "user_id": user_id,
        "article_id": str(article_id),
        "highlighted_text": highlighted_text,
        "note": note,
        "created_at": datetime.now(UTC),
    }
    try:
        result = get_collection("user_highlights").insert_one(doc)
        return bool(result.acknowledged)
    except PyMongoError as e:
        logger.error(f"MongoDB error in add_highlight(user={user_id}, article={article_id}): {e}")
        return False


def get_user_highlights(user_id: int, limit: int = 50) -> list[dict[str, Any]]:
    """
    Fetch recent highlights created by a user.
    """
    try:
        cursor = get_collection("user_highlights").find({"user_id": user_id}).sort("created_at", -1).limit(limit)
        return list(cursor)
    except PyMongoError as e:
        logger.error(f"MongoDB error in get_user_highlights(user={user_id}): {e}")
        return []


# ── Vocabulary Tracking ───────────────────────────────────────────────────────


def track_vocab(user_id: int, word: str, article_id: str) -> bool:
    """
    Track vocabulary lookups and increment review count for spaced repetition.
    """
    if not user_id or not word:
        return False

    doc = {
        "user_id": user_id,
        "word": word.lower(),
        "context_article_id": str(article_id),
        "last_reviewed_at": datetime.now(UTC),
    }

    try:
        result = get_collection("vocab_tracking").update_one(
            {"user_id": user_id, "word": word.lower()},
            {
                "$set": doc,
                "$inc": {"review_count": 1},
                "$setOnInsert": {"mastery_level": 0.0, "created_at": datetime.now(UTC)},
            },
            upsert=True,
        )
        return bool(result.acknowledged)
    except PyMongoError as e:
        logger.error(f"MongoDB error in track_vocab(user={user_id}, word={word}): {e}")
        return False


def get_daily_vocab_for_user(user_id: int, limit: int = 5) -> list[dict[str, Any]]:
    """
    Fetch vocabulary items prioritized for user daily review based on mastery level.
    """
    try:
        cursor = (
            get_collection("vocab_tracking")
            .find({"user_id": user_id})
            .sort([("mastery_level", 1), ("last_reviewed_at", 1)])
            .limit(limit)
        )
        return list(cursor)
    except PyMongoError as e:
        logger.error(f"MongoDB error in get_daily_vocab_for_user(user={user_id}): {e}")
        return []


def delete_article_activity(article_id: str) -> bool:
    """
    Purge reading history and user highlights associated with an article_id.
    """
    try:
        get_collection("reading_history").delete_many({"article_id": str(article_id)})
        get_collection("user_highlights").delete_many({"article_id": str(article_id)})
        return True
    except PyMongoError as e:
        logger.error(f"MongoDB error in delete_article_activity({article_id}): {e}")
        return False
