"""
service/infrastructure/bm25/connection.py — Process-level BM25 singleton index.
"""

import logging
from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)

_bm25_index: BM25Okapi | None = None
_corpus_ids: list[str] = []


def get_index() -> tuple[BM25Okapi | None, list[str]]:
    global _bm25_index, _corpus_ids
    if _bm25_index is None:
        rebuild_index()
    return _bm25_index, _corpus_ids


def rebuild_index() -> None:
    global _bm25_index, _corpus_ids

    logger.info("[BM25] Rebuilding index from article_index...")

    try:
        from service.infrastructure.mongo.connection import get_collection

        docs = list(
            get_collection("article_index").find(
                {"title": {"$ne": ""}},
                {"_id": 1, "title": 1},
            )
        )
    except Exception as e:
        logger.warning(f"[BM25] Index skipped at startup (MongoDB unavailable?): {e}")
        _bm25_index = None
        _corpus_ids = []
        return

    if not docs:
        logger.warning("[BM25] No completed articles found in article_index.")
        _bm25_index = None
        _corpus_ids = []
        return

    from service.infrastructure.bm25.text_processing import process_text_to_tokens

    _corpus_ids = [str(d["_id"]) for d in docs]
    corpus_tokens = [process_text_to_tokens(d.get("title", "")) for d in docs]

    _bm25_index = BM25Okapi(corpus_tokens)
    logger.info(f"[BM25] Index built: {len(docs)} documents.")
