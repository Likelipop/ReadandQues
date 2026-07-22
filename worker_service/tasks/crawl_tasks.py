"""
worker_service/tasks/crawl_tasks.py — Celery Tasks for Paper Crawling & Ingestion.
"""

import logging
from typing import Any, Dict

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    name="worker_service.crawl_paper_task",
    bind=True,
    max_retries=3,
    default_retry_delay=20,
)
def crawl_paper_task(self, url: str) -> Dict[str, Any]:
    """
    Crawls raw article/paper content from a given URL in the background worker.
    """
    from worker_service.database.Crawler.scraper import crawl_article_content

    logger.info("🕷️ Starting background Celery paper crawl for URL: %s", url)
    try:
        result = crawl_article_content(url)
        logger.info(
            "✅ Finished Celery paper crawl for URL: %s (success=%s)",
            url,
            result.get("success"),
        )
        return result
    except Exception as exc:
        logger.exception("⚠️ Failed to crawl paper for URL: %s", url)
        raise self.retry(exc=exc)
