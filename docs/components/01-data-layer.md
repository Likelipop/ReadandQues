# Component Guide: Data Layer & Datastores

This document details the data layer architecture, datastore ownership rules, Pydantic contracts, repositories, lazy connections, and non-SQL migration system.

---

## 1. Datastore Ownership Principles

According to [ADR-0001](file:///home/likelipop/Project/ReadandQues/docs/refactor/adr/0001-data-ownership.md), each datastore in ReadAndQues has strict, explicit single-source-of-truth ownership:

```
+-------------------+-------------------------------------------------------------------+
| Datastore         | Ownership & Data Responsibility                                  |
+-------------------+-------------------------------------------------------------------+
| PostgreSQL        | Transactional ledgers (AIRunLog, ArticleImportRequest,            |
|                   | ExamAttemptLog) and user account management.                      |
| MongoDB           | Canonical article documents (gold_articles collection).           |
| MinIO (S3)        | Raw Bronze JSON source scrapes + SHA-256 integrity manifests.     |
| ChromaDB          | Vector embeddings (Silver/Gold chunks) for semantic search.       |
| BM25              | In-memory lexical index for fast keyword matching.                |
+-------------------+-------------------------------------------------------------------+
```

---

## 2. Canonical Pydantic Data Contracts

All data passing through the system is validated against typed Pydantic v2 data contracts defined in [service/domain/contracts.py](file:///home/likelipop/Project/ReadandQues/ReadAndQues/service/domain/contracts.py):

- **`ArticleContract`**: Canonical article structure (`article_id`, `title`, `content`, `url`, `status`, `created_at`, `quizzes`).
- **`ExamContract`**: Examination structure containing comprehension questions, options, and explanations.
- **`ExamAttemptContract`**: User test attempt recording `user_id`, `score`, `total_questions`, `answers`, `highlighted_markdown`.
- **`RawSourceManifestContract`**: MinIO raw Bronze object metadata (`object_key`, `sha256_hash`, `source_url`, `scraped_at`).

Deterministic Article ID Generation:
```python
from service.domain import generate_article_id

article_id = generate_article_id(url="https://example.com/news/1")
# Returns deterministic ID e.g. "art_a1b2c3d4e5f67890"
```

---

## 3. Lazy Side-Effect Free Connections

To prevent network I/O or connection failures at Python import time, datastore drivers use lazy proxies:

- **`LazyMongoCollection`** in [database/Mongo/connection.py](file:///home/likelipop/Project/ReadandQues/ReadAndQues/database/Mongo/connection.py)
- **`LazyMinioClient`** in [database/Minio/connection.py](file:///home/likelipop/Project/ReadandQues/ReadAndQues/database/Minio/connection.py)
- **`LazyChromaClient`** in [database/Chroma/connection.py](file:///home/likelipop/Project/ReadandQues/ReadAndQues/database/Chroma/connection.py)

Connections are established on-demand upon first database query, allowing unit tests and offline management tools to run cleanly without live database infrastructure.

---

## 4. Non-SQL Versioned Migrations

MongoDB validators and indexes are managed through a locked, checksummed migration runner in [service/migrations_nonsql/runner.py](file:///home/likelipop/Project/ReadandQues/ReadAndQues/service/migrations_nonsql/runner.py).

To apply non-SQL migrations:
```bash
.venv/bin/python ReadAndQues/manage.py migrate_non_sql
```

Migration scripts live in [service/migrations_nonsql/versions/](file:///home/likelipop/Project/ReadandQues/ReadAndQues/service/migrations_nonsql/versions/). Each script must define an `apply(db)` function and is checksummed in the MongoDB `_migrations` collection to detect drift.

---

## 5. Repositories

Database operations are abstracted through repositories in [service/repositories/](file:///home/likelipop/Project/ReadandQues/ReadAndQues/service/repositories/):

- **`ArticleRepository`**: Handles canonical article reading/writing in MongoDB (`gold_articles`). Includes `LegacyArticleReadAdapter` for backward compatibility with older document structures.
- **`AttemptRepository`**: Handles saving exam attempt logs to PostgreSQL `ExamAttemptLog` with fallback querying from MongoDB.

Example usage:
```python
from service.repositories import ArticleRepository

repo = ArticleRepository()
article = repo.get_by_id("art_a1b2c3d4e5f67890")
```

---

## 6. Management Commands Reference

- **`python manage.py audit_data`**: Scans MongoDB articles and validates schema compliance against `ArticleContract`.
- **`python manage.py rebuild_projections`**: Rebuilds ChromaDB vector embeddings and BM25 index from MongoDB.
- **`python manage.py archive_legacy_collections`**: Safely archives legacy Gold collections into `archived_legacy_articles` without deleting raw data.
- **`python manage.py check_deployment_health`**: Verifies PostgreSQL, MongoDB, MinIO, BM25, and ChromaDB connectivity and readiness.
