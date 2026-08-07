import logging
import os
import socket
import chromadb

logger = logging.getLogger(__name__)

_chroma_client = None
_articles_collection = None


def get_chroma_client():
    global _chroma_client, _articles_collection
    if _chroma_client is not None:
        return _chroma_client, _articles_collection

    host = os.getenv("CHROMA_HOST", "chromadb")
    port = int(os.getenv("CHROMA_PORT", 8000))

    try:
        socket.gethostbyname(host)
    except socket.gaierror:
        host = "localhost"
        port = 8002

    try:
        _chroma_client = chromadb.HttpClient(host=host, port=port)
        _articles_collection = _chroma_client.get_or_create_collection(name="articles")
        logger.info(f"ChromaDB client initialized successfully on {host}:{port}.")
    except Exception as e:
        logger.warning(f"HttpClient ChromaDB fail ({e}), attempting PersistentClient fallback...")
        try:
            storage_path = os.getenv("CHROMA_PERSISTENT_DIR", os.path.join(os.path.dirname(__file__), "chroma_data"))
            _chroma_client = chromadb.PersistentClient(path=storage_path)
            _articles_collection = _chroma_client.get_or_create_collection(name="articles")
            logger.info(f"ChromaDB PersistentClient initialized at {storage_path}.")
        except Exception as pe:
            logger.error(f"Failed to initialize ChromaDB PersistentClient: {pe}")
            _chroma_client, _articles_collection = None, None

    return _chroma_client, _articles_collection


def get_news_chunks_collection():
    client, _ = get_chroma_client()
    if client is not None:
        try:
            return client.get_or_create_collection(name="news_chunks")
        except Exception as e:
            logger.error(f"Failed to get news_chunks collection: {e}")
            return None
    return None


class LazyChromaClient:
    def __getattr__(self, name: str):
        c, _ = get_chroma_client()
        if c is None:
            raise RuntimeError("ChromaDB client is not available")
        return getattr(c, name)


class LazyChromaCollection:
    def __getattr__(self, name: str):
        _, col = get_chroma_client()
        if col is None:
            raise RuntimeError("ChromaDB collection is not available")
        return getattr(col, name)


class LazyNewsChunksCollection:
    def __getattr__(self, name: str):
        col = get_news_chunks_collection()
        if col is None:
            raise RuntimeError("ChromaDB news_chunks collection is not available")
        return getattr(col, name)


chroma_client = LazyChromaClient()
articles_collection = LazyChromaCollection()
news_chunks_collection = LazyNewsChunksCollection()

