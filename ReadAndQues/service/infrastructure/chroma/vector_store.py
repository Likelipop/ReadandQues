"""
service/infrastructure/chroma/vector_store.py — Vector Store Operations for articles and news_chunks collections.
"""

import logging

from service.infrastructure.chroma.chunking import chunk_article_with_hierarchy
from service.infrastructure.chroma.connection import articles_collection, news_chunks_collection
from service.infrastructure.utils import db_safe

logger = logging.getLogger(__name__)


# ── Article Summary Embeddings ────────────────────────────────────────────────

@db_safe(default_return=False)
def add_article_vector(
    gold_id: str, summary: str, title: str, url: str, theme: str = "General", genre: str = "general"
) -> bool:
    if not articles_collection or not summary:
        return False

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


@db_safe(default_return=[])
def query_related_chroma_ids(summary: str, exclude_id: str, limit: int = 5) -> list[str]:
    if not articles_collection or not summary:
        return []

    results = articles_collection.query(query_texts=[summary], n_results=limit + 1)
    if not results or not results["ids"]:
        return []

    related_ids = [
        str(r_id) for r_id in results["ids"][0] if str(r_id) != str(exclude_id)
    ][:limit]
    return related_ids


@db_safe(default_return=[])
def search_by_text(query: str, limit: int = 5) -> list[dict]:
    if not articles_collection or not query:
        return []

    results = articles_collection.query(query_texts=[query], n_results=limit)
    if not results or not results["ids"]:
        return []

    hits = []
    for i in range(len(results["ids"][0])):
        hit = {
            "id": str(results["ids"][0][i]),
            "distance": results["distances"][0][i] if "distances" in results and results["distances"] else 0.0,
            "metadata": results["metadatas"][0][i] if "metadatas" in results and results["metadatas"] else {}
        }
        hits.append(hit)
    return hits


# ── Parent-Child Paragraph Chunk Vectors ──────────────────────────────────────

@db_safe(default_return=False)
def upsert_article_chunks(
    article_id: str,
    title: str,
    full_text: str,
    url: str = "",
    theme: str = "General",
    genre: str = "general",
    published_at: str = "",
) -> bool:
    if not news_chunks_collection or not full_text or not article_id:
        return False

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
    logger.info(f"[Chroma] Indexed {len(chunks)} parent-child chunks for article {article_id}")
    return True


@db_safe(default_return=[])
def vector_search_chunks(
    query: str, limit: int = 10, where_filter: dict | None = None
) -> list[dict]:
    if not news_chunks_collection or not query:
        return []

    kwargs = {"query_texts": [query], "n_results": limit}
    if where_filter:
        kwargs["where"] = where_filter

    results = news_chunks_collection.query(**kwargs)
    if not results or not results["ids"] or not results["ids"][0]:
        return []

    hits = []
    for i in range(len(results["ids"][0])):
        doc_id = results["ids"][0][i]
        document = results["documents"][0][i] if "documents" in results and results["documents"] else ""
        metadata = results["metadatas"][0][i] if "metadatas" in results and results["metadatas"] else {}
        distance = results["distances"][0][i] if "distances" in results and results["distances"] else 0.0

        hits.append({
            "id": str(doc_id),
            "text": document,
            "metadata": metadata,
            "distance": distance,
            "score": 1.0 / (1.0 + distance),
        })
    return hits


@db_safe(default_return=False)
def delete_article_chunks(article_id: str) -> bool:
    """Delete all vector chunks for article_id across collections."""
    try:
        articles_collection.delete(ids=[str(article_id)])
    except Exception:
        pass
    try:
        news_chunks_collection.delete(where={"article_id": str(article_id)})
    except Exception:
        pass
    return True
