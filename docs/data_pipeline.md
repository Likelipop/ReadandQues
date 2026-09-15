# Data Pipeline (Dagster ETL)

The Data Pipeline documentation has been organized into a comprehensive, modular suite located under **[`docs/data_pipeline/`](./data_pipeline/overview.md)**:

1. **[Overview & Architecture](./data_pipeline/overview.md)** — Architectural design, Medallion flow, storage matrix, orchestration model.
2. **[Bronze Layer (Ingestion)](./data_pipeline/bronze.md)** — RSS parsing, URL deduplication, deterministic MD5 IDs, MongoDB staging.
3. **[Silver Layer (Cleansing)](./data_pipeline/silver.md)** — Raw HTML MinIO backup, Trafilatura extraction, regex sanitization, 150-word quality gate.
4. **[Gold Layer (Serving & Indexing)](./data_pipeline/gold.md)** — LangChain recursive chunking, ChromaDB vector indexing, BM25Okapi corpus build, TF-IDF keywords.
5. **[Developer Operations & Database Guide](./data_pipeline/dev_guide.md)** — Step-by-step connection guides, CLI tools (`chroma browse` navigation, `mongosh`, MinIO `mc`), and Dagster execution.
