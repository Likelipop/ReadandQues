# Developer Operations & Database Guide

This guide provides concrete, step-by-step instructions for developers to inspect, query, and debug the databases powering the Data Pipeline: **ChromaDB**, **MongoDB**, and **MinIO**. It also documents connection strings, web consoles, CLI tooling, and Dagster resource fallbacks.

---

## 1. Quick Connection Reference Table

| Service | Host Port / URL | Docker Internal URL | Web UI / Console | Default Credentials |
| :--- | :--- | :--- | :--- | :--- |
| **ChromaDB** | `http://localhost:8002` | `http://chromadb:8000` | N/A *(CLI TUI)* | None |
| **MongoDB** | `localhost:27017` | `mongo:27017` | `http://localhost:8081` *(Mongo Express)* | `admin` / `changeme` |
| **MinIO** | `localhost:9000` | `minio:9000` | `http://localhost:9001` *(MinIO Console)* | `minioadmin` / `minioadmin` |
| **Dagster UI**| `http://localhost:3001` | `dagster-webserver:3000`| `http://localhost:3001` | None |

---

## 2. ChromaDB (Vector Database)

ChromaDB stores all text embeddings and chunked documents in the `gold_semantic_chunks` collection.

### A. Connection Parameters
* **Host Machine URL:** `http://localhost:8002`
* **Docker Internal URL:** `http://chromadb:8000`
* **Tenant:** `default_tenant`
* **Database:** `default_database`
* **Collection Name:** `gold_semantic_chunks`
* **Internal Storage Path:** `/data` (persisted to Docker named volume `chroma_data`)

> [!CAUTION]
> **Storage Volume Path Requirement:**
> In `docker-compose.yaml`, the volume mapping **must** be `chroma_data:/data`. Older versions used `/chroma/chroma`, but modern `chromadb/chroma:latest` containers store SQLite data at `/data/chroma.sqlite3`. Mapping to `/chroma/chroma` will cause data to be wiped when containers restart.

---

### B. Interactive Terminal UI (`chroma browse`)
ChromaDB provides an official interactive terminal UI to inspect vectors, documents, and metadata.

#### Launching the Browser
You can launch the browser either from inside the container directly against the physical storage:
```bash
# Execute from host terminal:
docker exec -it chromadb chroma browse gold_semantic_chunks --path /data
```
Or from your local machine using the Python environment pointing to the host port:
```bash
uv run chroma browse gold_semantic_chunks --host http://localhost:8002
```

#### Navigation & Shortcuts Reference
The CLI browser features two modes: the **Main Tabular View** and the **Search / Query Editor**.

```
┌────────────────────────────────────────────────────────────────────────┐
│ Collection: gold_semantic_chunks                       Total: 400      │
├──────────────────────┬────────────────────────────────┬────────────────┤
│ ID                   │ Document                       │ Metadata       │
├──────────────────────┼────────────────────────────────┼────────────────┤
│ art_b63f7920..._0    │ Antarctica gained a record...  │ chunk_index: 0 │
│ art_b63f7920..._1    │ Scientists observed ice cor... │ chunk_index: 1 │
└──────────────────────┴────────────────────────────────┴────────────────┘
```

1. **Main View (Tabular Records):**
   * `↑` / `↓` / `←` / `→`: Navigate across cells and rows.
   * `Return` (Enter): Expand selected cell into a full-screen scrollable modal.
   * **Lazy Loading:** 100 records load initially; scrolling to the bottom automatically fetches the next batch.
   * `s`: Enter the **Query Editor** modal.
   * `q` or `Ctrl + C`: Exit the browser.

2. **Search / Query Editor (`s`):**
   * `e`: Enter form edit mode.
   * `Space`: Toggle metadata query operators (`$eq`, `$in`, `$ne`, etc.).
   * `Esc`: Exit edit mode back to form navigation.
   * `Return` (Enter): Submit the `.get()` query and display matching vectors.
   * `c`: Clear query fields.
   * `s`: Return to Query Editor from search results.
   * `Esc`: Return to Main View table from search results.

---

