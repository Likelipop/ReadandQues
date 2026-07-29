"""
pipeline/orchestrator.py — Unified Pipeline Orchestrator for Simple Monolith.

Executes crawling, cleaning, AI exam generation, and Chroma vector indexing
in background threads without Celery or Redis.
"""

import logging
import threading
from typing import Any, Dict

from pipeline.etl.jobs.clean_logic import clean_and_validate_article
from database.Chroma.operations import add_article_vector
from database.Crawler.scraper import crawl_article_content
from database.Mongo.crud import update_article_document

from pipeline.etl.jobs.generate_questions import run_ai_pipeline
from pipeline.etl.registry import get_pipe
# Load pipes
import pipeline.etl.pipes  # noqa: F401

logger = logging.getLogger(__name__)


def execute_article_pipeline_task(article_id: str, url: str) -> Dict[str, Any]:
    """
    Executes the full pipeline for a single article by delegating to the single_article_pipe.
    """
    logger.info("🔄 Starting background pipeline task for article_id=%s, url=%s", article_id, url)
    pipe = get_pipe("single_article_pipe")
    result = pipe.invoke(article_id=article_id, url=url)
    
    # Extract the job result
    job_result = result.get("results", {}).get("process_single_article", {})
    if not job_result:
        job_result = {"status": "failed", "error": "Pipeline invocation failed."}
        
    return job_result


def run_article_pipeline_async(article_id: str, url: str) -> None:
    """
    Spawns a background thread to execute the article pipeline.
    """
    thread = threading.Thread(
        target=execute_article_pipeline_task,
        args=(article_id, url),
        name=f"ArticlePipeline-{article_id}",
        daemon=True,
    )
    thread.start()
    logger.info("🚀 Spawned background thread for article_id=%s", article_id)


def run_daily_pipeline(max_news: int = None) -> dict[str, str]:
    """
    Runs the full daily ETL pipeline using the new framework.
    """
    logger.info("🕘 Daily pipeline started")
    kwargs = {}
    if max_news is not None:
        kwargs["max_links"] = max_news
        kwargs["max_docs"] = max_news
        logger.info(f"Using max_news overriding: {max_news}")
        
    try:
        get_pipe("ingest_news_pipe").invoke(**kwargs)
        get_pipe("generate_questions_pipe").invoke(**kwargs)
        get_pipe("generate_paraphrase_pipe").invoke(**kwargs)
    except Exception as e:
        logger.error("❌ Pipeline execution error: %s", e)

    return {"status": "completed", "message": "Daily pipeline processed successfully"}
