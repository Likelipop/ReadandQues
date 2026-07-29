import logging
from typing import Dict, List

from bson import ObjectId
from database.Mongo.connection import article_collection

from .connection import articles_collection

logger = logging.getLogger(__name__)


def add_article_vector(gold_id: str, summary: str, title: str, url: str) -> bool:
    """
    Insert or update an article summary embedding in ChromaDB vector store.
    """
    if not articles_collection or not summary:
        return False

    try:
        articles_collection.add(
            documents=[summary],
            metadatas=[{"title": title, "url": url}],
            ids=[str(gold_id)],
        )
        logger.info(f"Successfully added vector embedding for gold_id: {gold_id}")
        return True
    except Exception as e:
        logger.error(
            f"Failed to add article vector to ChromaDB for gold_id {gold_id}: {e}"
        )
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
