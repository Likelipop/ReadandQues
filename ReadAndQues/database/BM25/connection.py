"""
database/BM25/connection.py

Process-level BM25 singleton. Index is built from article titles in the
`article_index` collection (lightweight, contains only completed gold articles).

Why title instead of original_text:
  - original_text now lives in MinIO silver — expensive to load all into RAM
  - title is denormalized in article_index, sufficient for keyword lookup
  - If deeper search is needed, use ChromaDB semantic search instead
"""

import logging

from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)

_bm25_index: BM25Okapi | None = None
_corpus_ids: list[str] = []


def get_index() -> tuple[BM25Okapi | None, list[str]]:
    """Lazy-load: return (index, corpus_ids). Build if not yet built."""
    global _bm25_index, _corpus_ids
    if _bm25_index is None:
        rebuild_index()
    return _bm25_index, _corpus_ids


def rebuild_index() -> None:
    """
    Rebuild BM25 index from the `article_index` collection.
    Indexes article titles of all AI-completed gold articles.
    Called on startup (AppConfig.ready()) and after save_to_gold.
    """
    global _bm25_index, _corpus_ids

    logger.info("[BM25] Rebuilding index from article_index...")

    try:
        from database.Mongo.connection import article_index_collection
        from service.domain.enums import AIStatus

        docs = list(
            article_index_collection.find(
                {"ai_status": AIStatus.COMPLETED.value},
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

    from .text_preprocessing import process_text_to_tokens

    _corpus_ids = [str(d["_id"]) for d in docs]
    corpus_tokens = [process_text_to_tokens(d.get("title", "")) for d in docs]

    _bm25_index = BM25Okapi(corpus_tokens)
    logger.info(f"[BM25] Index built: {len(docs)} documents.")
