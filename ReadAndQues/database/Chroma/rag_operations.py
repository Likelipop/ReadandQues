"""
database/Chroma/rag_operations.py — Pure ChromaDB vector collection I/O.
"""

import logging
from typing import Dict, List, Optional
from .connection import news_chunks_collection

logger = logging.getLogger(__name__)


def upsert_article_chunks(
    article_id: str,
    title: str,
    full_text: str,
    url: str = "",
    theme: str = "General",
    genre: str = "general",
    published_at: str = "",
) -> bool:
    """Upsert text chunks into ChromaDB news_chunks collection."""
    if not news_chunks_collection or not full_text or not article_id:
        return False

    # Delete old chunks for this article_id if present
    try:
        news_chunks_collection.delete(where={"article_id": str(article_id)})
    except Exception:
        pass

    paragraphs = [p.strip() for p in full_text.split("\n\n") if p.strip()]
    if not paragraphs:
        return False

    documents = []
    metadatas = []
    ids = []

    total_chunks = len(paragraphs)
    for idx, chunk_text in enumerate(paragraphs):
        chunk_id = f"{article_id}_chunk_{idx}"
        metadata = {
            "article_id": str(article_id),
            "title": title or "Untitled News",
            "url": url or "",
            "theme": theme or "General",
            "genre": genre or "general",
            "published_at": published_at or "",
            "chunk_index": idx,
            "total_chunks": total_chunks,
        }
        documents.append(chunk_text)
        metadatas.append(metadata)
        ids.append(chunk_id)

    news_chunks_collection.add(
        documents=documents,
        metadatas=metadatas,
        ids=ids,
    )
    logger.info(f"[RAG] Indexed {total_chunks} chunks for article {article_id}")
    return True


def vector_search_chunks(
    query: str, limit: int = 10, where_filter: Optional[Dict] = None
) -> List[Dict]:
    """Perform vector similarity search on ChromaDB news_chunks."""
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
