import logging
from datetime import datetime
from typing import List, Dict, Any

from database.Mongo.connection import vocab_tracking_collection

logger = logging.getLogger(__name__)

def track_vocab(user_id: int, word: str, article_id: str) -> bool:
    if not user_id or not word:
        return False
        
    try:
        doc = {
            "user_id": user_id,
            "word": word.lower(),
            "context_article_id": str(article_id),
            "last_reviewed_at": datetime.utcnow()
        }
        
        # Increment review count and update last_reviewed
        vocab_tracking_collection.update_one(
            {"user_id": user_id, "word": word.lower()},
            {
                "$set": doc, 
                "$inc": {"review_count": 1},
                "$setOnInsert": {"mastery_level": 0.0, "created_at": datetime.utcnow()}
            },
            upsert=True
        )
        return True
    except Exception as e:
        logger.error(f"Failed to track vocab {word}: {e}")
        return False

def get_daily_vocab_for_user(user_id: int, limit: int = 5) -> List[Dict[str, Any]]:
    try:
        # get vocab with low mastery or oldest last_reviewed
        cursor = vocab_tracking_collection.find({"user_id": user_id}).sort(
            [("mastery_level", 1), ("last_reviewed_at", 1)]
        ).limit(limit)
        return list(cursor)
    except Exception as e:
        logger.error(f"Failed to fetch daily vocab: {e}")
        return []
