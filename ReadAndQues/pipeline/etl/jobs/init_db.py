import logging

from database.Mongo.connection import rss_links_collection
from pipeline.etl.registry import job

logger = logging.getLogger(__name__)


@job("init_db")
def init_db(**kwargs):
    logger.info("Initializing database indices...")
    try:
        # Create a unique compound index on link and pubDate
        rss_links_collection.create_index(
            [("link", 1), ("pubDate", 1)], unique=True
        )
        logger.info("Created unique index on rss_links_collection (link, pubDate).")
        return {"status": "success", "message": "Indices created"}
    except Exception as e:
        logger.error(f"Failed to create indices: {e}")
        raise e
