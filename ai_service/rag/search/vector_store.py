"""
ai_service/rag/search/vector_store.py — ChromaDB Vector Store Operations.
"""

import logging
import os
from typing import Any

import chromadb

logger = logging.getLogger(__name__)

_chroma_client = None


def get_chroma_client():
    """Initialize and return ChromaDB client."""
    global _chroma_client
    if _chroma_client is not None:
        return _chroma_client

    host = os.getenv("CHROMA_HOST", "chromadb")
    port = int(os.getenv("CHROMA_PORT", 8000))

    try:
        client = chromadb.HttpClient(host=host, port=port)
        client.heartbeat()
        _chroma_client = client
        return _chroma_client
    except Exception as e:
        logger.info(f"ChromaDB HttpClient not reachable ({e}), using PersistentClient fallback.")
        storage_path = os.getenv("CHROMA_PERSISTENT_DIR", "./chroma_data")
        _chroma_client = chromadb.PersistentClient(path=storage_path)
        return _chroma_client


def get_collection(name: str = "gold_semantic_chunks"):
    """Retrieve or create a ChromaDB collection by name."""
    try:
        client = get_chroma_client()
        target_name = "gold_semantic_chunks" if name in ("news_chunks", "gold_semantic_chunks") else name
        return client.get_or_create_collection(name=target_name)
    except Exception as e:
        logger.warning(f"Failed to get ChromaDB collection '{name}': {e}")
        return None


def chunk_article_with_hierarchy(
    article_id: str,
    full_text: str,
    title: str = "",
    url: str = "",
    keywords: list[str] | None = None,
    published_at: str = "",
    target_parent_words: int = 500,
) -> list[dict[str, Any]]:
    """Splits full text into parent-child chunks for ChromaDB indexing."""
    if not full_text or not full_text.strip():
        return []

    paragraphs = [p.strip() for p in full_text.split("\n\n") if p.strip()]
    if not paragraphs:
        return []

    kw_str = ", ".join(keywords) if keywords else ""
    chunks_to_index = []
    parent_index = 0
    child_index_in_parent = 0
    current_parent_paragraphs = []
    current_parent_words = 0

    def _flush_parent(paras: list[str], p_idx: int) -> str:
        parent_text = "\n\n".join(paras)
        parent_id = f"{article_id}_parent_{p_idx}"
        chunks_to_index.append(
            {
                "id": parent_id,
                "text": parent_text,
                "metadata": {
                    "article_id": str(article_id),
                    "title": title or "Untitled",
                    "url": url or "",
                    "keywords": kw_str,
                    "published_at": published_at or "",
                    "chunk_type": "parent",
                    "parent_index": p_idx,
                    "child_count": len(paras),
                },
            }
        )
        return parent_id

    parent_id = f"{article_id}_parent_{parent_index}"

    for p in paragraphs:
        p_words = len(p.split())
        if current_parent_words + p_words > target_parent_words and current_parent_paragraphs:
            parent_id = _flush_parent(current_parent_paragraphs, parent_index)
            parent_index += 1
            current_parent_paragraphs = []
            current_parent_words = 0
            child_index_in_parent = 0

        current_parent_paragraphs.append(p)
        current_parent_words += p_words

        child_id = f"{article_id}_child_{parent_index}_{child_index_in_parent}"
        chunks_to_index.append(
            {
                "id": child_id,
                "text": p,
                "metadata": {
                    "article_id": str(article_id),
                    "title": title or "Untitled",
                    "url": url or "",
                    "keywords": kw_str,
                    "published_at": published_at or "",
                    "chunk_type": "child",
                    "parent_id": parent_id,
                    "parent_index": parent_index,
                    "child_index": child_index_in_parent,
                },
            }
        )
        child_index_in_parent += 1

    if current_parent_paragraphs:
        _flush_parent(current_parent_paragraphs, parent_index)

    return chunks_to_index


