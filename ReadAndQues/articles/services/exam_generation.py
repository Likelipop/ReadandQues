"""
articles/services/exam_generation.py — Celery Task Trigger Service for AI Exam Generation.
"""

import logging
from typing import Optional, Tuple

from worker_service.tasks import generate_exam_task

logger = logging.getLogger(__name__)


def trigger_async_exam_generation(
    article_id: str, original_text: str, title: str, url: str
) -> bool:
    """
    Triggers background Celery task for AI exam generation and Chroma vector indexing.
    """
    try:
        generate_exam_task.delay(article_id, original_text, title, url)
        logger.info(
            "🚀 Dispatched Celery task generate_exam_task for article %s", article_id
        )
        return True
    except Exception as exc:
        logger.error(
            "❌ Failed to dispatch Celery task for article %s: %s", article_id, exc
        )
        return False
