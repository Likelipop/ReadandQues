import logging
import uuid
from typing import Set
from database.Mongo.connection import attempts_collection
from service.domain.contracts import ExamAttemptContract

logger = logging.getLogger(__name__)


class AttemptRepository:
    """Canonical repository for exam attempts and highlighter marks."""

    def __init__(self):
        self.coll = attempts_collection

    def save_attempt(self, attempt: ExamAttemptContract) -> str:
        attempt_id = attempt.attempt_id or f"att_{uuid.uuid4().hex[:16]}"
        data = attempt.model_dump(mode="json")

        # 1. Dual-write / primary write to PostgreSQL if DB available
        try:
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
        except Exception as e:
            logger.warning(f"Could not persist ExamAttemptLog to PostgreSQL (DB might be offline): {e}")

        # 2. Write to MongoDB for legacy fallback
        data["attempt_id"] = attempt_id
        res = self.coll.insert_one(data)
        return str(res.inserted_id)

    def get_user_attempted_article_ids(self, user_id: int) -> Set[str]:
        if not user_id:
            return set()

        attempted_ids = set()
        # Query PostgreSQL primary
        try:
            from service.models import ExamAttemptLog
            qs = ExamAttemptLog.objects.filter(user_id=user_id).values_list("article_id", flat=True)
            attempted_ids.update(str(aid) for aid in qs if aid)
        except Exception as e:
            logger.warning(f"Could not query ExamAttemptLog from PostgreSQL: {e}")

        # Fallback to MongoDB
        try:
            cursor = self.coll.find({"user_id": user_id}, {"article_id": 1})
            attempted_ids.update(str(doc.get("article_id")) for doc in cursor if doc.get("article_id"))
        except Exception as e:
            logger.warning(f"Could not query attempts from MongoDB: {e}")

        return attempted_ids
