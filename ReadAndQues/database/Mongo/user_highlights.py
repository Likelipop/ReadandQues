import logging
from datetime import datetime, timezone
from typing import List, Dict, Any

from database.Mongo.connection import get_collection

logger = logging.getLogger(__name__)


def add_highlight(user_id: int, article_id: str, highlighted_text: str, note: str = "") -> bool:
    if not user_id or not article_id or not highlighted_text:
        return False

    doc = {
        "user_id": user_id,
        "article_id": str(article_id),
        "highlighted_text": highlighted_text,
        "note": note,
        "created_at": datetime.now(timezone.utc),
    }
    result = get_collection("user_highlights").insert_one(doc)
    return result.acknowledged


def get_user_highlights(user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
    cursor = get_collection("user_highlights").find({"user_id": user_id}).sort("created_at", -1).limit(limit)
    return list(cursor)
