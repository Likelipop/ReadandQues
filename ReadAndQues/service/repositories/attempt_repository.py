"""
service/repositories/attempt_repository.py — Canonical repository for exam attempts.
Protected by @db_safe error boundary.
"""

import logging
import uuid
from typing import Set

from service.domain.models import ExamAttempt
from service.repositories.utils import db_safe

logger = logging.getLogger(__name__)


class AttemptRepository:
    """Canonical repository for exam attempts."""

    @db_safe(default_return="")
    def save_attempt(self, attempt: ExamAttempt) -> str:
        """Persist an exam attempt to PostgreSQL."""
        attempt_id = attempt.attempt_id or f"att_{uuid.uuid4().hex[:16]}"

        from service.models import ExamAttemptLog
        ExamAttemptLog.objects.create(
            attempt_id=attempt_id,
            user_id=attempt.user_id,
            article_id=attempt.article_id,
            score=attempt.score,
            total_questions=attempt.total_questions,
            answers=attempt.answers,
            highlighted_markdown=attempt.highlighted_markdown or "",
            elapsed_time=attempt.elapsed_time,
        )
        logger.info(f"Persisted ExamAttemptLog {attempt_id} to PostgreSQL")
        return attempt_id

    @db_safe(default_return=set())
    def get_user_attempted_article_ids(self, user_id: int) -> Set[str]:
        """Return article IDs for which user has at least one attempt."""
        if not user_id:
            return set()

        from service.models import ExamAttemptLog
        qs = ExamAttemptLog.objects.filter(user_id=user_id).values_list(
            "article_id", flat=True
        )
        return {str(aid) for aid in qs if aid}
