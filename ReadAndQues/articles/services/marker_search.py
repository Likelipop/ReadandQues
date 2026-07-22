"""
articles/services/marker_search.py

Service layer: nhận markers, trả về danh sách article documents đầy đủ.
Đây là điểm duy nhất views.py gọi vào cho feature này.
"""

import logging

from database.BM25.operations import find_related_by_markers
from database.Mongo.crud import get_articles_by_ids

logger = logging.getLogger(__name__)


def get_related_articles_from_markers(
    highlighted_markdown: str,
    article_id: str,
    limit: int = 5,
) -> list[dict]:
    """
    Args:
        highlighted_markdown: Chuỗi markdown với ==highlight== từ AttemptMongoModel
        article_id: ID bài hiện tại (loại ra)
        limit: Số bài liên quan tối đa

    Returns:
        List[dict] — article documents (title, url, theme, genre, image_url...)
    """
    bm25_results = find_related_by_markers(
        highlighted_markdown, exclude_id=article_id, n=limit
    )

    if not bm25_results:
        logger.info(f"[MarkerSearch] No BM25 results for article {article_id}")
        return []

    related_ids = [r["id"] for r in bm25_results]
    articles = get_articles_by_ids(related_ids)

    logger.info(f"[MarkerSearch] Found {len(articles)} related articles via markers.")
    return articles
