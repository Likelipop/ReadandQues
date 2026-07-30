import logging
from pipeline.etl.registry import job
from database.Mongo.homepage_sections import update_section_data
from database.Mongo.connection import reading_history_collection, article_collection
from database.BM25.connection import rebuild_index

logger = logging.getLogger(__name__)

@job("update_trending_articles")
def update_trending_articles_job(**kwargs):
    """
    Calculate trending articles based on reading history and views.
    Update `homepage_sections` collection with 'trending_articles' ID.
    """
    logger.info("Starting update_trending_articles_job...")
    try:
        # Simplistic implementation: get latest 5 articles
        cursor = article_collection.find(
            {"status": "completed"}, 
            {"title": 1, "_id": 1, "theme": 1}
        ).sort("created_at", -1).limit(5)
        
        trending_data = [
            {"id": str(doc["_id"]), "title": doc.get("title", "No Title"), "theme": doc.get("theme", "General")}
            for doc in cursor
        ]
        
        update_section_data("trending_articles", trending_data, expires_in_hours=1)
        logger.info(f"Updated trending articles. Count: {len(trending_data)}")
        return {"status": "success", "count": len(trending_data)}
    except Exception as e:
        logger.error(f"Error updating trending articles: {e}")
        return {"status": "failed", "error": str(e)}

@job("reindex_search_data")
def reindex_search_data_job(**kwargs):
    """
    Re-build BM25 search index async.
    """
    logger.info("Starting reindex_search_data_job...")
    try:
        rebuild_index()
        logger.info("Rebuilt BM25 index.")
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error rebuilding search data: {e}")
        return {"status": "failed", "error": str(e)}
