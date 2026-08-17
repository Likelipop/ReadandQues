"""
service/tasks.py — Celery Async Tasks & Background Worker Dispatcher.
"""

import logging
import threading
from collections.abc import Callable
from typing import Any

from celery import shared_task

logger = logging.getLogger(__name__)


# ── Celery Shared Tasks ───────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=2, default_retry_delay=30, name="service.tasks.ingest_and_enrich_article")
def task_ingest_and_enrich_article(self, article_id: str, url: str) -> dict[str, Any]:
    """Celery worker task to crawl, parse, and generate IELTS quizzes with LangGraph."""
    from service.pipelines import ingest_and_enrich_article
    try:
        logger.info(f"⚡ [Celery] Ingesting article {article_id} from {url}")
        result = ingest_and_enrich_article(article_id=article_id, url=url)
        logger.info(f"✅ [Celery] Successfully ingested article {article_id}")
        return result
    except Exception as exc:
        logger.error(f"❌ [Celery] Error ingesting article {article_id}: {exc}", exc_info=True)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=2, default_retry_delay=30, name="service.tasks.enrich_article_only")
def task_enrich_article_only(self, article_id: str) -> dict[str, Any]:
    """Celery worker task to re-run AI quiz generation for an existing article."""
    from service.pipelines import enrich_article_only
    try:
        logger.info(f"⚡ [Celery] Generating quiz for article {article_id}")
        result = enrich_article_only(article_id=article_id)
        logger.info(f"✅ [Celery] Quiz generation complete for {article_id}")
        return result
    except Exception as exc:
        logger.error(f"❌ [Celery] Error generating quiz for {article_id}: {exc}", exc_info=True)
        raise self.retry(exc=exc)


@shared_task(name="service.tasks.rebuild_bm25_index")
def task_rebuild_bm25_index() -> None:
    """Celery worker task to rebuild the BM25 search index."""
    import service.infrastructure.bm25.connection as bm25_conn
    logger.info("⚡ [Celery] Rebuilding BM25 search index")
    bm25_conn.rebuild_index()


# ── Unified Dispatcher ────────────────────────────────────────────────────────

def run_in_background(func: Callable, *args, **kwargs) -> Any:
    """
    Dispatches task to Celery worker queue when available.
    Falls back to a daemon thread if Celery broker is unreachable or in local dev.
    """
    from service.pipelines import enrich_article_only, ingest_and_enrich_article

    try:
        if func == ingest_and_enrich_article:
            return task_ingest_and_enrich_article.delay(*args, **kwargs)
        elif func == enrich_article_only:
            return task_enrich_article_only.delay(*args, **kwargs)
    except Exception as celery_err:
        logger.warning(f"⚠️ Celery dispatch failed ({celery_err}), falling back to background thread")

    # Thread fallback
    def _worker():
        try:
            func(*args, **kwargs)
        except Exception as e:
            logger.error(f"❌ Background task '{func.__name__}' failed: {e}", exc_info=True)

    thread = threading.Thread(
        target=_worker,
        name=f"BackgroundTask-{func.__name__}",
        daemon=True,
    )
    thread.start()
    logger.info(f"🚀 Spawned background thread for '{func.__name__}'")
    return thread
