"""
service/crawler/feed_crawler.py — RSS Feed Ingestion Crawler for Today's Brief.
"""

import logging
from datetime import UTC, datetime

import feedparser

import service.infrastructure.mongo.pipeline_store as pipeline_store

logger = logging.getLogger(__name__)

DEFAULT_RSS_FEEDS = [
    "http://feeds.bbci.co.uk/news/rss.xml",
    "https://www.voanews.com/api/z-$m_pevoir",
    "https://www.theguardian.com/international/rss",
]


def fetch_rss_feed_links(feed_urls: list[str] = None, max_per_feed: int = 5) -> list[dict]:
    """Fetch and parse new RSS feed links."""
    urls = feed_urls or DEFAULT_RSS_FEEDS
    collected_links = []

    for feed_url in urls:
        try:
            parsed = feedparser.parse(feed_url)
            for entry in parsed.entries[:max_per_feed]:
                link = entry.get("link", "")
                title = entry.get("title", "")
                if link and title:
                    collected_links.append({
                        "link": link,
                        "title": title,
                        "pubDate": entry.get("published", str(datetime.now(UTC))),
                        "is_extracted": False,
                        "insert_date": datetime.now(UTC),
                    })
        except Exception as e:
            logger.warning(f"Error parsing RSS feed '{feed_url}': {e}")

    if not collected_links:
        return []

    # Deduplicate against database
    all_links = [doc["link"] for doc in collected_links]
    existing_set = pipeline_store.filter_existing_rss_links(all_links)

    new_docs = [doc for doc in collected_links if doc["link"] not in existing_set]
    if new_docs:
        pipeline_store.batch_insert_rss_links(new_docs)
        logger.info(f"📰 Ingested {len(new_docs)} new RSS news links.")

    return new_docs