### C. Python Direct Inspection (Host Script)
To inspect or verify ChromaDB programmatically without opening a TUI:
```python
import chromadb

# Connect to host port mapped by docker-compose
client = chromadb.HttpClient(host="localhost", port=8002)

# List all collections
collections = client.list_collections()
print(f"Collections: {[c.name for c in collections]}")

# Inspect gold_semantic_chunks
col = client.get_collection("gold_semantic_chunks")
print(f"Total Chunks: {col.count()}")

# Fetch sample records with documents and metadata
sample = col.get(limit=2)
for doc_id, doc, meta in zip(sample["ids"], sample["documents"], sample["metadatas"]):
    print(f"\nID: {doc_id}\nTitle: {meta.get('title')}\nPreview: {doc[:150]}...")
```

---

## 3. MongoDB (Document Storage)

MongoDB stores raw RSS discovery metadata (`bronze_links`) and finalized, curated articles (`gold_content`).

### A. Connection Parameters
* **Host Machine URI:** `mongodb://admin:changeme@localhost:27017/articlesDB?authSource=admin`
* **Docker Internal URI:** `mongodb://admin:changeme@mongo:27017/articlesDB?authSource=admin`
* **Username / Password:** `admin` / `changeme`
* **Database Name:** `articlesDB`
* **Primary Collections:**
  * `bronze_links`: Ingested RSS links, publication dates, raw thumbnail URLs.
  * `gold_content`: Cleaned Markdown text, calculated word count, extracted keywords, themes.

---

### B. Web GUI: Mongo Express
A pre-configured web GUI is available in the Docker stack:
* **URL:** `http://localhost:8081`
* **HTTP Basic Auth:** `admin` / `changeme`
* **Usage:**
  1. Open `http://localhost:8081` in your browser.
  2. Click on the `articlesDB` database.
  3. Click into `gold_content` or `bronze_links` to view documents in table or JSON tree format.
  4. Use the query box to filter documents: e.g., `{"partition_date": "2026-09-06"}`.

---

### C. CLI Access (`mongosh`)
Run interactive queries directly inside the MongoDB container:
```bash
docker exec -it mongo mongosh -u admin -p changeme --authenticationDatabase admin articlesDB
```

#### Essential Developer Queries
```javascript
// 1. Check document counts across collections
db.bronze_links.countDocuments()
db.gold_content.countDocuments()

// 2. View 1 sample article from gold_content formatted nicely
db.gold_content.findOne({}, { title: 1, word_count: 1, keywords: 1, partition_date: 1 })

// 3. Find all articles belonging to a specific date partition
db.gold_content.find({ partition_date: "2026-09-06" }, { title: 1, url: 1 }).pretty()

// 4. Find articles missing keywords (needs gold_article_keywords run)
db.gold_content.countDocuments({
  $or: [{ keywords: { $exists: false } }, { keywords: null }, { keywords: [] }]
})

// 5. Query article by deterministic ID
db.gold_content.findOne({ article_id: "art_b63f7920e6650b13" })
```

---

## 4. MinIO (S3-Compatible Object Storage)

MinIO serves as the data lake for raw HTML backups, intermediate sanitized JSONs, and serialized machine learning models.

### A. Connection Parameters
* **S3 API Endpoint (Host):** `http://localhost:9000`
* **S3 API Endpoint (Docker):** `http://minio:9000`
* **Web Console UI:** `http://localhost:9001`
* **Access Key / Secret Key:** `minioadmin` / `minioadmin`

---

### B. Bucket Structure & Key Paths
MinIO organizes data strictly by bucket and date prefixes:

| Bucket Name | Key Pattern | Content Type | Purpose |
| :--- | :--- | :--- | :--- |
| `raw-html` | `<partition_date>/<article_id>.html` | `text/html` | Full unmodified HTML page source |
| `silver-cleaned` | `<partition_date>/<article_id>.json` | `application/json`| Sanitized text & extracted metadata |
| `gold-content` | `<partition_date>/<article_id>.json` | `application/json`| Curated gold JSON backup |
| `bm25-index` | `gold_bm25_index/index.pkl` | `application/octet-stream` | Serialized BM25Okapi Python model |

---

### C. Web Console Inspection
1. Navigate to **`http://localhost:9001`**.
2. Log in with `minioadmin` / `minioadmin`.
3. In the left sidebar, click **Buckets**.
4. Click on `raw-html` or `silver-cleaned` to browse date folders (e.g. `2026-09-06/`).
5. Click on any `.html` or `.json` file to preview its content or download it directly to your machine.

