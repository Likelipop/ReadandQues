import logging
import hashlib
from datetime import datetime, timezone
import json

from database.Crawler.scraper import crawl_article_content
from database.Mongo.crud import get_unprocessed_rss_links, mark_rss_link_extracted, insert_pipeline_log
from database.Minio.crud import save_bronze_html, save_bronze_json
from pipeline.etl.config import BATCH_SIZE, MAX_RETRIES
from pipeline.etl.registry import job

logger = logging.getLogger(__name__)


@job("ingest_to_bronze", inputs=["max_links"], outputs=["bronze_paths"])
def ingest_to_bronze(max_links: int = BATCH_SIZE):
    unprocessed_links = get_unprocessed_rss_links(limit=max_links)
    
    if not unprocessed_links:
        logger.info("No unprocessed RSS links found.")
        return {"bronze_paths": []}

    success_count = 0
    bronze_paths = []
    
    current_time = datetime.now(timezone.utc)
    date_str = current_time.strftime("%Y-%m-%d")
    time_str = current_time.strftime("%H-%M-%S")
    
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
                stage="ingest_bronze",
                status="failed",
                message=error_msg,
                url=url,
            )
            # Mark as extracted anyway to avoid infinite loop
            mark_rss_link_extracted(url)
            continue
            
        url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()
        
        source_name = crawl_res.get("source_name", doc.get("source", "Unknown"))
        clean_source = "".join([c if c.isalnum() else "_" for c in source_name]).lower()
        
        published_at = crawl_res.get("published_at")
        published_at_str = published_at.isoformat() if hasattr(published_at, "isoformat") else None
        
        crawl_meta = crawl_res.get("crawl_metadata", {})
        if "crawled_at" in crawl_meta and hasattr(crawl_meta["crawled_at"], "isoformat"):
            crawl_meta["crawled_at"] = crawl_meta["crawled_at"].isoformat()
            
        bronze_metadata = {
            "url": url,
            "title": crawl_res.get("title", doc.get("title", "")),
            "source_name": source_name,
            "image_url": crawl_res.get("image_url") or doc.get("rss_image_url"),
            "image_urls": crawl_res.get("image_urls", []),
            "rss_feed": doc.get("source"),
            "crawled_at": current_time.isoformat(),
            "raw_text": crawl_res.get("raw_text", ""),
            "html_content": crawl_res.get("html_content", ""),
            "word_count": crawl_res.get("word_count", 0),
            "language": crawl_res.get("language", "en"),
            "author": crawl_res.get("author", ""),
            "canonical_url": crawl_res.get("canonical_url", ""),
            "published_at": published_at_str,
            "crawl_metadata": crawl_meta
        }
        
        raw_html = crawl_res.get("html_content") or crawl_res.get("raw_text") or crawl_res.get("content") or ""
        
        base_path = f"articles/{date_str}/{clean_source}/{url_hash}"
        html_path = f"{base_path}.html"
        json_path = f"{base_path}.json"
        
        try:
            # Save HTML and JSON to MinIO Bronze bucket
            save_bronze_html(html_path, raw_html)
            save_bronze_json(json_path, bronze_metadata)
            
            # Update state in Mongo tracker
            from database.Mongo.crud import insert_bronze_doc
            insert_bronze_doc({"url": url, "minio_path": base_path, "crawled_at": current_time})

            mark_rss_link_extracted(url)
            success_count += 1
            bronze_paths.append(base_path)
            logger.info(f"Successfully ingested {url} into bronze MinIO at {base_path}.")
        except Exception as e:
            logger.error(f"Failed to save bronze doc for {url}: {e}")
            
    logger.info(f"Crawl finished. Success: {success_count}/{len(unprocessed_links)}")
    return {"bronze_paths": bronze_paths}
