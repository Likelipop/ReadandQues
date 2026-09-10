# Bronze Layer: Ingestion & Discovery

The **Bronze Layer** is the entry point of the Data Pipeline. It is designed around the principle of **raw, non-destructive ingestion**: it identifies and captures candidate article links from external syndication feeds without modifying or interpreting the source data.

---

## 1. What It Does (Business & Functional Overview)

* **Continuous Discovery:** Periodically monitors configured news feeds (such as ScienceDaily, tech feeds, or general news) to discover newly published articles.
* **Partition Alignment:** Associates discovered articles with a specific UTC calendar date (`partition_date` in `YYYY-MM-DD` format).
* **Deterministic Identity:** Assigns every article a permanent, collision-resistant identifier based on its source URL.
* **Deduplication:** Prevents multiple feed entries referencing the same URL from producing duplicate work downstream.
* **Persistent Metadata Staging:** Stores raw discovery records into MongoDB (`bronze_links` collection) so that downstream stages (Silver) have an immutable backlog of tasks to process.

---

## 2. How It Works (Architectural & Technical Deep Dive)

The Bronze layer is implemented in `NewsPipeline/src/NewsPipeline/assets/bronze.py` and supported by `NewsPipeline/src/NewsPipeline/resources/rss_resource.py`.

```
rss_feeds.txt
      │
      ▼
┌─────────────────────────────────────────────────────────────┐
│ RSSResource.fetch_links(target_date)                        │
│ 1. Read feed URLs (ignoring '#' comments & blanks)          │
│ 2. feedparser parses XML entries                            │
│ 3. Normalize published_parsed to UTC ISO timestamp          │
│ 4. Filter: keep entries where published_date == target_date │
│ 5. Multi-format thumbnail extraction (5 fallback tiers)     │
│ 6. In-memory Set deduplication by URL                       │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ bronze_links Asset                                          │
│ 1. context.partition_key provides target date (YYYY-MM-DD)  │
│ 2. Assign deterministic ID: art_{MD5(url)[:16]}             │
│ 3. Return Dagster Output with execution metadata            │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ MongoIOManager.handle_output                                │
│ col.update_one({"article_id": id}, {"$set": doc}, upsert)   │
└─────────────────────────────────────────────────────────────┘
```

### Key Technical Mechanisms

#### A. Feed Reading & Date Normalization (`rss_resource.py`)
* Feeds are listed line-by-line in `NewsPipeline/src/NewsPipeline/rss_feeds.txt`.
* `feedparser` parses the XML feed payload.
* The function `_parse_entry_datetime(entry)` checks `published_parsed` and `updated_parsed` 9-tuple time structures and normalizes them into a `datetime` object in `UTC`.
* **Fallback:** If an entry lacks timestamp metadata, it defaults to the current UTC timestamp (`datetime.now(UTC)`).

#### B. Multi-Tier Thumbnail Extraction
News feeds format images inconsistently. `_extract_image_url_from_entry(entry)` applies a 5-tier fallback cascade:
1. `entry.media_thumbnail` (MediaRSS standard).
2. `entry.media_content` (filtering for `medium="image"` or image MIME types).
3. `entry.enclosures` (filtering for image extensions `.jpg`, `.png`, `.webp` or image MIME types).
4. `entry.links` with image relation types.
5. Regex scan for `<img[^>]+src=["']([^"']+)["']>` within `entry.summary` or `entry.description`.

#### C. In-Memory URL Deduplication
Feeds frequently repeat stories across sections or categories. Before returning, `fetch_links()` passes candidate URLs through an in-memory `seen_urls: set[str]` filter to guarantee that each URL is emitted exactly once per partition.

#### D. Deterministic Article ID Generation (`partitions.py`)
Article IDs are not auto-incrementing database integers. Instead, they are generated deterministically:
```python
def url_to_article_id(url: str) -> str:
    clean_url = url.strip()
    return f"art_{hashlib.md5(clean_url.encode('utf-8')).hexdigest()[:16]}"
```
* **Why?** If a partition fails halfway through and is retried, or if Dagster backfills a date range, the exact same URL always resolves to the exact same `article_id`. This prevents orphaned records and allows downstream assets to join across MongoDB, MinIO, and ChromaDB by ID alone.

#### E. MongoIOManager Upsert Strategy (`mongo_io_manager.py`)
`MongoIOManager` intercepts the return value of `bronze_links` and persists it directly into MongoDB:
* Target Database: `articlesDB`
* Target Collection: `bronze_links` (derived automatically from the asset name).
* Write Operation: `col.update_one({"article_id": doc["article_id"]}, {"$set": doc}, upsert=True)`.
* **Idempotency Guarantee:** Re-executing the Bronze asset updates existing records rather than inserting duplicate documents.

---

## 3. Data Contract & Schema Specification

The asset outputs a list of dictionaries adhering to the following schema:

| Field Name | Type | Nullable | Description | Example |
| :--- | :--- | :--- | :--- | :--- |
| `article_id` | `string` | No | Deterministic 16-char hex ID prefixed with `art_` | `"art_b63f7920e6650b13"` |
| `url` | `string` | No | Full canonical URL of the source article | `"https://www.sciencedaily.com/releases/2026/09/..."` |
| `title` | `string` | No | Article title extracted from RSS entry | `"Antarctica gained a record 695 billion tons..."` |
| `source` | `string` | No | Title of the parent RSS feed | `"Chinese Academy of Sciences"` |
| `published_at`| `string (ISO)`| No | Publication timestamp normalized to UTC | `"2026-09-06T14:00:00+00:00"` |
| `published_date`| `string` | No | Extracted date string (`YYYY-MM-DD`) | `"2026-09-06"` |
| `partition_date`| `string` | No | Dagster partition date this run targeted | `"2026-09-06"` |
| `image_url` | `string` | Yes | Extracted thumbnail URL (or empty string) | `"https://sciencedaily.com/images/..."` |
| `collected_at` | `string (ISO)`| No | Ingestion timestamp when the scraper processed it | `"2026-09-10T04:10:20.123456+00:00"` |

### Sample JSON Document in MongoDB (`bronze_links`)
```json
{
  "_id": { "$oid": "66e0012ab9876543210fedcb" },
  "article_id": "art_b63f7920e6650b13",
  "url": "https://www.sciencedaily.com/releases/2026/09/260906101520.htm",
  "title": "Antarctica gained a record 695 billion tons of ice. Scientists found the surprising reason",
  "source": "ScienceDaily",
  "published_at": "2026-09-06T14:15:20+00:00",
  "published_date": "2026-09-06",
  "partition_date": "2026-09-06",
  "image_url": "https://www.sciencedaily.com/images/2026/09/ice_core.jpg",
  "collected_at": "2026-09-10T04:10:20.123456+00:00"
}
```

---

## 4. Failure Modes & Edge Cases

| Failure Scenario | System Behavior & Handling |
| :--- | :--- |
| **Feed is unreachable (HTTP 500 / DNS error)** | `feedparser` returns a bozo exception or empty entries. Logged as a warning; pipeline continues processing remaining feeds. |
| **Article missing publication date** | `_parse_entry_datetime` falls back to `datetime.now(UTC)`. In partitioned runs, this entry will match today's partition. |
| **Duplicate article published across two feeds** | The URL deduplication set drops the second occurrence, keeping only the first ingested entry. |
| **Re-running a partition (backfill)** | `MongoIOManager` executes an `$set` upsert on `article_id`. No duplicate records are created in MongoDB. |
