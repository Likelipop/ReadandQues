import logging
from datetime import datetime, timezone
from typing import List, Dict, Any

from database.Mongo.connection import get_collection

logger = logging.getLogger(__name__)


def log_reading_session(user_id: int, article_id: str, duration_sec: int, completion_rate: float) -> bool:
    if not user_id or not article_id:
        return False

    doc = {
        "user_id": user_id,
        "article_id": str(article_id),
        "read_duration_sec": duration_sec,
        "completion_rate": completion_rate,
        "last_read_at": datetime.now(timezone.utc),
    }

    result = get_collection("reading_history").update_one(
        {"user_id": user_id, "article_id": str(article_id)},
        {"$set": doc, "$setOnInsert": {"created_at": datetime.now(timezone.utc)}},
        upsert=True,
    )
    return result.acknowledged


def get_user_reading_history(user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
    cursor = get_collection("reading_history").find({"user_id": user_id}).sort("last_read_at", -1).limit(limit)
    return list(cursor)
