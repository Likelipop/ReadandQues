"""
database/BM25/connection.py

Quản lý BM25 index như một process-level singleton.
Index được build từ original_text của tất cả article completed trong Mongo.
"""
import logging
from rank_bm25 import BM25Okapi
from database.Mongo.connection import article_collection

logger = logging.getLogger(__name__)

_bm25_index: BM25Okapi | None = None
_corpus_ids: list[str] = []


def get_index() -> tuple[BM25Okapi | None, list[str]]:
    """Lazy-load: trả về (index, corpus_ids). Build nếu chưa có."""
    global _bm25_index, _corpus_ids
    if _bm25_index is None:
        rebuild_index()
    return _bm25_index, _corpus_ids


def rebuild_index() -> None:
    """
    Build lại BM25 index từ Mongo.
    Gọi khi: Django startup (AppConfig.ready()) hoặc khi có article mới.
    """
    global _bm25_index, _corpus_ids

    logger.info("[BM25] Rebuilding index...")
    try:
        docs = list(article_collection.find(
            {"status": "completed"},
            {"_id": 1, "original_text": 1}
        ))
    except Exception as e:
        logger.warning(f"BM25 index skipped at startup: {e}")
        _bm25_index = None
        _corpus_ids = []
        return

    if not docs:
        logger.warning("[BM25] No completed articles found.")
        _bm25_index = None
        _corpus_ids = []
        return

    from .text_preprocessing import process_text_to_tokens
    _corpus_ids = [str(d["_id"]) for d in docs]
    corpus_tokens = []
    for d in docs:
        text = d.get("original_text", "")
        tokens = process_text_to_tokens(text)
        corpus_tokens.append(tokens)

    _bm25_index = BM25Okapi(corpus_tokens)
    logger.info(f"[BM25] Index built: {len(docs)} documents.")
