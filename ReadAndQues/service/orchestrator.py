"""
service/orchestrator.py — Unified Orchestration Facade & Async Background Runner.

Zen design: Pure thin facade delegating to atomic pipelines and central BackgroundRunner.
Zero duplicate workflow code.
"""

import logging
import threading
from typing import Any, Dict

from service.orchestration.configuration import get_pipe
import service.orchestration.pipes  # noqa: F401

logger = logging.getLogger(__name__)


class BackgroundRunner:
    """Centralized background task runner (easily swappable with Celery/Task Queue)."""

    @staticmethod
    def run_async(pipe_name: str, **kwargs) -> None:
        def _target():
            try:
                get_pipe(pipe_name).invoke(**kwargs)
            except Exception as e:
                logger.error(f"❌ Background pipeline '{pipe_name}' failed: {e}")

        thread = threading.Thread(
            target=_target,
            name=f"PipeRunner-{pipe_name}",
            daemon=True,
        )
        thread.start()
        logger.info("🚀 Spawned background thread for pipe '%s'", pipe_name)


class OrchestrationFacade:
    """Thin Facade unifying all asynchronous and batch orchestration entrypoints."""

    @staticmethod
    def execute_article_task(article_id: str, url: str) -> Dict[str, Any]:
        logger.info("🔄 Starting article pipeline task for article_id=%s, url=%s", article_id, url)
        pipe = get_pipe("single_article_pipe")
        result = pipe.invoke(article_id=article_id, url=url)
        return result

    @staticmethod
    def run_article_pipeline_async(article_id: str, url: str) -> None:
        """Trigger single article pipeline in background."""
        BackgroundRunner.run_async("single_article_pipe", article_id=article_id, url=url)

    @staticmethod
    def run_ai_only_pipeline_async(article_id: str) -> None:
        """Trigger AI-only pipeline in background."""
        BackgroundRunner.run_async("ai_only_pipe", article_id=article_id)

    @staticmethod
    def run_daily_pipeline(max_news: int = None) -> dict[str, str]:
        """Run daily batch pipeline stages sequentially."""
        logger.info("🕘 Daily batch pipeline started")
        from service.repositories.content_repository import ContentRepository
        from service.orchestration.configuration.config import BATCH_SIZE

        ContentRepository.ensure_buckets()
        limit = max_news if max_news is not None else BATCH_SIZE
        kwargs = {"max_links": limit, "max_docs": limit}

        pipes_to_run = [
            "ingest_bronze_pipe",
            "bronze_to_silver_pipe",
            "silver_to_gold_pipe",
        ]

        for pipe_name in pipes_to_run:
            try:
                res = get_pipe(pipe_name).invoke(**kwargs)
                if res.get("status") == "failed":
                    logger.error(f"❌ Daily pipeline failed at stage '{pipe_name}'")
                    return {
                        "status": "failed",
                        "message": f"Daily pipeline failed at stage '{pipe_name}'",
                    }
            except Exception as e:
                logger.error(f"❌ Pipeline execution error in '{pipe_name}': {e}")
                return {"status": "failed", "message": f"Pipeline '{pipe_name}' error: {e}"}

        return {"status": "completed", "message": "Daily pipeline processed successfully"}


# Top-level helper aliases for backward compatibility
execute_article_pipeline_task = OrchestrationFacade.execute_article_task
run_article_pipeline_async = OrchestrationFacade.run_article_pipeline_async
run_ai_only_pipeline_async = OrchestrationFacade.run_ai_only_pipeline_async
run_daily_pipeline = OrchestrationFacade.run_daily_pipeline
