import logging
from typing import Dict, List

from bson import ObjectId
from database.Chroma.operations import query_related_chroma_ids
from database.Mongo.connection import article_collection
from pipeline.etl.registry import job

logger = logging.getLogger(__name__)


@job("fetch_related_articles", 
     inputs=["article", "exclude_id", "limit"], 
     outputs=["related_articles"])
def fetch_related_articles(article, exclude_id: str, limit: int = 5) -> List[Dict]:
    """
    Fetches related articles by first querying ChromaDB for similar vectors,
    then fetching the actual documents from MongoDB.
    """
    summary = ""
    if hasattr(article, "analysis") and article.analysis:
        if hasattr(article.analysis, "core"):
            summary = getattr(article.analysis.core, "summary", "")
        elif isinstance(article.analysis, dict):
            summary = article.analysis.get("core", {}).get("summary", "")

    if not summary:
        summary = getattr(article, "title", "")

    if not summary:
        return []

    related_ids = query_related_chroma_ids(summary=summary, exclude_id=exclude_id, limit=limit)
    
    if not related_ids:
        return []

    object_ids = [ObjectId(rid) for rid in related_ids]

    try:
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
        logger.error(f"Error fetching related articles from MongoDB: {e}")
        return []
