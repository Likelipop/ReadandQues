"""
worker_service/data_pipeline/bronze_batch.py — Bronze stage: batch RSS ingestion.

Reads RSS feeds from rss_feeds.txt, extracts article links, deduplicates
against existing bronze_articles, crawls new articles, and inserts raw data.

Usage:
    python -m worker_service.data_pipeline.bronze_batch
    python -m worker_service.data_pipeline.bronze_batch --dry-run
"""

import argparse
import logging
from datetime import datetime, timezone

import feedparser

from .pipeline_config import RSS_FEEDS_FILE, MAX_INGESTED_NUMBER, BATCH_SIZE
from .utils.crawler import crawl_article_content
from .utils.mongo_client import bronze_col, logs_col

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def load_rss_feeds() -> list[str]:
    """Read RSS feed URLs from rss_feeds.txt, skip empty lines and comments."""
    feeds = []
    if not RSS_FEEDS_FILE.exists():
        logger.warning(f"RSS feeds file not found: {RSS_FEEDS_FILE}")
        return feeds
    with open(RSS_FEEDS_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                feeds.append(line)
    return feeds


def extract_links_from_rss(feed_url: str) -> list[dict]:
    """Parse RSS feed and return list of {url, title, rss_feed} dicts."""
    entries = []
    try:
        parsed = feedparser.parse(feed_url)
        for entry in parsed.entries:
            link = entry.get("link", "").strip()
            title = entry.get("title", "").strip()
            if link:
                entries.append({
                    "url": link,
                    "title": title,
                    "rss_feed": feed_url,
                })
    except Exception as e:
        logger.error(f"Error parsing RSS feed {feed_url}: {e}")
    return entries


def deduplicate(entries: list[dict]) -> list[dict]:
    """Remove entries whose URL already exists in bronze_articles."""
    if not entries:
        return []
    urls = [e["url"] for e in entries]
    existing = set()
    for doc in bronze_col.find({"url": {"$in": urls}}, {"url": 1}):
        existing.add(doc["url"])
    return [e for e in entries if e["url"] not in existing]


def ingest_batch(entries: list[dict], dry_run: bool = False) -> dict:
    """Crawl and insert each entry into bronze_articles. Returns stats."""
    stats = {"total": len(entries), "success": 0, "failed": 0, "skipped": 0}

    for entry in entries[:MAX_INGESTED_NUMBER]:
        url = entry["url"]

        if dry_run:
            logger.info(f"  [DRY-RUN] Would crawl: {url}")
            stats["skipped"] += 1
            continue

        crawl_res = crawl_article_content(url)
        if not crawl_res.get("success"):
            logger.warning(f"  ❌ Failed to crawl: {url} — {crawl_res.get('error', '')}")
            stats["failed"] += 1
            logs_col.insert_one({
                "stage": "bronze",
                "document_id": None,
                "url": url,
                "status": "failed",
                "message": crawl_res.get("error", "Unknown crawl error"),
                "timestamp": datetime.now(timezone.utc),
            })
            continue

        bronze_doc = {
            "url": url,
            "title": crawl_res.get("title", entry.get("title", "")),
            "raw_text": crawl_res.get("raw_text", ""),
            "source_name": crawl_res.get("source_name", "Unknown"),
            "image_url": crawl_res.get("image_url"),
            "image_urls": crawl_res.get("image_urls", []),
            "rss_feed": entry.get("rss_feed"),
            "crawled_at": datetime.now(timezone.utc),
        }

        try:
            result = bronze_col.insert_one(bronze_doc)
            stats["success"] += 1
            logger.info(f"  ✅ Ingested: {url} → {result.inserted_id}")
        except Exception as e:
            # Duplicate URL (unique index) or other error
            stats["failed"] += 1
            logger.warning(f"  ⚠️  Insert failed for {url}: {e}")

    return stats


def main(dry_run: bool = False):
    logger.info("═══════════════════════════════════════════════")
    logger.info("  🟤 BRONZE BATCH — RSS Feed Ingestion")
    logger.info("═══════════════════════════════════════════════")

    feeds = load_rss_feeds()
    if not feeds:
        logger.warning("No RSS feeds configured. Add feeds to rss_feeds.txt")
        return

    all_entries = []
    for feed_url in feeds:
        logger.info(f"📡 Parsing RSS: {feed_url}")
        entries = extract_links_from_rss(feed_url)
        logger.info(f"   Found {len(entries)} entries")
        all_entries.extend(entries)

    logger.info(f"\n📊 Total entries from all feeds: {len(all_entries)}")

    new_entries = deduplicate(all_entries)
    logger.info(f"🆕 New entries after deduplication: {len(new_entries)}")

    if not new_entries:
        logger.info("Nothing new to ingest. Done.")
        return

    # Limit to batch size
    batch = new_entries[:BATCH_SIZE]
    logger.info(f"📦 Processing batch of {len(batch)} articles...\n")

    stats = ingest_batch(batch, dry_run=dry_run)

    logger.info(f"\n📈 Batch complete: {stats['success']} success, "
                f"{stats['failed']} failed, {stats['skipped']} skipped")

    # Log batch run
    if not dry_run:
        logs_col.insert_one({
            "stage": "bronze_batch",
            "document_id": None,
            "status": "completed",
            "message": f"Batch: {stats['success']}/{stats['total']} ingested",
            "timestamp": datetime.now(timezone.utc),
        })


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bronze batch RSS ingestion")
    parser.add_argument("--dry-run", action="store_true", help="Parse RSS but don't crawl or insert")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
