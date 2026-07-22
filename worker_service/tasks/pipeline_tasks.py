"""
worker_service/tasks/pipeline_tasks.py — ETL & Data Pipeline Background Tasks.
"""

import logging
from typing import Any

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
