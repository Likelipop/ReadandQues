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


    # 1. Insert initial pending document into MongoDB
    pending_document = {
        "url": url,
        "title": "Đang tải tiêu đề...",
        "original_text": "",
        "status": "crawling",
        "user_id": user_id,
        "created_at": datetime.now(timezone.utc),
    }
    
    try:
        inserted_id = insert_article_document(pending_document)
    except Exception as e:
        logger.error(f"Failed to insert pending article: {e}")
        return False, "Lỗi cơ sở dữ liệu khi tạo bài báo mới.", None

    # 2. Queue AI exam generation in Celery
    generate_exam_task.delay(
        inserted_id,
        url,
    )

    return True, "", inserted_id
