"""
service/infrastructure/bm25/connection.py — BM25 Okapi Index Manager.

Loads the pre-computed BM25 lexical search index binary artifact directly from MinIO
bucket 'bm25-index/gold_bm25_index/index.pkl' produced by the Dagster Gold pipeline.
"""

import logging
import pickle

from rank_bm25 import BM25Okapi

from service.infrastructure.minio.connection import client as minio_client

logger = logging.getLogger(__name__)

BM25_BUCKET = "bm25-index"
BM25_KEY = "gold_bm25_index/index.pkl"

_bm25_index: BM25Okapi | None = None
_corpus_ids: list[str] = []


def load_index_from_minio() -> bool:
    """
    Fetch the pre-computed BM25 binary pickle payload from MinIO.
    Deserializes index and corpus_ids in O(1) time.
    """
    global _bm25_index, _corpus_ids
    try:
        response = minio_client.get_object(BM25_BUCKET, BM25_KEY)
        data = response.read()
        response.close()
        response.release_conn()

        payload = pickle.loads(data)
        _bm25_index = payload.get("index")
        _corpus_ids = [str(cid) for cid in payload.get("corpus_ids", [])]
        logger.info(f"[BM25] Successfully loaded Gold BM25 index from MinIO for {len(_corpus_ids)} documents.")
        return True
    except Exception as e:
        logger.warning(f"[BM25] Could not load pre-computed index from MinIO ({e}).")
        return False


def get_index() -> tuple[BM25Okapi | None, list[str]]:
    """
    Return the current BM25 index instance and corresponding article IDs list.
    Automatically loads from MinIO if not yet initialized.
    """
    global _bm25_index, _corpus_ids
    if _bm25_index is None:
        rebuild_index()
    return _bm25_index, _corpus_ids


def rebuild_index() -> None:
    """
    Load the pre-computed Gold BM25 index from MinIO.
    """
    global _bm25_index, _corpus_ids
    logger.info("[BM25] Loading Gold index from MinIO...")
    success = load_index_from_minio()
    if not success:
        _bm25_index = None
        _corpus_ids = []

