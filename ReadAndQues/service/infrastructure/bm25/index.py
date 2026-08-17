"""
service/infrastructure/bm25/index.py — Raw BM25 search & marker search operations.
"""

import logging
import re
from service.infrastructure.bm25.connection import get_index
from service.infrastructure.bm25.text_processing import process_text_to_tokens
from service.infrastructure.utils import db_safe

logger = logging.getLogger(__name__)


def extract_markers_text(markdown_text: str) -> str:
    if not markdown_text:
        return ""
    markers = re.findall(r"==(.*?)==", markdown_text)
    if markers:
        return " ".join(markers)
    return ""


@db_safe(default_return=[])
def search_bm25(
    query_tokens: list[str],
    n: int = 5,
    exclude_id: str | None = None,
) -> list[dict]:
    bm25_index, corpus_ids = get_index()
    if bm25_index is None or not query_tokens:
        return []

    scores = bm25_index.get_scores(query_tokens)
    results = [
        {"id": corpus_ids[i], "score": float(scores[i])}
        for i in range(len(corpus_ids))
        if corpus_ids[i] != exclude_id and scores[i] > 0
    ]
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:n]


@db_safe(default_return=[])
def find_related_by_markers(
    highlighted_markdown: str,
    exclude_id: str | None = None,
    n: int = 5,
) -> list[dict]:
    text = extract_markers_text(highlighted_markdown)
    tokens = process_text_to_tokens(text)
    if not tokens:
        return []
    return search_bm25(tokens, n=n, exclude_id=exclude_id)
