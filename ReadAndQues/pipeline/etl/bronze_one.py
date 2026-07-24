"""
pipeline/etl/bronze_one.py — Bronze stage: single article ingestion.
"""

import argparse
import logging
from datetime import datetime, timezone
from typing import Optional

from database.Crawler.scraper import crawl_article_content
from database.Mongo.crud import (get_bronze_by_url,
                                 insert_bronze_doc,
                                 insert_pipeline_log)

logger = logging.getLogger(__name__)


def ingest_one(url: str, user_id: Optional[int] = None) -> dict:
    existing = get_bronze_by_url(url)
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
        insert_pipeline_log(
            stage="bronze_one",
            status="failed",
            message=error_msg,
            url=url,
        )
        return {"success": False, "error": error_msg}

    bronze_doc = {
        "url": url,
        "title": crawl_res.get("title", ""),
        "raw_text": crawl_res.get("raw_text", ""),
        "source_name": crawl_res.get("source_name", "Unknown"),
        "image_url": crawl_res.get("image_url"),
        "image_urls": crawl_res.get("image_urls", []),
        "rss_feed": None,
        "user_id": user_id,
        "crawled_at": datetime.now(timezone.utc),
    }

    try:
        bronze_id = insert_bronze_doc(bronze_doc)
        logger.info(f"✅ Bronze ingested: {url} → {bronze_id}")
        return {
            "success": True,
            "bronze_id": bronze_id,
            "crawl_result": crawl_res,
            "already_exists": False,
        }
    except Exception as e:
        logger.warning(f"⚠️  Bronze insert failed for {url}: {e}")
        existing = get_bronze_by_url(url)
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
    parser.add_argument("--url", required=True)
    parser.add_argument("--user-id", type=int, default=None)
    args = parser.parse_args()

    result = ingest_one(args.url, user_id=args.user_id)
    if result["success"]:
        print(f"✅ Bronze ID: {result['bronze_id']}")
    else:
        print(f"❌ Failed: {result['error']}")


if __name__ == "__main__":
    main()
