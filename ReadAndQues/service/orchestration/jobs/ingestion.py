"""
service/orchestration/jobs/ingestion.py — Bronze ingestion jobs (RSS → MinIO bronze).

Jobs:
  read_rss_sources  — read URL list from rss_feeds.txt
  fetch_rss_links   — parse RSS feeds and extract article links
  filter_new_links  — deduplicate against MongoDB rss_links tracker
  ingest_to_bronze  — crawl articles and save to MinIO bronze + article_index
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict

import feedparser

from service.crawler.scraper import crawl_article_content
from service.repositories.content_repository import ContentRepository
from service.repositories.pipeline_repository import PipelineRepository
from service.domain.contracts import generate_article_id
from service.orchestration.configuration import job
from service.orchestration.configuration.config import BATCH_SIZE, MAX_RETRIES, RSS_FEEDS_FILE

logger = logging.getLogger(__name__)


@job("read_rss_sources", outputs=["rss_sources"])
def read_rss_sources(**kwargs):
    """Read list of RSS feed URLs from rss_feeds.txt."""
    sources = []
    if not RSS_FEEDS_FILE.exists():
        logger.warning(f"RSS feeds file not found: {RSS_FEEDS_FILE}")
        return {"rss_sources": sources}

    with open(RSS_FEEDS_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                sources.append(line)

    logger.info(f"[ingestion] Read {len(sources)} RSS sources.")
    return {"rss_sources": sources}


@job("fetch_rss_links", inputs=["rss_sources"], outputs=["raw_links_dict"])
def fetch_rss_links(rss_sources: list):
    """Parse each RSS feed and extract article link metadata."""
    raw_links_dict = []

    for feed_url in rss_sources:
        try:
            parsed = feedparser.parse(feed_url)
            for entry in parsed.entries:
                link = entry.get("link", "").strip()
                title = entry.get("title", "").strip()
                pubdate = entry.get("published", "") or entry.get("updated", "")

                image_url = ""
                if "media_content" in entry and entry.media_content:
                    image_url = entry.media_content[0].get("url", "")
                elif "media_thumbnail" in entry and entry.media_thumbnail:
                    image_url = entry.media_thumbnail[0].get("url", "")
                elif "links" in entry:
                    for link_item in entry.links:
                        if link_item.get("type", "").startswith("image/"):
                            image_url = link_item.get("href", "")
                            break

                if link:
                    raw_links_dict.append({
                        "link": link,
                        "title": title,
                        "pubDate": pubdate,
                        "source": feed_url,
                        "rss_image_url": image_url,
                    })
        except Exception as e:
            logger.error(f"[ingestion] Error parsing RSS feed {feed_url}: {e}")

    logger.info(f"[ingestion] Fetched {len(raw_links_dict)} links from RSS sources.")
    return {"raw_links_dict": raw_links_dict}


@job("filter_new_links", inputs=["raw_links_dict"], outputs=["new_links_dict"])
def filter_new_links(raw_links_dict: list):
    """Deduplicate RSS links against MongoDB tracker. Batch insert new ones."""
    pipeline_repo = PipelineRepository()
    if not raw_links_dict:
        return {"new_links_dict": []}

    links_to_check = [d.get("link") for d in raw_links_dict if d.get("link")]
    existing_links = pipeline_repo.filter_existing_rss_links(links_to_check)

    new_links_dict = []
    docs_to_insert = []

    for data in raw_links_dict:
        link = data.get("link")
        if link and link not in existing_links:
            docs_to_insert.append({
                **data,
                "is_extracted": False,
                "insert_date": datetime.now(timezone.utc),
            })
            new_links_dict.append(data)
            existing_links.add(link)

    if docs_to_insert:
        inserted_count = pipeline_repo.batch_insert_rss_links(docs_to_insert)
        logger.info(f"[ingestion] Batch inserted {inserted_count} new RSS links.")

    logger.info(f"[ingestion] Found {len(new_links_dict)} new links after filtering.")
    return {"new_links_dict": new_links_dict}


@job("ingest_to_bronze", inputs=["max_links"], outputs=["ingested_ids"])
def ingest_to_bronze(max_links: int = BATCH_SIZE):
    """
    Crawl unprocessed RSS links and save raw data to MinIO bronze.
    Creates article_index entries for each successfully ingested article.
    """
    pipeline_repo = PipelineRepository()
    content_repo = ContentRepository()
    
    unprocessed = pipeline_repo.get_unprocessed_rss_links(limit=max_links)
    if not unprocessed:
        logger.info("[ingestion] No unprocessed RSS links found.")
        return {"ingested_ids": []}

    ingested_ids = []
    success_count = 0
    current_time = datetime.now(timezone.utc)

    for rss_doc in unprocessed:
        url = rss_doc.get("link")
        if not url:
            continue

        # Deterministic article_id from URL
        article_id = generate_article_id(url)
        logger.info(f"[ingestion] Crawling: {url} → {article_id}")

        crawl_res = None
        for attempt in range(MAX_RETRIES):
            crawl_res = crawl_article_content(url)
            if crawl_res.get("success"):
                break
            logger.warning(f"[ingestion] Attempt {attempt + 1} failed for {url}")

        if not crawl_res or not crawl_res.get("success"):
            error_msg = (crawl_res.get("error", "Unknown error") if crawl_res else "Failed after retries")
            logger.error(f"[ingestion] Crawl failed for {url}: {error_msg}")
            pipeline_repo.insert_pipeline_log(stage="ingest_bronze", status="failed", message=error_msg, url=url)
            pipeline_repo.mark_rss_link_extracted(url)
            continue

        # Build bronze metadata
        bronze_meta: Dict[str, Any] = {
            "url": url,
            "title": crawl_res.get("title", rss_doc.get("title", "")),
            "source_name": crawl_res.get("source_name", rss_doc.get("source", "Unknown")),
            "image_url": crawl_res.get("image_url") or rss_doc.get("rss_image_url"),
            "image_urls": crawl_res.get("image_urls", []),
            "rss_feed": rss_doc.get("source"),
            "crawled_at": current_time.isoformat(),
            "raw_text": crawl_res.get("raw_text", ""),
            "html_content": crawl_res.get("html_content", ""),
            "word_count": crawl_res.get("word_count", 0),
            "language": crawl_res.get("language", "en"),
            "author": crawl_res.get("author", ""),
            "canonical_url": crawl_res.get("canonical_url", ""),
            "published_at": str(crawl_res.get("published_at") or ""),
        }

        try:
            # Save to MinIO bronze
            html_saved = content_repo.save_bronze_html(article_id, crawl_res.get("html_content") or crawl_res.get("raw_text", ""))
            meta_saved = content_repo.save_bronze_meta(article_id, bronze_meta)
            
            if not html_saved or not meta_saved:
                raise Exception("Failed to save data to MinIO")

            # Create article_index entry (stage=BRONZE)
            pipeline_repo.create_article_index(
                article_id=article_id,
                url=url,
                title=bronze_meta["title"],
                source_name=bronze_meta["source_name"],
                image_url=bronze_meta["image_url"],
                published_at=crawl_res.get("published_at"),
            )

            pipeline_repo.mark_rss_link_extracted(url)
            success_count += 1
            ingested_ids.append(article_id)
            logger.info(f"[ingestion] ✅ Ingested {url} → bronze/{article_id}")
        except Exception as e:
            logger.error(f"[ingestion] Failed saving bronze for {url}: {e}")

    logger.info(f"[ingestion] Done. Success: {success_count}/{len(unprocessed)}")
    return {"ingested_ids": ingested_ids}


@job("ingest_single_to_bronze", inputs=["article_id", "url"], outputs=["bronze_docs", "bronze_ids"])
def ingest_single_to_bronze(article_id: str, url: str):
    """
    Atomic Job: Crawl a single user-submitted URL and save raw HTML/meta to MinIO bronze.
    Creates article_index entry if not already present.
    """
    pipeline_repo = PipelineRepository()
    content_repo = ContentRepository()
    from service.domain.models import Status

    logger.info(f"[ingestion] Single crawl starting: {url} → {article_id}")

    crawl_res = crawl_article_content(url)
    if not crawl_res or not crawl_res.get("success"):
        error_msg = crawl_res.get("error", "Crawl failed") if crawl_res else "Crawl failed"
        logger.error(f"[ingestion] Single crawl failed for {url}: {error_msg}")
        pipeline_repo.update_ai_status(article_id, Status.FAILED, error_msg)
        pipeline_repo.insert_log(stage="ingest_bronze", status="failed", message=error_msg, url=url)
        return {"bronze_docs": [], "bronze_ids": [], "status": "failed", "error": error_msg}

    bronze_meta: Dict[str, Any] = {
        "article_id": article_id,
        "url": url,
        "title": crawl_res.get("title", ""),
        "source_name": crawl_res.get("source_name", "Unknown"),
        "image_url": crawl_res.get("image_url"),
        "image_urls": crawl_res.get("image_urls", []),
        "crawled_at": datetime.now(timezone.utc).isoformat(),
        "raw_text": crawl_res.get("raw_text", ""),
        "html_content": crawl_res.get("html_content", ""),
        "word_count": crawl_res.get("word_count", 0),
        "language": crawl_res.get("language", "en"),
        "author": crawl_res.get("author", ""),
        "canonical_url": crawl_res.get("canonical_url", ""),
        "published_at": str(crawl_res.get("published_at") or ""),
    }

    try:
        content_repo.save_bronze_html(article_id, crawl_res.get("html_content") or crawl_res.get("raw_text", ""))
        content_repo.save_bronze_meta(article_id, bronze_meta)
        pipeline_repo.update_article_title(article_id, bronze_meta["title"])
        logger.info(f"[ingestion] ✅ Single bronze saved: {article_id}")
        return {"bronze_docs": [bronze_meta], "bronze_ids": [article_id]}
    except Exception as e:
        logger.error(f"[ingestion] Failed saving single bronze for {article_id}: {e}")
        pipeline_repo.update_ai_status(article_id, Status.FAILED, str(e))
        return {"bronze_docs": [], "bronze_ids": []}

