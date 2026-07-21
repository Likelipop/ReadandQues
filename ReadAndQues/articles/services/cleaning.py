"""
articles/services/cleaning.py — Article text validation and formatting logic.
"""

import logging
from typing import Dict, Any, Tuple

logger = logging.getLogger(__name__)

SILVER_MIN_WORD_COUNT = 500
SILVER_MAX_WORD_COUNT = 4000


def clean_and_validate_article(crawl_result: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Validates article text length (500 - 4000 words) and returns cleaned document data.
    """
    if not crawl_result.get("success"):
        return False, crawl_result.get("error", "Lỗi khi cào nội dung bài báo."), {}

    content = crawl_result.get("content", "").strip()
    title = crawl_result.get("title", "").strip()
    source_name = crawl_result.get("source_name", "Unknown")

    if not content or not title:
        return False, "Bài báo thiếu tiêu đề hoặc nội dung.", {}

    word_count = len(content.split())
    if word_count < SILVER_MIN_WORD_COUNT:
        return False, f"Nội dung bài báo quá ngắn ({word_count} từ, tối thiểu {SILVER_MIN_WORD_COUNT} từ).", {}
    if word_count > SILVER_MAX_WORD_COUNT:
        return False, f"Nội dung bài báo quá dài ({word_count} từ, tối đa {SILVER_MAX_WORD_COUNT} từ).", {}

    cleaned_doc = {
        "title": title,
        "original_text": content,
        "source_name": source_name,
        "word_count": word_count,
    }

    return True, "", cleaned_doc
