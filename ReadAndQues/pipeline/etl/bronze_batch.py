"""
pipeline/etl/bronze_batch.py — Bronze stage: batch RSS ingestion.
"""

import argparse
import logging
from datetime import datetime, timezone

import feedparser

from database.Crawler.scraper import crawl_article_content
from database.Mongo.crud import (find_existing_bronze_urls,
                                 insert_bronze_doc,
                                 insert_pipeline_log)

from .pipeline_config import BATCH_SIZE, MAX_INGESTED_NUMBER, RSS_FEEDS_FILE

logger = logging.getLogger(__name__)


def load_rss_feeds() -> list[str]:
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
    entries = []
    try:
        parsed = feedparser.parse(feed_url)
        for entry in parsed.entries:
            link = entry.get("link", "").strip()
            title = entry.get("title", "").strip()
            if link:
                entries.append(
                    {
                        "url": link,
                        "title": title,
                        "rss_feed": feed_url,
                    }
                )
    except Exception as e:
        logger.error(f"Error parsing RSS feed {feed_url}: {e}")
    return entries


def deduplicate(entries: list[dict]) -> list[dict]:
    if not entries:
        return []
    urls = [e["url"] for e in entries]
    existing = find_existing_bronze_urls(urls)
    return [e for e in entries if e["url"] not in existing]


def ingest_batch(entries: list[dict], dry_run: bool = False) -> dict:
    stats = {"total": len(entries), "success": 0, "failed": 0, "skipped": 0}

    for entry in entries[:MAX_INGESTED_NUMBER]:
        url = entry["url"]

        if dry_run:
            logger.info(f"  [DRY-RUN] Would crawl: {url}")
            stats["skipped"] += 1
            continue

        crawl_res = crawl_article_content(url)
        if not crawl_res.get("success"):
            logger.warning(
                f"  ❌ Failed to crawl: {url} — {crawl_res.get('error', '')}"
            )
            stats["failed"] += 1
            insert_pipeline_log(
                stage="bronze",
                status="failed",
                message=crawl_res.get("error", "Unknown crawl error"),
                url=url,
            )
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
            inserted_id = insert_bronze_doc(bronze_doc)
            stats["success"] += 1
            logger.info(f"  ✅ Ingested: {url} → {inserted_id}")
        except Exception as e:
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
        entries = extract_links_from_rss(feed_url)
        all_entries.extend(entries)

    new_entries = deduplicate(all_entries)
    if not new_entries:
        logger.info("Nothing new to ingest. Done.")
        return

    batch = new_entries[:BATCH_SIZE]
    stats = ingest_batch(batch, dry_run=dry_run)

    if not dry_run:
        insert_pipeline_log(
            stage="bronze_batch",
            status="completed",
            message=f"Batch: {stats['success']}/{stats['total']} ingested",
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bronze batch RSS ingestion")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
