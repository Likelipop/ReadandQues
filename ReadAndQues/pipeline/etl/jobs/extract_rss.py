import logging
from datetime import datetime, timezone

import feedparser

from database.Mongo.crud import upsert_rss_link
from pipeline.etl.config import RSS_FEEDS_FILE
from pipeline.etl.registry import job

logger = logging.getLogger(__name__)


@job("extract_rss")
def extract_rss(**kwargs):
    feeds = []
    if not RSS_FEEDS_FILE.exists():
        logger.warning(f"RSS feeds file not found: {RSS_FEEDS_FILE}")
        return {"status": "failed", "error": "Feeds file missing"}

    with open(RSS_FEEDS_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                feeds.append(line)

    total_extracted = 0
    total_upserted = 0

    for feed_url in feeds:
        try:
            parsed = feedparser.parse(feed_url)
            for entry in parsed.entries:
                link = entry.get("link", "").strip()
                title = entry.get("title", "").strip()
                pubdate = entry.get("published", "") or entry.get("updated", "")
                
                if link:
                    total_extracted += 1
                    data = {
                        "link": link,
                        "title": title,
                        "pubDate": pubdate,
                        "source": feed_url,
                        "is_extracted": False,
                        "category": "",
                        "insert_date": datetime.now(timezone.utc),
                    }
                    res = upsert_rss_link(data)
                    if res and res != "updated":
                        total_upserted += 1
        except Exception as e:
            logger.error(f"Error parsing RSS feed {feed_url}: {e}")

    logger.info(f"Extracted {total_extracted} links, upserted {total_upserted} new links.")
    return {"extracted": total_extracted, "new_upserted": total_upserted}
