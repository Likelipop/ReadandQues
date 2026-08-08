import logging
from datetime import datetime, timezone
from typing import List, Dict, Any

from database.Mongo.connection import get_collection

logger = logging.getLogger(__name__)


def track_vocab(user_id: int, word: str, article_id: str) -> bool:
    if not user_id or not word:
        return False

    doc = {
        "user_id": user_id,
        "word": word.lower(),
        "context_article_id": str(article_id),
        "last_reviewed_at": datetime.now(timezone.utc),
    }

    result = get_collection("vocab_tracking").update_one(
        {"user_id": user_id, "word": word.lower()},
        {
            "$set": doc,
            "$inc": {"review_count": 1},
            "$setOnInsert": {"mastery_level": 0.0, "created_at": datetime.now(timezone.utc)},
        },
        upsert=True,
    )
    return result.acknowledged


def get_daily_vocab_for_user(user_id: int, limit: int = 5) -> List[Dict[str, Any]]:
    cursor = get_collection("vocab_tracking").find({"user_id": user_id}).sort(
        [("mastery_level", 1), ("last_reviewed_at", 1)]
    ).limit(limit)
    return list(cursor)
