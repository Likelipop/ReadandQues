"""
service/infrastructure/bm25/connection.py — In-memory BM25 Okapi Index Manager.
Builds and maintains the lexical search index from completed articles in MongoDB.
"""

import logging
from rank_bm25 import BM25Okapi

from service.infrastructure.bm25.text_processing import process_text_to_tokens

logger = logging.getLogger(__name__)

_bm25_index: BM25Okapi | None = None
_corpus_ids: list[str] = []


def get_index() -> tuple[BM25Okapi | None, list[str]]:
    """
    Return the current BM25 index instance and corresponding article IDs list.
    Automatically triggers index rebuild if not yet initialized.
    """
    global _bm25_index, _corpus_ids
    if _bm25_index is None:
        rebuild_index()
    return _bm25_index, _corpus_ids


def rebuild_index() -> None:
    """
    Fetch all indexed article titles from MongoDB and build a fresh BM25Okapi index.
    """
    global _bm25_index, _corpus_ids

    logger.info("[BM25] Building index from article_index...")

    try:
        from service.infrastructure.mongo.connection import get_collection

        docs = list(
            get_collection("article_index").find(
                {"title": {"$ne": ""}},
                {"_id": 1, "title": 1},
            )
        )
    except Exception as e:
        logger.warning(f"[BM25] Could not load articles for index build: {e}")
        _bm25_index = None
        _corpus_ids = []
        return

    if not docs:
        logger.info("[BM25] No articles found to index.")
        _bm25_index = None
        _corpus_ids = []
        return

    _corpus_ids = [str(d["_id"]) for d in docs]
    corpus_tokens = [process_text_to_tokens(d.get("title", "")) for d in docs]

    _bm25_index = BM25Okapi(corpus_tokens)
    logger.info(f"[BM25] Successfully built index for {len(docs)} documents.")
