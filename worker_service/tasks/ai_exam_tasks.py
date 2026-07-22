"""
worker_service/tasks/ai_exam_tasks.py — AI Exam & Vector Indexing Tasks.
"""

import logging
from typing import Any

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name='worker_service.generate_exam_task', bind=True, max_retries=3, default_retry_delay=30)
def generate_exam_task(self, article_id: str, url: str) -> dict[str, Any]:
    """Run the heavy AI exam generation in a dedicated background worker."""
    from database.Chroma.operations import add_article_vector
    from database.Mongo.crud import update_article_document
    from worker_service.data_pipeline.gold import run_ai_pipeline
    from database.Crawler.scraper import crawl_article_content
    from articles.services.cleaning import clean_and_validate_article

    logger.info('🔄 Starting Celery crawl+exam task for article_id=%s', article_id)

    # 1. Crawl
    crawl_result = crawl_article_content(url)
    if not crawl_result.get("success"):
        update_article_document(article_id, {
            'status': 'failed',
            'error_message': crawl_result.get("error", "Lỗi khi cào dữ liệu.")
        })
        return {'status': 'failed', 'article_id': article_id}
    
    # 2. Clean
    is_valid, error_msg, cleaned_doc = clean_and_validate_article(crawl_result)
    if not is_valid:
        update_article_document(article_id, {
            'status': 'failed',
            'error_message': error_msg
        })
        return {'status': 'failed', 'article_id': article_id}
        
    # 3. Update DB to 'processing' and save content
    cleaned_doc['status'] = 'processing'
    update_article_document(article_id, cleaned_doc)
    
    original_text = cleaned_doc.get("original_text", "")
    title = cleaned_doc.get("title", "")

    # 4. AI Pipeline
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
