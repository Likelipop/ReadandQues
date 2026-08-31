"""
service/infrastructure/chroma/vector_store.py — Vector Store Operations for articles and news_chunks collections.
Provides clean vector upsert, similarity search, and chunk deletion.
"""

import logging

from service.infrastructure.chroma.chunking import chunk_article_with_hierarchy
from service.infrastructure.chroma.connection import articles_collection, news_chunks_collection

logger = logging.getLogger(__name__)


# ── Article Summary Embeddings ────────────────────────────────────────────────


def add_article_vector(
    gold_id: str,
    summary: str,
    title: str,
    url: str,
    theme: str = "General",
    genre: str = "general",
) -> bool:
    """
    Upsert an article's summary embedding into the articles collection.
    """
    if not summary:
        return False

    try:
        try:
            articles_collection.delete(ids=[str(gold_id)])
        except Exception:
            pass

        articles_collection.add(
            documents=[summary],
            metadatas=[{"title": title, "url": url, "theme": theme, "genre": genre}],
            ids=[str(gold_id)],
        )
        logger.info(f"[Chroma] Upserted vector for {gold_id}")
        return True
    except Exception as e:
        logger.error(f"[Chroma] Failed to add article vector for {gold_id}: {e}")
        return False


def query_related_chroma_ids(summary: str, exclude_id: str, limit: int = 5) -> list[str]:
    """
    Find related article IDs based on summary embedding similarity, excluding the query article itself.
    """
    if not summary:
        return []

    try:
        results = articles_collection.query(query_texts=[summary], n_results=limit + 1)
        if not results or not results.get("ids") or not results["ids"][0]:
            return []

        related_ids = [str(r_id) for r_id in results["ids"][0] if str(r_id) != str(exclude_id)][:limit]
        return related_ids
    except Exception as e:
        logger.error(f"[Chroma] Error in query_related_chroma_ids: {e}")
        return []


def search_by_text(query: str, limit: int = 5) -> list[dict]:
    """
    Perform semantic search against article summary embeddings.
    """
    if not query:
        return []

    try:
        results = articles_collection.query(query_texts=[query], n_results=limit)
        if not results or not results.get("ids") or not results["ids"][0]:
            return []

        hits = []
        for i in range(len(results["ids"][0])):
            hit = {
                "id": str(results["ids"][0][i]),
                "distance": results["distances"][0][i] if "distances" in results and results["distances"] else 0.0,
                "metadata": results["metadatas"][0][i] if "metadatas" in results and results["metadatas"] else {},
            }
            hits.append(hit)
        return hits
    except Exception as e:
        logger.error(f"[Chroma] Error in search_by_text({query}): {e}")
        return []


# ── Paragraph Chunk Vectors for RAG ───────────────────────────────────────────


def upsert_article_chunks(
    article_id: str,
    title: str,
    full_text: str,
    url: str = "",
    theme: str = "General",
    genre: str = "general",
    published_at: str = "",
) -> bool:
    """
    Split full article text into chunks and index them into news_chunks collection.
    """
    if not full_text or not article_id:
        return False

    try:
        try:
            news_chunks_collection.delete(where={"article_id": str(article_id)})
        except Exception:
            pass

        chunks = chunk_article_with_hierarchy(
            article_id=article_id,
            full_text=full_text,
            title=title,
            url=url,
            theme=theme,
            genre=genre,
            published_at=published_at,
        )
        if not chunks:
            return False

        documents = [c["text"] for c in chunks]
        metadatas = [c["metadata"] for c in chunks]
        ids = [c["id"] for c in chunks]

        news_chunks_collection.add(documents=documents, metadatas=metadatas, ids=ids)
        logger.info(f"[Chroma] Indexed {len(chunks)} chunks for article {article_id}")
        return True
    except Exception as e:
        logger.error(f"[Chroma] Failed to upsert article chunks for {article_id}: {e}")
        return False


def vector_search_chunks(query: str, limit: int = 10, where_filter: dict | None = None) -> list[dict]:
    """
    Search indexed paragraph chunks by query text, with optional metadata filters.
    """
    if not query:
        return []

    try:
        kwargs = {"query_texts": [query], "n_results": limit}
        if where_filter:
            kwargs["where"] = where_filter

        results = news_chunks_collection.query(**kwargs)
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


def delete_article_chunks(article_id: str) -> bool:
    """
    Delete all vector records associated with an article across collections.
    """
    try:
        try:
            articles_collection.delete(ids=[str(article_id)])
        except Exception:
            pass
        try:
            news_chunks_collection.delete(where={"article_id": str(article_id)})
        except Exception:
            pass
        return True
    except Exception as e:
        logger.warning(f"[Chroma] Error deleting vector chunks for {article_id}: {e}")
        return False
