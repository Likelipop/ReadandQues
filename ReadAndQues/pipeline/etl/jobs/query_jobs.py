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
    Fetches related articles. First attempts ChromaDB (if AI processed).
    Falls back to fetching recent articles from the same category.
    """
    summary = ""
    # Try to extract summary (Medallion or Legacy)
    if isinstance(article, dict):
        summary = article.get("summary", "")
        if not summary and article.get("analysis"):
            summary = article.get("analysis", {}).get("core", {}).get("summary", "")
    else:
        if hasattr(article, "summary") and article.summary:
            summary = article.summary
        elif hasattr(article, "analysis") and article.analysis:
            if hasattr(article.analysis, "core"):
                summary = getattr(article.analysis.core, "summary", "")
            elif isinstance(article.analysis, dict):
                summary = article.analysis.get("core", {}).get("summary", "")

    if not summary:
        summary = getattr(article, "title", "")

    related_articles = []
    
    # Only use ChromaDB if we have a real summary (which means AI likely ran)
    # or if we want to wait. To avoid the 80MB ONNX download hanging the web worker,
    # we can bypass it if summary is short (just the title).
    if len(summary) > 50:
        related_ids = query_related_chroma_ids(summary=summary, exclude_id=exclude_id, limit=limit)
        
        if related_ids:
            object_ids = [ObjectId(rid) for rid in related_ids]
            try:
                from database.Mongo.connection import gold_homepage_collection, article_collection
                # Try Medallion first
                cursor = gold_homepage_collection.find({"_id": {"$in": object_ids}})
                docs = list(cursor)
                if not docs:
                    # Fallback to legacy
                    cursor = article_collection.find({"_id": {"$in": object_ids}})
                    docs = list(cursor)
                
                related_docs = {str(d["_id"]): d for d in docs}
                for rid in related_ids:
                    if rid in related_docs:
                        r_doc = related_docs[rid]
                        r_doc["id"] = str(r_doc["_id"])
                        related_articles.append(r_doc)
            except Exception as e:
                logger.error(f"Error fetching related articles from MongoDB: {e}")

    # Fallback: if no related articles found via Chroma, get latest from the same category
    if not related_articles:
        from database.Mongo.connection import gold_homepage_collection
        
        category = "General"
        if isinstance(article, dict):
            category = article.get("category", "General")
        elif hasattr(article, "category"):
            category = getattr(article, "category", "General")
            
        try:
            # exclude the current article
            exclude_obj_id = ObjectId(exclude_id) if ObjectId.is_valid(exclude_id) else None
            query = {"status": "active", "category": category}
            if exclude_obj_id:
                query["_id"] = {"$ne": exclude_obj_id}
                
            cursor = gold_homepage_collection.find(query).sort("published_at", -1).limit(limit)
            for doc in cursor:
                doc["id"] = str(doc["_id"])
                related_articles.append(doc)
        except Exception as e:
            logger.error(f"Fallback fetching failed: {e}")

    return related_articles

@job("db_get_article_by_id", inputs=["article_id"], outputs=["article_doc"])
def db_get_article_by_id(article_id: str) -> Dict:
    from database.Mongo.crud import get_article_document_by_id
    return {"article_doc": get_article_document_by_id(article_id)}

@job("db_get_completed_articles", inputs=["theme", "genre", "limit"], outputs=["articles_list"])
def db_get_completed_articles(theme: str = None, genre: str = None, limit: int = 100) -> List[Dict]:
    from database.Mongo.crud import get_completed_articles
    return get_completed_articles(theme=theme, genre=genre, limit=limit)

@job("db_get_user_attempted_ids", inputs=["user_id"], outputs=["attempted_ids"])
def db_get_user_attempted_ids(user_id: int) -> set:
    from database.Mongo.crud import get_user_attempted_article_ids
    return get_user_attempted_article_ids(user_id)

@job("db_find_related_by_markers", inputs=["highlighted_markdown", "article_id", "limit"], outputs=["related_articles"])
def db_find_related_by_markers(highlighted_markdown: str, article_id: str, limit: int = 5) -> List[Dict]:
    from database.BM25.operations import find_related_by_markers
    from database.Mongo.crud import get_articles_by_ids
    bm25_results = find_related_by_markers(highlighted_markdown, exclude_id=article_id, n=limit)
    if not bm25_results:
        return []
    related_ids = [r["id"] for r in bm25_results]
    return get_articles_by_ids(related_ids)
