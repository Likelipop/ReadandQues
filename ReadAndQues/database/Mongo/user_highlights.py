import logging
from datetime import datetime, timezone
from typing import List, Dict, Any

from database.Mongo.connection import user_highlights_collection

logger = logging.getLogger(__name__)

def add_highlight(user_id: int, article_id: str, highlighted_text: str, note: str = "") -> bool:
    if not user_id or not article_id or not highlighted_text:
        return False
        
    try:
        doc = {
            "user_id": user_id,
            "article_id": str(article_id),
            "highlighted_text": highlighted_text,
            "note": note,
            "created_at": datetime.now(timezone.utc)
        }
        user_highlights_collection.insert_one(doc)
        return True
    except Exception as e:
        logger.error(f"Failed to add highlight: {e}")
        return False

def get_user_highlights(user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
    try:
        cursor = user_highlights_collection.find({"user_id": user_id}).sort("created_at", -1).limit(limit)
        return list(cursor)
    except Exception as e:
        logger.error(f"Failed to fetch user highlights: {e}")
        return []
