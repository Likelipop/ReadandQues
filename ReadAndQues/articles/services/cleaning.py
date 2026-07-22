"""
articles/services/cleaning.py — Article text formatting and document cleaning logic.
"""

import logging
from typing import Any, Dict, Tuple

logger = logging.getLogger(__name__)


def clean_and_validate_article(
    crawl_result: Dict[str, Any],
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Formats and extracts cleaned document data from crawl_result.
    Validation for min/max word count, title, and content non-emptiness is handled
    during article extraction in scraper.py.
    """
    if not crawl_result.get("success"):
        return False, crawl_result.get("error", "Lỗi khi cào nội dung bài báo."), {}

    content = crawl_result.get("content", "").strip()
    title = crawl_result.get("title", "").strip()
    source_name = crawl_result.get("source_name", "Unknown")

    cleaned_doc = {
        "title": title,
        "original_text": content,
        "source_name": source_name,
        "word_count": crawl_result.get("word_count") or len(content.split()),
        "canonical_url": crawl_result.get("canonical_url"),
        "author": crawl_result.get("author"),
        "published_at": crawl_result.get("published_at"),
        "language": crawl_result.get("language", "en"),
        "image_url": crawl_result.get("image_url"),
        "image_urls": crawl_result.get("image_urls") or [],
        "crawl_metadata": crawl_result.get("crawl_metadata") or {},
    }

    return True, "", cleaned_doc
