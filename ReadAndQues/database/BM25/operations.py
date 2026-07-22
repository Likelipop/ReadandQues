"""
database/BM25/operations.py — Raw BM25 search & marker search operations.
"""

import re
import logging
from .connection import get_index
from .text_preprocessing import process_text_to_tokens

logger = logging.getLogger(__name__)


def extract_markers_text(markdown_text: str) -> str:
    """Extract text inside ==highlight== tags, fallback to full markdown if none found."""
    if not markdown_text:
        return ""
    markers = re.findall(r"==(.*?)==", markdown_text)
    if markers:
        return " ".join(markers)
    return markdown_text


def search_bm25(
    query_tokens: list[str],
    n: int = 5,
    exclude_id: str | None = None,
) -> list[dict]:
    """
    Args:
        query_tokens: List token đã được clean + lemmatize
        n: Số kết quả tối đa
        exclude_id: article_id hiện tại (loại ra khỏi kết quả)

    Returns:
        [{"id": str, "score": float}, ...] sorted by score desc
    """
    bm25_index, corpus_ids = get_index()
    if bm25_index is None or not query_tokens:
        return []

    try:
        scores = bm25_index.get_scores(query_tokens)
        results = [
            {"id": corpus_ids[i], "score": float(scores[i])}
            for i in range(len(corpus_ids))
            if corpus_ids[i] != exclude_id and scores[i] > 0
        ]
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:n]

    except Exception as e:
        logger.error(f"[BM25] search error: {e}")
        return []


def find_related_by_markers(
    highlighted_markdown: str,
    exclude_id: str | None = None,
    n: int = 5,
) -> list[dict]:
    """Extracts text markers, tokenizes, and performs BM25 search."""
    text = extract_markers_text(highlighted_markdown)
    tokens = process_text_to_tokens(text)
    if not tokens:
        return []
    return search_bm25(tokens, n=n, exclude_id=exclude_id)
