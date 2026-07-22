"""
worker_service/tasks/pipeline_tasks.py — ETL & Data Pipeline Background Tasks.
"""

import logging
from typing import Any, Dict

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name='worker_service.daily_pipeline_task')
def daily_pipeline_task() -> dict[str, str]:
    """Run the daily extraction and AI enrichment pipeline on the worker service."""
    from worker_service.data_pipeline.gold import process_gold
    from worker_service.data_pipeline.silver import process_silver

    logger.info('🕘 Daily pipeline task started')
    process_silver()
    process_gold()
    return {'status': 'completed', 'message': 'Daily pipeline processed successfully'}


@shared_task(name='worker_service.reindex_bm25_task')
def reindex_bm25_task() -> Dict[str, Any]:
    """Rebuild BM25 search index in background Celery worker."""
    logger.info('🔍 Reindexing BM25 search index...')
    try:
        from database.BM25.connection import rebuild_index
        rebuild_index()
        logger.info('✅ BM25 search index reindexed successfully')
        return {'status': 'completed', 'message': 'BM25 index reindexed successfully'}
    except Exception as exc:
        logger.error('❌ Failed to reindex BM25 index: %s', exc)
        return {'status': 'failed', 'message': str(exc)}
