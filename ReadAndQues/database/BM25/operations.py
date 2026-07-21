"""
database/BM25/operations.py

Raw BM25 search — không biết về context business, chỉ trả về IDs và scores.
"""
import logging
from .connection import get_index

logger = logging.getLogger(__name__)


def search_bm25(
    query_tokens: list[str],
    n: int = 5,
    exclude_id: str | None = None,
) -> list[dict]:
    """
    Args:
        query_tokens: List token đã được clean + lemmatize từ AI_core
        n: Số kết quả tối đa
        exclude_id: article_id hiện tại (loại ra khỏi kết quả)

    Returns:
        [{"id": str, "score": float}, ...]  sorted by score desc
    """
    bm25_index, corpus_ids = get_index()
    if bm25_index is None or not query_tokens:
        return []

    try:
        scores = bm25_index.get_scores(query_tokens)

        # Build results, loại exclude_id
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
