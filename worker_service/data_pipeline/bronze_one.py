"""
worker_service/data_pipeline/bronze_one.py — Bronze stage: single article ingestion.

Input: a single article URL (+ optional user_id).
Crawls the article and inserts raw data into bronze_articles.

Usage:
    python -m worker_service.data_pipeline.bronze_one --url "https://example.com/article"
    
Programmatic:
    from worker_service.data_pipeline.bronze_one import ingest_one
    bronze_id = ingest_one("https://example.com/article", user_id=1)
"""

import argparse
import logging
from datetime import datetime, timezone
from typing import Optional

from .utils.crawler import crawl_article_content
from .utils.mongo_client import bronze_col, logs_col

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def ingest_one(url: str, user_id: Optional[int] = None) -> dict:
    """
    Crawl a single article URL and insert into bronze_articles.

    Parameters
    ----------
    url      : article URL to crawl
    user_id  : optional Django user ID (for tracking user-initiated imports)

    Returns
    -------
    dict with keys:
        success  : bool
        bronze_id: str (if success)
        crawl_result: dict (full crawl output for downstream use)
        error    : str (if failed)
    """
    # Check if already exists in bronze
    existing = bronze_col.find_one({"url": url}, {"_id": 1})
    if existing:
        return {
            "success": True,
            "bronze_id": str(existing["_id"]),
            "crawl_result": None,
            "already_exists": True,
        }

    crawl_res = crawl_article_content(url)
    if not crawl_res.get("success"):
        error_msg = crawl_res.get("error", "Unknown crawl error")
        logs_col.insert_one({
            "stage": "bronze_one",
            "document_id": None,
            "url": url,
            "status": "failed",
            "message": error_msg,
            "timestamp": datetime.now(timezone.utc),
        })
        return {"success": False, "error": error_msg}

    bronze_doc = {
        "url": url,
        "title": crawl_res.get("title", ""),
        "raw_text": crawl_res.get("raw_text", ""),
        "source_name": crawl_res.get("source_name", "Unknown"),
        "image_url": crawl_res.get("image_url"),
        "image_urls": crawl_res.get("image_urls", []),
        "rss_feed": None,  # user-initiated, not from RSS
        "user_id": user_id,
        "crawled_at": datetime.now(timezone.utc),
    }

    try:
        result = bronze_col.insert_one(bronze_doc)
        bronze_id = str(result.inserted_id)
        logger.info(f"✅ Bronze ingested: {url} → {bronze_id}")
        return {
            "success": True,
            "bronze_id": bronze_id,
            "crawl_result": crawl_res,
            "already_exists": False,
        }
    except Exception as e:
        # Likely duplicate URL due to race condition
        logger.warning(f"⚠️  Bronze insert failed for {url}: {e}")
        existing = bronze_col.find_one({"url": url}, {"_id": 1})
        if existing:
            return {
                "success": True,
                "bronze_id": str(existing["_id"]),
                "crawl_result": crawl_res,
                "already_exists": True,
            }
        return {"success": False, "error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Ingest a single article into bronze")
    parser.add_argument("--url", required=True, help="Article URL to crawl")
    parser.add_argument("--user-id", type=int, default=None, help="Optional user ID")
    args = parser.parse_args()

    result = ingest_one(args.url, user_id=args.user_id)
    if result["success"]:
        print(f"✅ Bronze ID: {result['bronze_id']}")
    else:
        print(f"❌ Failed: {result['error']}")


if __name__ == "__main__":
    main()