def add_article_vector(
    gold_id: str,
    summary: str,
    title: str,
    url: str,
    keywords: list[str] | None = None,
) -> bool:
    """Upsert an article's summary embedding into the articles collection."""
    if not summary:
        return False
    col = get_collection("articles")
    if not col:
        return False

    kw_str = ", ".join(keywords) if keywords else ""
    try:
        try:
            col.delete(ids=[str(gold_id)])
        except Exception:
            pass

        col.add(
            documents=[summary],
            metadatas=[{"title": title, "url": url, "keywords": kw_str}],
            ids=[str(gold_id)],
        )
        return True
    except Exception as e:
        logger.error(f"[Chroma] Failed to add article vector for {gold_id}: {e}")
        return False


def search_by_text(query: str, limit: int = 5) -> list[dict]:
    """Perform semantic search against article summary embeddings."""
    if not query:
        return []
    col = get_collection("articles")
    if not col:
        return []

    try:
        results = col.query(query_texts=[query], n_results=limit)
        if not results or not results.get("ids") or not results["ids"][0]:
            return []

        hits = []
        for i in range(len(results["ids"][0])):
            hits.append(
                {
                    "id": str(results["ids"][0][i]),
                    "article_id": str(results["ids"][0][i]),
                    "title": results["metadatas"][0][i].get("title", "Untitled") if results.get("metadatas") else "Untitled",
                    "distance": results["distances"][0][i] if "distances" in results and results["distances"] else 0.0,
                    "metadata": results["metadatas"][0][i] if "metadatas" in results and results["metadatas"] else {},
                }
            )
        return hits
    except Exception as e:
        logger.error(f"[Chroma] Error in search_by_text({query}): {e}")
        return []


def upsert_article_chunks(
    article_id: str,
    title: str,
    full_text: str,
    url: str = "",
    keywords: list[str] | None = None,
    published_at: str = "",
) -> bool:
    """Split full article text into chunks and index them into gold_semantic_chunks collection."""
    if not full_text or not article_id:
        return False
    col = get_collection("gold_semantic_chunks")
    if not col:
        return False

    try:
        try:
            col.delete(where={"article_id": str(article_id)})
        except Exception:
            pass

        chunks = chunk_article_with_hierarchy(
            article_id=article_id,
            full_text=full_text,
            title=title,
            url=url,
            keywords=keywords,
            published_at=published_at,
        )
        if not chunks:
            return False

        col.add(
            documents=[c["text"] for c in chunks],
            metadatas=[c["metadata"] for c in chunks],
            ids=[c["id"] for c in chunks],
        )
        return True
    except Exception as e:
        logger.error(f"[Chroma] Failed to upsert article chunks for {article_id}: {e}")
        return False


def vector_search_chunks(query: str, limit: int = 10, where_filter: dict | None = None) -> list[dict]:
    """Search indexed paragraph chunks in gold_semantic_chunks by query text, with optional metadata filters."""
    if not query:
        return []
    col = get_collection("gold_semantic_chunks")
    if not col:
        return []

    try:
        kwargs = {"query_texts": [query], "n_results": limit}
        if where_filter:
            kwargs["where"] = where_filter

        results = col.query(**kwargs)
        if not results or not results.get("ids") or not results["ids"][0]:
            return []

        hits = []
        for i in range(len(results["ids"][0])):
            doc_id = results["ids"][0][i]
            document = results["documents"][0][i] if "documents" in results and results["documents"] else ""
            metadata = results["metadatas"][0][i] if "metadatas" in results and results["metadatas"] else {}
            distance = results["distances"][0][i] if "distances" in results and results["distances"] else 0.0

            hits.append(
                {
                    "id": str(doc_id),
                    "text": document,
                    "metadata": metadata,
                    "distance": distance,
                    "score": 1.0 / (1.0 + distance),
                }
            )
        return hits
    except Exception as e:
        logger.error(f"[Chroma] Error in vector_search_chunks: {e}")
        return []
