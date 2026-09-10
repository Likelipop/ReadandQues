# Gold Layer: Serving, Vectorization & Lexical Indexing

The **Gold Layer** is the production-serving tier of the pipeline. It prepares cleaned text for high-performance retrieval, powering both **Dense Semantic Vector Search (ChromaDB)** and **Sparse Lexical Search (BM25)**, as well as the application's primary content database in MongoDB.

---

## 1. What It Does (Business & Functional Overview)

* **Curated Article Storage (`gold_content`):** Stages finalized, production-ready article documents into MongoDB for instant retrieval by web backends, APIs, and frontends.
* **Semantic Text Chunking (`gold_semantic_chunks`):** Splits long articles into context-preserving, overlapping text segments (chunks) and indexes them into ChromaDB for vector similarity queries (RAG).
* **Corpus Lexical Indexing (`gold_bm25_index`):** Evaluates the entire database of articles to build a global **BM25 Okapi** index, serialized and stored in MinIO for fast keyword search.
* **Automated Keyword & Theme Tagging (`gold_article_keywords`):** Automatically extracts 1 to 2 representative domain keywords per article using BM25 inverse document frequency (IDF) weights, updating MongoDB documents in place.

---

## 2. How It Works (Architectural & Technical Deep Dive)

The Gold layer consists of four assets defined in `NewsPipeline/src/NewsPipeline/assets/gold.py`:

```
silver_cleaned_articles (from MinIO)
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│ Asset: gold_content                                         │
│ Persists curated documents via MongoIOManager:              │
│ Target: MongoDB 'articlesDB' -> collection 'gold_content'   │
└──────────────┬──────────────────────────────┬───────────────┘
               │                              │
               ▼                              ▼
┌──────────────────────────────┐ ┌────────────────────────────┐
│ Asset: gold_semantic_chunks  │ │ Asset: gold_bm25_index     │
│ - LangChain text splitter    │ │ - Unpartitioned full scan  │
│   (chunk=800, overlap=100)   │ │ - spaCy lemmatization      │
│ - ID: {article_id}_{i}       │ │ - BM25Okapi model build    │
│ - Purge prior article chunks │ │ - Upload pickle to MinIO   │
│ - Micro-batch: 5 chunks/call │ │   "bm25-index/index.pkl"   │
│ - Target: ChromaDB collection│ └──────────────┬─────────────┘
│   "gold_semantic_chunks"     │                │
└──────────────────────────────┘                ▼
                                 ┌────────────────────────────┐
                                 │ Asset: gold_article_keywords│
                                 │ - Incremental: missing KWs │
                                 │ - Title x2 + 1500 chars    │
                                 │ - Score: TF * BM25 IDF     │
                                 │ - In-place $set update     │
                                 │   in MongoDB 'gold_content'│
                                 └────────────────────────────┘
```

---

### Deep Dive: Processing Assets

### A. `gold_content` (Curated Staging)
* **Input:** Sanitized documents from `silver_cleaned_articles`.
* **Execution:** Iterates over each clean article, verifies presence of `article_id` and `original_text`, and emits records to `MongoIOManager`.
* **Storage:** Upserted into MongoDB collection `gold_content` on key `{"article_id": doc["article_id"]}`.

---

### B. `gold_semantic_chunks` (Vector Database Indexing)
* **Chunking Algorithm:** Uses LangChain's `RecursiveCharacterTextSplitter`:
  - `chunk_size = 800` characters
  - `chunk_overlap = 100` characters
  - `separators = ["\n\n", "\n", ". ", " ", ""]`
  - **Fallback:** If LangChain is unavailable, it gracefully degrades to a simple paragraph splitter (`text.split("\n\n")`).
* **Deterministic Chunk Identifiers:** Each chunk receives an ID composed of the parent article ID and its zero-indexed sequence position:
  `f"{article_id}_{chunk_index}"` (e.g. `art_b63f7920e6650b13_0`, `art_b63f7920e6650b13_1`).
* **Idempotent Purge-Before-Add:** Before adding new chunks, `ChromaResource` executes:
  ```python
  col.delete(where={"article_id": aid})
  ```
  This removes all previously indexed chunks for each article in the batch, guaranteeing that backfilling or re-running a partition never creates duplicate vector records.
* **Micro-Batching Memory Protection (5 chunks/batch):**
  Generating vector embeddings inside Docker containers can trigger memory exhaustion (`SIGKILL` / Out-Of-Memory error). To prevent this, `ChromaResource` flushes embeddings in micro-batches of **exactly 5 chunks**:
  ```python
  batch_size = 5
  for i in range(0, len(chunks), batch_size):
      batch_slice = chunks[i : i + batch_size]
      col.add(ids=..., documents=..., metadatas=...)
  ```
  If a batch add throws an exception, it falls back to retrying each chunk individually.

---

