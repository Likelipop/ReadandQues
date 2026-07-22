"""
articles/services/pipeline_orchestrator.py — Pipeline Orchestrator.

Combines article crawling, cleaning, database insertion, and async AI exam generation.
Uses crawl_article_content directly from database.Crawler.scraper.
"""

import logging
from datetime import datetime, timezone
from typing import Tuple, Optional

from database.Crawler.scraper import crawl_article_content
from database.Mongo.crud import insert_article_document
from worker_service.tasks import generate_exam_task
from .cleaning import clean_and_validate_article

logger = logging.getLogger(__name__)


def import_and_trigger_pipeline(url: str, user_id: int) -> Tuple[bool, str, Optional[str]]:
    """
    Runs the ingestion and cleaning steps.
    If successful, inserts a pending document in MongoDB and kicks off the AI exam pipeline asynchronously via Celery.
    Returns (success, error_message, inserted_id).
    """
    # 1. Ingestion stage (Crawler validates URL format, SSRF, HTTP status & extracts content)
    crawl_result = crawl_article_content(url)
    if not crawl_result.get("success"):
        return False, crawl_result.get("error", "Không thể trích xuất nội dung từ bài báo này."), None

    # 2. Cleaning stage
    is_valid, error_msg, cleaned_doc = clean_and_validate_article(crawl_result)
    if not is_valid:
        return False, error_msg, None

    # 3. Insert pending document into MongoDB
    pending_document = {
        "url": url,
        "canonical_url": cleaned_doc.get("canonical_url") or url,
        "title": cleaned_doc.get("title", ""),
        "original_text": cleaned_doc.get("original_text", ""),
        "source_name": cleaned_doc.get("source_name", "Unknown"),
        "author": cleaned_doc.get("author"),
        "published_at": cleaned_doc.get("published_at"),
        "language": cleaned_doc.get("language", "en"),
        "word_count": cleaned_doc.get("word_count", 0),
        "image_url": cleaned_doc.get("image_url"),
        "image_urls": cleaned_doc.get("image_urls") or [],
        "crawl_metadata": cleaned_doc.get("crawl_metadata") or {},
        "status": "pending",
        "user_id": user_id,
        "created_at": datetime.now(timezone.utc),
    }
    inserted_id = insert_article_document(pending_document)

    # 4. Queue AI exam generation in Celery
    generate_exam_task.delay(
        inserted_id,
        cleaned_doc.get("original_text", ""),
        cleaned_doc.get("title", ""),
        url,
    )

    return True, "", inserted_id
