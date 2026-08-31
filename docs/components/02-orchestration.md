# Component Guide: Data Pipeline Orchestration (Dagster)

The data pipeline is located in [`NewsPipeline/`](file:///home/likelipop/Project/ReadandQues/NewsPipeline/) and orchestrated using Dagster 1.13.

---

## 1. Pipeline Architecture (Medallion Flow)

```
[RSS Feeds]
    │
    ▼
[bronze_article_links]  ──▶  Parses RSS (BBC, NYTimes, Guardian), filters freshness (7 days), skips seen URLs
    │
    ▼
[silver_html_documents] ──▶  Crawls raw HTML via Trafilatura, extracts clean text, saves to MinIO
    │
    ▼
[gold_articles]         ──▶  Calls ai_service.interface.generate_quiz(text), NO AI HERE IN THE GOLD LAYER
                             extracts dynamic keywords & quizzes,            CHUNKING 
                             upserts to MongoDB gold_articles, 
                             indexes into ChromaDB & BM25
```

---

## 2. Asset Definitions

* **`bronze_article_links`** ([`defs/bronze.py`](file:///home/likelipop/Project/ReadandQues/NewsPipeline/src/NewsPipeline/defs/bronze.py)):
  Reads feed URLs from `rss_feeds.txt`, parses RSS XML, filters items newer than 7 days, and deduplicates against MongoDB.

* **`silver_html_documents`** ([`defs/silver.py`](file:///home/likelipop/Project/ReadandQues/NewsPipeline/src/NewsPipeline/defs/silver.py)):
  Fetches full article HTML with Trafilatura, checks minimum word count (>150 words), and caches raw HTML snapshot in MinIO.

* **`gold_articles`** ([`defs/gold.py`](file:///home/likelipop/Project/ReadandQues/NewsPipeline/src/NewsPipeline/defs/gold.py)):
  Invokes `ai_service.interface.generate_quiz()` to extract `keywords`, `summary`, and `questions`. Saves gold document into MongoDB and triggers search indexing.

---

## 3. Schedules & Execution

* **Daily Ingestion**: Scheduled via `daily_crawl_schedule` at `06:00 UTC` daily.
* **Development Server**: Run `dg dev` inside `NewsPipeline/` to open the Dagster UI at `http://localhost:3000`.
