import logging
from typing import Dict, List

from .connection import articles_collection

logger = logging.getLogger(__name__)



def add_article_vector(
    gold_id: str, summary: str, title: str, url: str, theme: str = "General", genre: str = "general"
) -> bool:
    """
    Upsert an article summary embedding in ChromaDB vector store.
    Deletes existing entry before adding to avoid DuplicateIDError on retries.
    """
    if not articles_collection or not summary:
        return False

    try:
        # Delete existing embedding if present (idempotent upsert)
        try:
            articles_collection.delete(ids=[str(gold_id)])
        except Exception:
            pass  # no-op if not found

        articles_collection.add(
            documents=[summary],
            metadatas=[{"title": title, "url": url, "theme": theme, "genre": genre}],
            ids=[str(gold_id)],
        )
        logger.info(f"[Chroma] Upserted vector for {gold_id}")
        return True
    except Exception as e:
        logger.error(f"[Chroma] Failed to upsert vector for {gold_id}: {e}")
        return False


def query_related_chroma_ids(summary: str, exclude_id: str, limit: int = 5) -> List[str]:
    """
    Queries ChromaDB for semantically similar articles based on the summary.
    Returns a list of related ChromaDB document IDs.
    """
    if not articles_collection or not summary:
        return []

    try:
        results = articles_collection.query(query_texts=[summary], n_results=limit + 1)

        if not results or not results["ids"]:
            return []

        related_ids = [
            str(r_id) for r_id in results["ids"][0] if str(r_id) != str(exclude_id)
        ][:limit]

        return related_ids
    except Exception as e:
        logger.error(f"Error fetching related articles from ChromaDB: {e}")
        return []


def search_by_text(query: str, limit: int = 5) -> List[Dict]:
    """
    Search ChromaDB using a text query.
    Returns a list of dicts with id, distance, and metadata.
    """
    if not articles_collection or not query:
        return []

    try:
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
    except Exception as e:
        logger.error(f"Error in Semantic Search ChromaDB: {e}")
        return []