### C. `gold_bm25_index` (Global Lexical Corpus Index)
* **Scope:** Corpus-level unpartitioned asset. Unlike daily partitioned news jobs, BM25 requires global document frequency statistics ($IDF$).
* **Data Retrieval:** Connects to MongoDB `articlesDB.gold_content` and queries all non-empty articles (`{"title": {"$ne": ""}}`).
* **Text Preprocessing Pipeline (`bm25_resource.py`):**
  1. `clean_text()`: Strips HTML entities (`&[a-z]+;`), removes all non-alphabetical characters, normalizes whitespace to lowercase.
  2. `tokenize_and_lemmatize()`: Uses the **spaCy** English model `en_core_web_sm` (with `parser` and `ner` disabled for speed). Filters out stopwords (`token.is_stop`), punctuation, and whitespace, returning root lemmas. *(Fallback to standard whitespace splitting if spaCy model is absent).*
* **Index Construction:** Fits a `BM25Okapi` model over all processed titles.
* **Artifact Persistence:** Serializes index payload using `pickle`:
  - Payload dictionary: `{"index": bm25_index, "corpus_ids": corpus_ids, "built_at": ..., "doc_count": ...}`
  - Target: MinIO bucket `bm25-index`, key `gold_bm25_index/index.pkl`.

---

### D. `gold_article_keywords` (Automated Term Extraction)
* **Scope:** Incremental unpartitioned asset.
* **Target Identification:** Only queries MongoDB for articles currently missing keywords:
  ```json
  { "$or": [{ "keywords": { "$exists": false } }, { "keywords": null }, { "keywords": [] }] }
  ```
* **Term Weighting Algorithm (`extract_keywords_from_bm25`):**
  1. **Sampling:** Concatenates the title twice (giving it 2x weight) with the first 1500 characters of the article text:
     `content_sample = f"{title} {title} {text[:1500]}"`
  2. **Tokenization:** Cleans and lemmatizes sample tokens using the BM25 preprocessor.
  3. **Term Frequency (TF):** Calculates raw frequency $TF(t)$ for each token.
  4. **Scoring:** Multiplies term frequency by the precomputed BM25 inverse document frequency:
     $$\text{Score}(t) = TF(t) \times IDF(t)$$
  5. **Keyword Selection:**
     - Always selects the top-scoring term (capitalized).
     - Selects a second keyword **only if** its score meets the minimum ratio:
       $$\text{Score}_2 \ge 0.5 \times \text{Score}_1$$
* **In-Place Mutation:** Updates MongoDB document directly:
  ```python
  collection.update_one(
      {"_id": doc["_id"]},
      {"$set": {"keywords": keywords, "theme": keywords[0]}}
  )
  ```

---

## 3. Data Contract & Storage Schemas

### A. MongoDB Document (`gold_content` Collection)
```json
{
  "_id": { "$oid": "66e0012ab9876543210fedcb" },
  "article_id": "art_b63f7920e6650b13",
  "url": "https://www.sciencedaily.com/releases/2026/09/260906101520.htm",
  "title": "Antarctica gained a record 695 billion tons of ice. Scientists found the surprising reason",
  "source": "ScienceDaily",
  "image_url": "https://sciencedaily.com/images/2026/09/ice_core.jpg",
  "thumbnail_url": "https://sciencedaily.com/images/2026/09/ice_core.jpg",
  "original_text": "### Surprising Ice Accumulation\n\nEast Antarctica experienced record-breaking snowfall...",
  "word_count": 524,
  "published_at": "2026-09-06T14:15:20+00:00",
  "partition_date": "2026-09-06",
  "sanitized_at": "2026-09-10T04:10:25.432109+00:00",
  "keywords": ["Antarctica", "Snowfall"],
  "theme": "Antarctica"
}
```

### B. ChromaDB Vector Record (`gold_semantic_chunks` Collection)
Each record stored in ChromaDB contains:
* **ID (`id`):** `art_b63f7920e6650b13_0` (String)
* **Document (`document`):** The raw text snippet (~800 characters)
* **Metadata (`metadata`):**
  ```json
  {
    "article_id": "art_b63f7920e6650b13",
    "title": "Antarctica gained a record 695 billion tons of ice...",
    "partition_date": "2026-09-06",
    "chunk_index": 0
  }
  ```
* **Embedding (`embedding`):** Dense floating-point vector automatically generated by ChromaDB's default embedding function (`all-MiniLM-L6-v2` or similar).

### C. MinIO Lexical Artifact (`bm25-index` Bucket)
* **Object Key:** `gold_bm25_index/index.pkl`
* **Content:** Python pickled dictionary containing:
  - `index`: `BM25Okapi` instance with token IDF dictionary and document lengths.
  - `corpus_ids`: List of article IDs matching the index internal document offsets.
  - `doc_count`: Integer representing total indexed documents.
  - `built_at`: ISO timestamp string.

---

## 4. Failure Modes & Idempotency Safeguards

| Failure Risk | Safeguard Implemented |
| :--- | :--- |
| **PyTorch / Tokenizer OOM Crash** | Pipeline executes in-process (`in_process_executor`) and upserts ChromaDB chunks in micro-batches of 5 to keep memory footprint flat. |
| **Duplicate Vector Chunks on Backfill** | `ChromaResource` executes `col.delete(where={"article_id": aid})` before upserting chunks. |
| **Missing spaCy model** | `BM25Resource` falls back automatically to regex/whitespace tokenization without crashing. |
| **Corpus Empty during BM25 Build** | `gold_bm25_index` logs an info message and yields status `"empty"` with `doc_count=0` instead of raising an error. |
