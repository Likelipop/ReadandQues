# Component Guide: Data Layer & Datastores

This document details the data layer architecture, datastore ownership rules, ZEN Pydantic models, repositories with `@db_safe` error boundaries, native PyMongo connection management, and non-SQL migration system.

---

## 1. Datastore Ownership Principles

According to [ADR-0001](file:///home/likelipop/Project/ReadandQues/docs/refactor/adr/0001-data-ownership.md), each datastore in ReadAndQues has strict, explicit single-source-of-truth ownership:

```
+-------------------+-------------------------------------------------------------------+
| Datastore         | Ownership & Data Responsibility                                  |
+-------------------+-------------------------------------------------------------------+
| PostgreSQL        | Transactional ledgers (AIRunLog, ArticleImportRequest,            |
|                   | ExamAttemptLog) and user account management.                      |
| MongoDB           | 1. Metadata Routing & Indexing (article_index collection).        |
|                   | 2. AI Feature Data & Exams (exams collection).                    |
| MinIO (S3)        | Primary Data Lake (Medallion Architecture):                       |
|                   | - Bronze: Raw HTML & Source Metadata                              |
|                   | - Silver: Cleaned & Validated text                                |
|                   | - Gold: AI-enriched analysis and final state                      |
| ChromaDB          | Vector embeddings (Gold chunks) for semantic search.              |
| BM25              | In-memory lexical index for fast keyword matching.                |
+-------------------+-------------------------------------------------------------------+
```

---

## 2. Canonical ZEN Pydantic Data Models

All data passing through the system is validated against clean, unified Pydantic v2 domain models defined in [service/domain/models.py](file:///home/likelipop/Project/ReadandQues/ReadAndQues/service/domain/models.py):

- **`Article`**: Core article entity (`article_id`, `title`, `url`, `source_name`, `stage`, `status`, `summary`, `theme`, `genre`, `exams`).
- **`Exam`**, **`Question`**, **`Option`**: Streamlined quiz examination structures.
- **`ExamAttempt`**: User test attempt recording `user_id`, `article_id`, `score`, `total_questions`, `answers`, `elapsed_time`.
- **`RawSourceManifest`**: MinIO raw Bronze object metadata (`article_id`, `url`, `sha256_hash`, `raw_size_bytes`, `stage`).
- **`Stage`** (`BRONZE`, `SILVER`, `GOLD`) & **`Status`** (`PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`): Clean Medallion enums.

> Note: Legacy imports from `service.domain.contracts` and `service.domain.enums` are maintained as backward-compatibility proxies.

---

## 3. Pure Atomic Database Layer & Native Connection Management

To prevent eager side-effect network I/O at Python import time and maximize IDE autocomplete support:

- **`database/Mongo/connection.py`**: Uses native PyMongo `MongoClient(..., connect=False)` with a clean `get_collection(name: str) -> Collection` helper function. Zero custom proxy classes.
- **Pure Atomic I/O**: Lower-level functions in `database/Mongo/`, `database/Minio/`, and `database/Chroma/` contain **zero domain imports** (`from service.domain...`). They accept primitive types (`str`, `dict`, `bytes`) and fail-fast without silent `try-except` catch-alls.

---

## 4. Repositories & `@db_safe` Error Boundary

All application database access must pass through the Repository layer in [service/repositories/](file:///home/likelipop/Project/ReadandQues/ReadAndQues/service/repositories/):

- **`ArticleRepository`**: Handles canonical article tracking and lifecycle state.
- **`AttemptRepository`**: Handles saving exam attempt logs to PostgreSQL `ExamAttemptLog`.
- **`PipelineRepository`**: Manages article stage progression, AI status updates, RSS tracking, and pipeline execution logs.
- **`ContentRepository`**: Manages Medallion storage (MinIO), RawSourceManifest generation, paraphrase cache, and homepage section cache.
- **`SearchRepository`**: Unified search gateway combining BM25 keyword search, ChromaDB vector search, text chunking, and Reciprocal Rank Fusion (RRF).
- **`UserActivityRepository`**: Handles user reading history, highlights, and vocabulary tracking.

### Error Boundary (`@db_safe`)
All repository methods are protected by the `@db_safe` decorator ([service/repositories/utils.py](file:///home/likelipop/Project/ReadandQues/ReadAndQues/service/repositories/utils.py)). Upon database or network infrastructure failures, `@db_safe` logs the full Python traceback (`exc_info=True`) and returns a safe fallback value (`None`, `False`, `[]`, or `{}`).

---

## 5. Non-SQL Versioned Migrations

MongoDB validators and indexes are managed through a locked, checksummed migration runner in [service/migrations_nonsql/runner.py](file:///home/likelipop/Project/ReadandQues/ReadAndQues/service/migrations_nonsql/runner.py).

To apply non-SQL migrations:
```bash
.venv/bin/python ReadAndQues/manage.py migrate_non_sql
```

---

## 6. Management Commands Reference

- **`python manage.py audit_data`**: Scans `article_index` records and validates model compliance against `ArticleRepository`.
- **`python manage.py rebuild_projections`**: Rebuilds ChromaDB vector embeddings and BM25 index using `SearchRepository`.
- **`python manage.py archive_legacy_collections`**: Safely archives legacy collections into `archived_legacy_articles` without deleting raw data.
- **`python manage.py check_deployment_health`**: Verifies PostgreSQL, MongoDB, MinIO, BM25, and ChromaDB connectivity and readiness.
