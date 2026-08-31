"""
NewsPipeline/resources/rss_resource.py — RSS Feed reading and date-aware link collection.
"""

import logging
import os
from datetime import UTC, datetime, timedelta
from typing import Any

import feedparser
from dagster import ConfigurableResource

logger = logging.getLogger(__name__)


def _parse_entry_datetime(entry: Any) -> datetime:
    """Extract and normalize publication datetime from RSS entry to UTC."""
    parsed_time = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed_time:
        try:
            return datetime(*parsed_time[:6], tzinfo=UTC)
        except Exception:
            pass

    # Fallback to current UTC time if RSS lacks timestamp
    return datetime.now(UTC)


class RSSResource(ConfigurableResource):
    """
    Resource that parses configured RSS feeds from rss_feeds.txt,
    filters articles by publication date, and returns deduplicated article links.
    """

    feeds_file: str = ""

    def _resolve_feeds_file(self) -> str:
        if self.feeds_file and os.path.exists(self.feeds_file):
            return self.feeds_file
        return os.path.abspath(os.path.join(os.path.dirname(__file__), "../rss_feeds.txt"))

    def get_feed_urls(self) -> list[str]:
        """Read active feed URLs from rss_feeds.txt, ignoring comments and blanks."""
        feeds_path = self._resolve_feeds_file()
        if not os.path.exists(feeds_path):
            logger.warning(f"RSSResource: Feeds file not found at {feeds_path}")
            return []

        feed_urls = []
        with open(feeds_path, encoding="utf-8") as f:
            for line in f:
                cleaned = line.strip()
                if cleaned and not cleaned.startswith("#"):
                    feed_urls.append(cleaned)
        return feed_urls

    def fetch_links(self, target_date: str | None = None) -> list[dict[str, Any]]:
        """
        Parse all configured RSS feeds.
        If target_date ('YYYY-MM-DD') is provided, filters for articles published on that date.
        Otherwise filters by default 7-day freshness window.
        """
        feed_urls = self.get_feed_urls()
        all_links: list[dict[str, Any]] = []
        cutoff_7d = datetime.now(UTC) - timedelta(days=7)

        for feed_url in feed_urls:
            try:
                parsed = feedparser.parse(feed_url)
                source_name = parsed.feed.get("title", "News Source")

                for entry in parsed.entries:
                    link = entry.get("link")
                    if not link:
                        continue

                    pub_dt = _parse_entry_datetime(entry)
                    pub_date_str = pub_dt.strftime("%Y-%m-%d")

                    # Filter by target partition date or 7-day freshness
                    if target_date:
                        if pub_date_str != target_date:
                            continue
                    elif pub_dt < cutoff_7d:
                        continue

                    all_links.append(
                        {
                            "url": link.strip(),
                            "title": entry.get("title", "").strip(),
                            "source": source_name,
                            "published_at": pub_dt.isoformat(),
                            "published_date": pub_date_str,
                            "collected_at": datetime.now(UTC).isoformat(),
                        }
                    )
            except Exception as e:
                logger.warning(f"RSSResource: Error parsing feed '{feed_url}': {e}")

        # Deduplicate links by URL preserving order
        seen_urls: set[str] = set()
        unique_links: list[dict[str, Any]] = []
        for item in all_links:
            if item["url"] not in seen_urls:
                seen_urls.add(item["url"])
                unique_links.append(item)

        filter_info = f"for date '{target_date}'" if target_date else "within 7 days"
        logger.info(f"RSSResource: Collected {len(unique_links)} unique articles {filter_info}.")
        return unique_links
