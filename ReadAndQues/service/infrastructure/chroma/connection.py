"""
service/infrastructure/chroma/connection.py — ChromaDB Client and Collection Management.
Provides clean initialization for local persistent and HTTP ChromaDB clients.
"""

import logging
import os

import chromadb

logger = logging.getLogger(__name__)

_chroma_client = None


def get_chroma_client():
    """
    Initialize and return ChromaDB client.
    Tries HttpClient first, falls back to PersistentClient for local development.
    """
    global _chroma_client
    if _chroma_client is not None:
        return _chroma_client

    host = os.getenv("CHROMA_HOST", "chromadb")
    port = int(os.getenv("CHROMA_PORT", 8000))
    env = os.getenv("DJANGO_ENV", "development")

    try:
        client = chromadb.HttpClient(host=host, port=port)
        client.heartbeat()
        _chroma_client = client
        logger.info(f"Connected to ChromaDB HttpClient on {host}:{port}")
        return _chroma_client
    except Exception as e:
        if env == "production":
            logger.error(f"ChromaDB HttpClient unavailable in production: {e}")
            raise RuntimeError(f"ChromaDB connection failed: {e}")
        logger.info(f"ChromaDB HttpClient not reachable ({e}), using PersistentClient.")
        storage_path = os.getenv(
            "CHROMA_PERSISTENT_DIR",
            os.path.join(os.path.dirname(__file__), "chroma_data"),
        )
        _chroma_client = chromadb.PersistentClient(path=storage_path)
        return _chroma_client


def get_collection(name: str = "articles"):
    """
    Retrieve or create a ChromaDB collection by name.
    """
    try:
        client = get_chroma_client()
        return client.get_or_create_collection(name=name)
    except Exception as e:
        logger.warning(f"Failed to get ChromaDB collection '{name}': {e}")
        return None


def get_news_chunks_collection():
    """
    Retrieve or create the news_chunks collection.
    """
    return get_collection(name="news_chunks")


class _CollectionProxy:
    """Lightweight proxy delegating to get_collection()."""

    def __init__(self, collection_name: str):
        self._name = collection_name

    def _get_target(self):
        col = get_collection(self._name)
        if col is None:
            raise RuntimeError(f"ChromaDB collection '{self._name}' is unavailable")
        return col

    def add(self, *args, **kwargs):
        return self._get_target().add(*args, **kwargs)

    def query(self, *args, **kwargs):
        return self._get_target().query(*args, **kwargs)

    def delete(self, *args, **kwargs):
        return self._get_target().delete(*args, **kwargs)

    def get(self, *args, **kwargs):
        return self._get_target().get(*args, **kwargs)

    def count(self, *args, **kwargs):
        return self._get_target().count(*args, **kwargs)

    def __getattr__(self, name: str):
        return getattr(self._get_target(), name)


class _ClientProxy:
    def __getattr__(self, name: str):
        c = get_chroma_client()
        if c is None:
            raise RuntimeError("ChromaDB client is unavailable")
        return getattr(c, name)


chroma_client = _ClientProxy()
articles_collection = _CollectionProxy("articles")
news_chunks_collection = _CollectionProxy("news_chunks")
