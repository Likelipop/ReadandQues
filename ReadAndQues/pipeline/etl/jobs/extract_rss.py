import logging
from datetime import datetime, timezone

import feedparser

from database.Mongo.crud import upsert_rss_link, get_unprocessed_rss_links
from pipeline.etl.config import RSS_FEEDS_FILE
from pipeline.etl.registry import job

logger = logging.getLogger(__name__)


@job("read_rss_sources", outputs=["rss_sources"])
def read_rss_sources(**kwargs):
    sources = []
    if not RSS_FEEDS_FILE.exists():
        logger.warning(f"RSS feeds file not found: {RSS_FEEDS_FILE}")
        return {"rss_sources": sources}

    with open(RSS_FEEDS_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                sources.append(line)
    
    logger.info(f"Read {len(sources)} RSS sources.")
    return {"rss_sources": sources}


@job("fetch_rss_links", inputs=["rss_sources"], outputs=["raw_links_dict"])
def fetch_rss_links(rss_sources: list):
    raw_links_dict = []
    
    for feed_url in rss_sources:
        try:
            parsed = feedparser.parse(feed_url)
            for entry in parsed.entries:
                link = entry.get("link", "").strip()
                title = entry.get("title", "").strip()
                pubdate = entry.get("published", "") or entry.get("updated", "")
                
                # Extract image from RSS feed (media:content, enclosure, etc.)
                image_url = ""
                if 'media_content' in entry and len(entry.media_content) > 0:
                    image_url = entry.media_content[0].get('url', '')
                elif 'media_thumbnail' in entry and len(entry.media_thumbnail) > 0:
                    image_url = entry.media_thumbnail[0].get('url', '')
                elif 'links' in entry:
                    for link_item in entry.links:
                        if link_item.get('type', '').startswith('image/'):
                            image_url = link_item.get('href', '')
                            break
                            
                if link:
                    raw_links_dict.append({
                        "link": link,
                        "title": title,
                        "pubDate": pubdate,
                        "source": feed_url,
                        "rss_image_url": image_url
                    })
        except Exception as e:
            logger.error(f"Error parsing RSS feed {feed_url}: {e}")

    logger.info(f"Fetched {len(raw_links_dict)} links from RSS sources.")
    return {"raw_links_dict": raw_links_dict}


@job("filter_new_links", inputs=["raw_links_dict"], outputs=["new_links_dict"])
def filter_new_links(raw_links_dict: list):
    from database.Mongo.crud import filter_existing_rss_links, batch_insert_rss_links
    import hashlib
    
    if not raw_links_dict:
        return {"new_links_dict": []}
        
    # Prepare links and hashes
    links_to_check = [data.get("link") for data in raw_links_dict if data.get("link")]
    
    # 1. Batch filter: ask MongoDB for existing links in the last 30 days
    existing_links = filter_existing_rss_links(links_to_check)
    
    new_links_dict = []
    docs_to_insert = []
    
    for data in raw_links_dict:
        link = data.get("link")
        if link and link not in existing_links:
            # We add MD5 hash of URL for the index optimization
            url_hash = hashlib.md5(link.encode('utf-8')).hexdigest()
            doc_data = data.copy()
            doc_data["url_hash"] = url_hash
            doc_data["is_extracted"] = False
            doc_data["category"] = ""
            doc_data["insert_date"] = datetime.now(timezone.utc)
            
            docs_to_insert.append(doc_data)
            new_links_dict.append(data)
            # Add to local set to avoid duplicates in the same batch
            existing_links.add(link)
            
    # 2. Batch Insert the truly new links
    if docs_to_insert:
        inserted_count = batch_insert_rss_links(docs_to_insert)
        logger.info(f"Batch inserted {inserted_count} new RSS links to tracker.")
        
    logger.info(f"Found {len(new_links_dict)} new links after filtering.")
    return {"new_links_dict": new_links_dict}
