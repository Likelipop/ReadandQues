"""
worker_service/tasks/ai_exam_tasks.py — AI Exam & Vector Indexing Tasks.
"""

import logging
from typing import Any

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name='worker_service.generate_exam_task', bind=True, max_retries=3, default_retry_delay=30)
def generate_exam_task(self, article_id: str, original_text: str, title: str, url: str) -> dict[str, Any]:
    """Run the heavy AI exam generation in a dedicated background worker."""
    from database.Chroma.operations import add_article_vector
    from database.Mongo.crud import update_article_document
    from worker_service.data_pipeline.gold import run_ai_pipeline

    logger.info('🔄 Starting Celery exam task for article_id=%s', article_id)

    ai_result = run_ai_pipeline(original_text)
    if ai_result:
        update_data = ai_result
        status_msg = 'completed'
    else:
        update_data = {
            'status': 'failed',
            'error_message': 'AI pipeline failed to generate exam',
            'exams': [],
        }
        status_msg = 'failed'

    try:
        update_article_document(article_id, update_data)
        if status_msg == 'completed':
            summary = (
                ai_result.get('analysis', {}).get('summary')
                or ai_result.get('analysis', {}).get('theme')
                or title
            )
            if summary:
                add_article_vector(
                    gold_id=article_id,
                    summary=summary,
                    title=title,
                    url=url,
                )
        logger.info('✅ Celery task completed for article_id=%s status=%s', article_id, status_msg)
        return {'status': status_msg, 'article_id': article_id}
    except Exception:
        logger.exception('⚠️ Celery exam task failed for article_id=%s', article_id)
        raise
