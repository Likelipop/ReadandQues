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


def get_related_articles_via_chroma(
    article, exclude_id: str, limit: int = 5
) -> List[Dict]:
    """
    Queries ChromaDB for semantically similar articles based on the summary.
    Returns a list of related MongoDB article documents.
    """
    summary = ""
    if hasattr(article, "analysis") and article.analysis:
        if hasattr(article.analysis, "core"):
            summary = getattr(article.analysis.core, "summary", "")
        elif isinstance(article.analysis, dict):
            summary = article.analysis.get("core", {}).get("summary", "")

    if not summary:
        summary = getattr(article, "title", "")

    if not articles_collection or not summary:
        return []

    try:
        # Query ChromaDB
        results = articles_collection.query(query_texts=[summary], n_results=limit + 1)

        if not results or not results["ids"]:
            return []

        related_ids = [
            str(r_id) for r_id in results["ids"][0] if str(r_id) != str(exclude_id)
        ][:limit]

        if not related_ids:
            return []

        object_ids = [ObjectId(rid) for rid in related_ids]

        # Fetch from MongoDB
        cursor = article_collection.find({"_id": {"$in": object_ids}})
        related_docs = {str(d["_id"]): d for d in cursor}

        # Maintain order returned by vector search
        related_articles = []
        for rid in related_ids:
            if rid in related_docs:
                r_doc = related_docs[rid]
                r_doc["id"] = str(r_doc["_id"])
                related_articles.append(r_doc)

        return related_articles
    except Exception as e:
        logger.error(f"Error fetching related articles from ChromaDB: {e}")
        return []
