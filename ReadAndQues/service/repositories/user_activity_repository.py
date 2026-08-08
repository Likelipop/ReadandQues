"""
service/repositories/user_activity_repository.py — User behavior data access.
Protected by @db_safe error boundary.
"""

import logging
from typing import Any, Dict, List

from database.Mongo.reading_history import (
    get_user_reading_history,
    log_reading_session,
)
from database.Mongo.user_highlights import add_highlight, get_user_highlights
from database.Mongo.vocab_tracking import get_daily_vocab_for_user, track_vocab
from service.repositories.utils import db_safe

logger = logging.getLogger(__name__)


class UserActivityRepository:
    """Data access for user reading behavior and vocabulary tracking."""

    @db_safe(default_return=False)
    def log_reading_session(
        self,
        user_id: int,
        article_id: str,
        duration_sec: int,
        completion_rate: float,
    ) -> bool:
        return log_reading_session(user_id, article_id, duration_sec, completion_rate)

    @db_safe(default_return=[])
    def get_reading_history(
        self, user_id: int, limit: int = 20
    ) -> List[Dict[str, Any]]:
        return get_user_reading_history(user_id, limit=limit)

    @db_safe(default_return=False)
    def add_highlight(
        self,
        user_id: int,
        article_id: str,
        highlighted_text: str,
        note: str = "",
    ) -> bool:
        return add_highlight(user_id, article_id, highlighted_text, note)

    @db_safe(default_return=[])
    def get_highlights(
        self, user_id: int, limit: int = 50
    ) -> List[Dict[str, Any]]:
        return get_user_highlights(user_id, limit=limit)

    @db_safe(default_return=False)
    def track_vocab(self, user_id: int, word: str, article_id: str) -> bool:
        return track_vocab(user_id, word, article_id)

    @db_safe(default_return=[])
    def get_daily_vocab(
        self, user_id: int, limit: int = 5
    ) -> List[Dict[str, Any]]:
        return get_daily_vocab_for_user(user_id, limit=limit)
