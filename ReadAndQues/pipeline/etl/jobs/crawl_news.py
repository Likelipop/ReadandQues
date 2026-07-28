import logging
from datetime import datetime, timezone

from database.Crawler.scraper import crawl_article_content
from database.Mongo.crud import (get_unprocessed_rss_links, insert_bronze_doc,
                                 insert_pipeline_log, mark_rss_link_extracted)
from pipeline.etl.config import BATCH_SIZE, MAX_RETRIES
from pipeline.etl.registry import job

logger = logging.getLogger(__name__)


@job("crawl_news")
def crawl_news(**kwargs):
    max_links = kwargs.get("max_links", BATCH_SIZE)
    unprocessed_links = get_unprocessed_rss_links(limit=max_links)
    
    if not unprocessed_links:
        logger.info("No unprocessed RSS links found.")
        return {"processed": 0, "success": 0}

    success_count = 0
    for doc in unprocessed_links:
        url = doc.get("link")
        if not url:
            continue
            
        logger.info(f"Crawling: {url}")
        
        # Retry mechanism
        crawl_res = None
        for attempt in range(MAX_RETRIES):
            crawl_res = crawl_article_content(url)
            if crawl_res.get("success"):
                break
            logger.warning(f"Attempt {attempt + 1} failed for {url}")
            
        if not crawl_res or not crawl_res.get("success"):
            error_msg = crawl_res.get("error", "Unknown crawl error") if crawl_res else "Failed after retries"
            logger.error(f"Failed to crawl {url}: {error_msg}")
            insert_pipeline_log(
                stage="crawl_news",
                status="failed",
                message=error_msg,
                url=url,
            )
            # Mark as extracted anyway to avoid infinite loop
            mark_rss_link_extracted(url)
            continue
            
        bronze_doc = {
            "url": url,
            "title": crawl_res.get("title", doc.get("title", "")),
            "raw_text": crawl_res.get("raw_text") or crawl_res.get("content") or "",
            "html_content": crawl_res.get("html_content"),
            "source_name": crawl_res.get("source_name", doc.get("source", "Unknown")),
            "image_url": crawl_res.get("image_url"),
            "image_urls": crawl_res.get("image_urls", []),
            "rss_feed": doc.get("source"),
            "crawled_at": datetime.now(timezone.utc),
        }
        
        try:
            insert_bronze_doc(bronze_doc)
            mark_rss_link_extracted(url)
            success_count += 1
            logger.info(f"Successfully ingested {url} into bronze.")
        except Exception as e:
            logger.error(f"Failed to insert bronze doc for {url}: {e}")
            
    logger.info(f"Crawl finished. Success: {success_count}/{len(unprocessed_links)}")
    return {"processed": len(unprocessed_links), "success": success_count}
