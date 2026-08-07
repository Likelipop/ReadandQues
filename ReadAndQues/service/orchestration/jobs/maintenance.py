"""
service/orchestration/jobs/maintenance.py — System maintenance jobs.

Jobs:
  init_db             — create MongoDB indexes for all collections
  reindex_search      — rebuild in-process BM25 index
  update_trending     — refresh homepage trending section cache
"""

import logging

from database.Mongo.connection import (
    article_index_collection,
    attempts_collection,
    exams_collection,
    reading_history_collection,
    rss_links_collection,
    smart_paraphrase_collection,
)
from service.orchestration.configuration import job

logger = logging.getLogger(__name__)


@job("init_db")
def init_db(**kwargs):
    """
    Idempotent: create all MongoDB indexes.
    Safe to run on every startup — MongoDB is a no-op if index already exists.
    """
    logger.info("[maintenance] Creating MongoDB indexes...")
    created = []

    try:
        # article_index
        article_index_collection.create_index("url", unique=True, name="url_unique")
        article_index_collection.create_index("stage", name="stage_1")
        article_index_collection.create_index("ai_status", name="ai_status_1")
        article_index_collection.create_index([("published_at", -1)], name="published_at_desc")
        created.append("article_index")

        # exams
        exams_collection.create_index("article_id", unique=True, name="article_id_unique")
        exams_collection.create_index([("theme", 1), ("genre", 1)], name="theme_genre")
        created.append("exams")

        # attempts
        attempts_collection.create_index([("user_id", 1), ("article_id", 1)], name="user_article")
        created.append("attempts")

        # reading_history
        reading_history_collection.create_index(
            [("user_id", 1), ("article_id", 1)], unique=True, name="user_article_unique"
        )
        created.append("reading_history")

        # smart_paraphrase_cache
        smart_paraphrase_collection.create_index(
            [("article_id", 1), ("paragraph_hash", 1), ("user_start_index", 1), ("user_end_index", 1)],
            name="paraphrase_lookup",
        )
        created.append("smart_paraphrase_cache")

        # rss_links (keep existing)
        rss_links_collection.create_index(
            [("link", 1), ("pubDate", 1)], unique=True, name="rss_link_pubdate_unique"
        )
        created.append("rss_links")

        logger.info(f"[maintenance] ✅ Indexes created for: {', '.join(created)}")
        return {"status": "success", "collections_indexed": created}
    except Exception as e:
        logger.error(f"[maintenance] Failed to create indexes: {e}")
        raise


@job("reindex_search")
def reindex_search(**kwargs):
    """Rebuild in-process BM25 index from article_index collection."""
    logger.info("[maintenance] Rebuilding BM25 index...")
    try:
        from database.BM25.connection import rebuild_index
        rebuild_index()
        logger.info("[maintenance] ✅ BM25 index rebuilt.")
        return {"status": "success"}
    except Exception as e:
        logger.error(f"[maintenance] BM25 rebuild failed: {e}")
        return {"status": "failed", "error": str(e)}


@job("update_trending")
def update_trending(**kwargs):
    """
    Refresh the homepage trending section with the latest gold articles.
    Reads from exams collection (most recent AI-completed articles).
    """
    logger.info("[maintenance] Updating trending articles...")
    try:
        from database.Mongo.homepage_sections import update_section_data

        cursor = exams_collection.find(
            {},
            {"article_id": 1, "title": 1, "theme": 1},
        ).sort("created_at", -1).limit(5)

        trending_data = [
            {
                "id": doc["article_id"],
                "title": doc.get("title", "No Title"),
                "theme": doc.get("theme", "General"),
            }
            for doc in cursor
        ]

        update_section_data("trending_articles", trending_data, expires_in_hours=1)
        logger.info(f"[maintenance] ✅ Updated trending. Count: {len(trending_data)}")
        return {"status": "success", "count": len(trending_data)}
    except Exception as e:
        logger.error(f"[maintenance] update_trending failed: {e}")
        return {"status": "failed", "error": str(e)}
