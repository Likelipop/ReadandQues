import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from database.Mongo.connection import reading_history_collection
from bson import ObjectId

logger = logging.getLogger(__name__)

def log_reading_session(user_id: int, article_id: str, duration_sec: int, completion_rate: float) -> bool:
    if not user_id or not article_id:
        return False
    
    try:
        doc = {
            "user_id": user_id,
            "article_id": str(article_id),
            "read_duration_sec": duration_sec,
            "completion_rate": completion_rate,
            "last_read_at": datetime.utcnow(),
        }
        
        # Upsert: if user already read this article, update duration and last_read_at
        reading_history_collection.update_one(
            {"user_id": user_id, "article_id": str(article_id)},
            {"$set": doc, "$setOnInsert": {"created_at": datetime.utcnow()}},
            upsert=True
        )
        return True
    except Exception as e:
        logger.error(f"Failed to log reading session: {e}")
        return False

def get_user_reading_history(user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
    try:
        cursor = reading_history_collection.find({"user_id": user_id}).sort("last_read_at", -1).limit(limit)
        return list(cursor)
    except Exception as e:
        logger.error(f"Failed to fetch reading history: {e}")
        return []
