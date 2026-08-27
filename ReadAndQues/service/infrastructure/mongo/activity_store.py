"""
service/infrastructure/mongo/activity_store.py — Atomic I/O for reading_history, user_highlights, vocab_tracking.
"""

import logging
from datetime import UTC, datetime
from typing import Any

from service.infrastructure.mongo.connection import get_collection
from service.infrastructure.utils import db_safe

logger = logging.getLogger(__name__)


# ── Reading History ───────────────────────────────────────────────────────────


@db_safe(default_return=False)
def log_reading_session(user_id: int, article_id: str, duration_sec: int, completion_rate: float) -> bool:
    if not user_id or not article_id:
        return False

    doc = {
        "user_id": user_id,
        "article_id": str(article_id),
        "read_duration_sec": duration_sec,
        "completion_rate": completion_rate,
        "last_read_at": datetime.now(UTC),
    }

    result = get_collection("reading_history").update_one(
        {"user_id": user_id, "article_id": str(article_id)},
        {"$set": doc, "$setOnInsert": {"created_at": datetime.now(UTC)}},
        upsert=True,
    )
    return result.acknowledged


@db_safe(default_return=[])
def get_user_reading_history(user_id: int, limit: int = 20) -> list[dict[str, Any]]:
    cursor = get_collection("reading_history").find({"user_id": user_id}).sort("last_read_at", -1).limit(limit)
    return list(cursor)


# ── User Highlights ───────────────────────────────────────────────────────────


@db_safe(default_return=False)
def add_highlight(user_id: int, article_id: str, highlighted_text: str, note: str = "") -> bool:
    if not user_id or not article_id or not highlighted_text:
        return False

    doc = {
        "user_id": user_id,
        "article_id": str(article_id),
        "highlighted_text": highlighted_text,
        "note": note,
        "created_at": datetime.now(UTC),
    }
    result = get_collection("user_highlights").insert_one(doc)
    return result.acknowledged


@db_safe(default_return=[])
def get_user_highlights(user_id: int, limit: int = 50) -> list[dict[str, Any]]:
    cursor = get_collection("user_highlights").find({"user_id": user_id}).sort("created_at", -1).limit(limit)
    return list(cursor)


# ── Vocabulary Tracking ───────────────────────────────────────────────────────


@db_safe(default_return=False)
def track_vocab(user_id: int, word: str, article_id: str) -> bool:
    if not user_id or not word:
        return False

    doc = {
        "user_id": user_id,
        "word": word.lower(),
        "context_article_id": str(article_id),
        "last_reviewed_at": datetime.now(UTC),
    }

    result = get_collection("vocab_tracking").update_one(
        {"user_id": user_id, "word": word.lower()},
        {
            "$set": doc,
            "$inc": {"review_count": 1},
            "$setOnInsert": {"mastery_level": 0.0, "created_at": datetime.now(UTC)},
        },
        upsert=True,
    )
    return result.acknowledged


@db_safe(default_return=[])
def get_daily_vocab_for_user(user_id: int, limit: int = 5) -> list[dict[str, Any]]:
    cursor = (
        get_collection("vocab_tracking")
        .find({"user_id": user_id})
        .sort([("mastery_level", 1), ("last_reviewed_at", 1)])
        .limit(limit)
    )
    return list(cursor)


@db_safe(default_return=False)
def delete_article_activity(article_id: str) -> bool:
    """Delete reading history and user highlights associated with article_id."""
    get_collection("reading_history").delete_many({"article_id": str(article_id)})
    get_collection("user_highlights").delete_many({"article_id": str(article_id)})
    return True
