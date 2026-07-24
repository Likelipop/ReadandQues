"""
pipeline/orchestrator.py — Unified Pipeline Orchestrator for Simple Monolith.

Executes crawling, cleaning, AI exam generation, and Chroma vector indexing
in background threads without Celery or Redis.
"""

import logging
import threading
from typing import Any, Dict

from articles.services.cleaning import clean_and_validate_article
from database.Chroma.operations import add_article_vector
from database.Crawler.scraper import crawl_article_content
from database.Mongo.crud import update_article_document

from pipeline.etl.gold import process_gold, run_ai_pipeline
from pipeline.etl.silver import process_silver

logger = logging.getLogger(__name__)


def execute_article_pipeline_task(article_id: str, url: str) -> Dict[str, Any]:
    """
    Executes the full pipeline for a single article:
      1. Crawl URL
      2. Clean & Validate Content
      3. Run LangGraph AI Exam Generation Pipeline
      4. Save to MongoDB
      5. Index Summary in ChromaDB Vector Database
    """
    logger.info("🔄 Starting background pipeline task for article_id=%s, url=%s", article_id, url)

    # 1. Crawl
    crawl_result = crawl_article_content(url)
    if not crawl_result.get("success"):
        error_msg = crawl_result.get("error", "Lỗi khi cào dữ liệu.")
        update_article_document(
            article_id,
            {
                "status": "failed",
                "error_message": error_msg,
            },
        )
        logger.error("❌ Crawl failed for article_id=%s: %s", article_id, error_msg)
        return {"status": "failed", "article_id": article_id, "error": error_msg}

    # 2. Clean & Validate
    is_valid, error_msg, cleaned_doc = clean_and_validate_article(crawl_result)
    if not is_valid:
        update_article_document(
            article_id, {"status": "failed", "error_message": error_msg}
        )
        logger.error("❌ Validation failed for article_id=%s: %s", article_id, error_msg)
        return {"status": "failed", "article_id": article_id, "error": error_msg}

    # 3. Update DB to 'processing'
    cleaned_doc["status"] = "processing"
    update_article_document(article_id, cleaned_doc)

    original_text = cleaned_doc.get("original_text", "")
    title = cleaned_doc.get("title", "")

    # 4. AI LangGraph Pipeline Execution
    ai_result = run_ai_pipeline(original_text)
    if ai_result:
        update_data = ai_result
        status_msg = "completed"
    else:
        update_data = {
            "status": "failed",
            "error_message": "AI pipeline failed to generate exam",
            "exams": [],
        }
        status_msg = "failed"

    try:
        update_article_document(article_id, update_data)
        if status_msg == "completed":
            summary = (
                ai_result.get("analysis", {}).get("summary")
                or ai_result.get("analysis", {}).get("theme")
                or title
            )
            if summary:
                add_article_vector(
                    gold_id=article_id,
                    summary=summary,
                    title=title,
                    url=url,
                )
        logger.info("✅ Pipeline task completed for article_id=%s, status=%s", article_id, status_msg)
        return {"status": status_msg, "article_id": article_id}
    except Exception as exc:
        logger.exception("⚠️ Failed updating article document for article_id=%s: %s", article_id, exc)
        return {"status": "failed", "article_id": article_id, "error": str(exc)}


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


def run_daily_pipeline() -> Dict[str, str]:
    """
    Runs the daily ETL pipeline (Silver cleaning & Gold AI enrichment).
    """
    logger.info("🕘 Daily pipeline started")
    process_silver()
    process_gold()
    return {"status": "completed", "message": "Daily pipeline processed successfully"}
