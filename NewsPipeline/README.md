# NewsPipeline

Dagster-powered Medallion Data Pipeline for ReadAndQues.

# NewsPipeline 🚀

Dagster-powered Medallion Data Pipeline for ReadAndQues.

## Architecture

```
RSS Feed list (file: rss_feeds.txt)
   │
   ▼
[Bronze] bronze_links ──────────────► MongoDB (collection: bronze_links)
   │
   ▼ (dynamic partition per link)
[Silver] silver_raw_html ────────────► MinIO (bucket: raw-html)
   │
   ▼
[Gold]  gold_content ─────────────────► MongoDB (collection: gold_content)
   │
   ├──► gold_semantic_chunks ────────► ChromaDB (collection: gold_semantic_chunks)
   │
   └──► gold_bm25_index (standalone) ─► MinIO (bucket: bm25-index, key: gold_bm25_index/index.pkl)
```

## Naming Conventions

- **Assets**: `<layer>_<subject>[_<detail>]`
  - `bronze_links` (group: `bronze`)
  - `silver_raw_html` (group: `silver`, partition: `link_partitions`)
  - `gold_content` (group: `gold`, partition: `link_partitions`)
  - `gold_semantic_chunks` (group: `gold`, partition: `link_partitions`)
  - `gold_bm25_index` (group: `gold`, unpartitioned corpus rebuild)
- **IO Managers & Resources**:
  - `mongo_io_manager`: 1:1 asset-to-collection persistence (MongoDB).
  - `minio_io_manager`: HTML document persistence (MinIO `raw-html`).
  - `rss_resource`: RSS parser & freshness filter.
  - `chroma_resource`: Semantic vector chunks management (ChromaDB `gold_semantic_chunks`).
  - `bm25_resource`: BM25 lexical index builder & pickle MinIO uploader (`bm25-index`).

## Directory Structure

```
NewsPipeline/
├── pyproject.toml                     # Dependencies
├── README.md
├── src/
│   └── NewsPipeline/
│       ├── definitions.py             # Central Dagster Definitions() declaration
│       ├── rss_feeds.txt              # Configured RSS feed sources
│       ├── partitions.py              # Dynamic partition definition (link_partitions)
│       ├── jobs.py                    # ingest_job, process_job, reindex_job, ingest_schedule
│       ├── sensors.py                 # new_link_sensor
│       ├── assets/
│       │   ├── bronze.py              # bronze_links
│       │   ├── silver.py              # silver_raw_html
│       │   └── gold.py                # gold_content, gold_semantic_chunks, gold_bm25_index
│       └── resources/
│           ├── mongo_io_manager.py    # MongoIOManager
│           ├── minio_io_manager.py    # MinIOIOManager
│           ├── rss_resource.py        # RSSResource
│           ├── chroma_resource.py     # ChromaResource
│           └── bm25_resource.py       # BM25Resource
└── tests/
    └── test_pipeline_definitions.py   # Unit tests
```

## Getting Started

### 1. Synchronize Virtual Environment
```bash
cd NewsPipeline
uv sync
```

### 2. Run Tests
```bash
uv run pytest tests/ -v
```

### 3. Run Dagster UI Webserver
```bash
uv run dagster dev -f src/NewsPipeline/definitions.py
```
Open [http://localhost:3000](http://localhost:3000) to view the Asset Lineage graph and run jobs.