---

### D. MinIO Client CLI (`mc`)
You can use the MinIO Client bundled inside the container to inspect storage from the terminal:

```bash
# 1. List all existing buckets
docker exec -it minio mc ls local/

# 2. List objects in a specific partition
docker exec -it minio mc ls local/silver-cleaned/2026-09-06/

# 3. View the content of a saved JSON document in terminal
docker exec -it minio mc cat local/silver-cleaned/2026-09-06/art_b63f7920e6650b13.json | head -n 30

# 4. Check disk usage per bucket
docker exec -it minio mc du local/raw-html
```

---

### E. Python Interaction Snippet (`minio`)
```python
from minio import Minio
import json

client = Minio(
    endpoint="localhost:9000",
    access_key="minioadmin",
    secret_key="minioadmin",
    secure=False
)

# List all buckets
buckets = client.list_buckets()
print("Buckets:", [b.name for b in buckets])

# Read a cleaned article JSON
response = client.get_object("silver-cleaned", "2026-09-06/art_b63f7920e6650b13.json")
data = json.loads(response.read().decode("utf-8"))
response.close()
response.release_conn()

print("Title:", data.get("title"))
print("Word Count:", data.get("word_count"))
```

---

## 5. Dagster Resource Architecture & Auto-Fallbacks

To allow seamless development both inside Docker containers and directly on the host machine, every custom resource implements an **automatic localhost fallback**:

```mermaid
flowchart TD
    Req["Resource Call"] --> TryDocker["Try Docker Service Host<br/>mongo:27017 / minio:9000 / chromadb:8000"]
    TryDocker -->|"Connected in Docker"| Success["Proceed with Call"]
    TryDocker -->|"Connection Refused"| TryHost["Fallback to Localhost<br/>localhost:27017 / localhost:9000 / localhost:8002"]
    TryHost -->|"Connected on Host"| Success
    TryHost -->|"Unreachable"| RaiseError["Raise Connection Error"]
```

* **`MongoIOManager`:** Tries `mongo:27017`. If connection ping fails, automatically swaps string to `localhost:27017`.
* **`MinIOResource`:** Tries `minio:9000`. If `list_buckets()` fails, automatically swaps endpoint to `localhost:9000`.
* **`ChromaResource`:** Tries `chromadb:8000`. If heartbeat fails, iterates through `localhost:8002`, `127.0.0.1:8002`, and falls back to a local disk `PersistentClient`.

---

## 6. Pipeline Execution & Troubleshooting Cheat Sheet

### Triggering Partitioned Runs via CLI
```bash
# Execute daily_news_job for a specific partition date
docker exec -it dagster_code_server dagster job execute \
  -m NewsPipeline.definitions \
  -j daily_news_job \
  --tags '{"dagster/partition": "2026-09-06"}'
```

### Triggering Full-Corpus Reindex Job
```bash
# Rebuild BM25 index and extract keywords across all articles
docker exec -it dagster_code_server dagster job execute \
  -m NewsPipeline.definitions \
  -j reindex_job
```

### Common Issues & Quick Fixes

| Issue | Cause | Fix |
| :--- | :--- | :--- |
| `Cannot access partition_key for a non-partitioned run` | Running `daily_news_job` without specifying `--tags '{"dagster/partition": "YYYY-MM-DD"}'` | Add the partition tag to the CLI command or select a partition partition square in the Dagster Web UI. |
| `All selected assets must have a PartitionsDefinition...` | Running `dagster asset materialize --select *` with a partition on unpartitioned assets | Select only partitioned assets: `--select bronze_links,silver_raw_html,silver_cleaned_articles,gold_content,gold_semantic_chunks`. |
| `ECONNREFUSED 127.0.0.1:8002` in container logs | Container trying to connect to host port `8002` instead of internal service port `8000` | Use Docker network hostnames inside containers (`chromadb:8000`, `mongo:27017`, `minio:9000`). |
| ChromaDB shows 0 collections after restart | Data directory mapped to `/chroma/chroma` instead of `/data` | Verify `docker-compose.yaml` maps `chroma_data:/data`. |
