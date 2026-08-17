"""
service/study_buddy_service.py — Study Buddy persistent multi-turn chat service.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List
from service.infrastructure.mongo.connection import get_collection
from service.infrastructure.utils import db_safe

logger = logging.getLogger(__name__)


@db_safe(default_return=[])
def get_chat_history(user_id: int, article_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Fetch multi-turn chat history for user and article."""
    doc = get_collection("chat_sessions").find_one({"user_id": user_id, "article_id": str(article_id)})
    if doc:
        return doc.get("messages", [])
    return []


@db_safe(default_return=False)
def append_chat_message(user_id: int, article_id: str, role: str, content: str, citations: List[dict] = None) -> bool:
    """Append a user or assistant message to chat session."""
    message_doc = {
        "role": role,
        "content": content,
        "citations": citations or [],
        "timestamp": datetime.now(timezone.utc),
    }

    result = get_collection("chat_sessions").update_one(
        {"user_id": user_id, "article_id": str(article_id)},
        {
            "$push": {"messages": message_doc},
            "$set": {"updated_at": datetime.now(timezone.utc)},
            "$setOnInsert": {"created_at": datetime.now(timezone.utc)},
        },
        upsert=True,
    )
    return result.acknowledged
