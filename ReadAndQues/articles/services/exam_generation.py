"""
articles/services/exam_generation.py — Task Trigger Service for AI Exam Generation.
"""

import logging
from typing import Optional, Tuple

from pipeline.orchestrator import run_article_pipeline_async

logger = logging.getLogger(__name__)


def trigger_async_exam_generation(
    article_id: str, original_text: str, title: str, url: str
) -> bool:
    """
    Triggers background thread for AI exam generation and Chroma vector indexing.
    """
    try:
        run_article_pipeline_async(article_id, url)
        logger.info(
            "🚀 Dispatched background thread pipeline for article %s", article_id
        )
        return True
    except Exception as exc:
        logger.error(
            "❌ Failed to dispatch pipeline for article %s: %s", article_id, exc
        )
        return False

