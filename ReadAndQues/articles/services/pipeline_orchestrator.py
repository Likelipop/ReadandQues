"""
articles/services/pipeline_orchestrator.py — Pipeline Orchestrator.

Combines article crawling, cleaning, database insertion, and async AI exam generation.
Uses crawl_article_content directly from database.Crawler.scraper.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Tuple

from database.Crawler.scraper import crawl_article_content
from database.Mongo.crud import insert_article_document

from pipeline.orchestrator import run_article_pipeline_async

from .cleaning import clean_and_validate_article

logger = logging.getLogger(__name__)


def import_and_trigger_pipeline(
    url: str, user_id: int
) -> Tuple[bool, str, Optional[str]]:
    """
    Runs the ingestion and cleaning steps.
    If successful, inserts a pending document in MongoDB and kicks off the AI exam pipeline asynchronously via background thread.
    Returns (success, error_message, inserted_id).
    """
    from database.Mongo.crud import get_article_document_by_url

    # 0. Deduplication check
    existing_doc = get_article_document_by_url(url)
    if existing_doc:
        status = existing_doc.get("status", "")
        # If the article is already being crawled, processed, or is completed, return the existing ID directly.
        if status in ("crawling", "processing", "completed"):
            logger.info(f"Deduplication: Article {url} already exists with status {status}. Reusing _id: {existing_doc.get('_id')}")
            return True, "", str(existing_doc.get("_id"))

    # 1. Insert initial pending document into MongoDB
    pending_document = {
        "url": url,
        "title": "Loading title...",
        "original_text": "",
        "status": "crawling",
        "user_id": user_id,
        "created_at": datetime.now(timezone.utc),
    }

    try:
        inserted_id = insert_article_document(pending_document)
    except Exception as e:
        logger.error(f"Failed to insert pending article: {e}")
        return False, "Database error while creating new article.", None

    # 2. Trigger AI exam generation asynchronously via background thread
    run_article_pipeline_async(inserted_id, url)

    return True, "", inserted_id

