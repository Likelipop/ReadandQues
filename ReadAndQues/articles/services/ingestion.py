"""
articles/services/ingestion.py — Article content crawling business logic.
"""

import logging
from typing import Dict, Any
from database.Crawler.scraper import crawl_article_content

logger = logging.getLogger(__name__)


def ingest_article_content(url: str) -> Dict[str, Any]:
    """
    Crawls raw article content from a given URL using the local Crawler scraper.
    """
    if not url:
        return {
            "success": False,
            "error": "URL không hợp lệ."
        }
    
    return crawl_article_content(url)
