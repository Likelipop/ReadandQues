# 📋 Task 04: Database Infrastructure & Polyglot Lifecycle

> **Git Branch**: `feature/04-database-infrastructure-lifecycle`

## 🎯 Goal
Standardize multi-store polyglot data access, local HuggingFace embeddings, schema initialization, and multi-store cascading deletion.

---

## 🛠 Detailed Technical Changes

### 1. Polyglot Adapter Standardization (`service/infrastructure/`)
- **PostgreSQL 15**: Django ORM (`models.py`) for transactional ledgers (`AIRunLog`, `ArticleImportRequest`, `ExamAttemptLog`, `TopicProficiency`, Auth).
- **MongoDB 7**: Raw `pymongo` with Pydantic v2 schemas (`domain/schemas.py`) protected by `@db_safe`.
- **MinIO S3**: Immutable buckets (`bronze-articles`, `silver-articles`, `gold-articles`).
- **ChromaDB**: Dense vector store (`news_chunks` parent-child collection).
- **BM25**: In-memory tokenized lexical search index (`rank_bm25` + spaCy `en_core_web_sm`).

### 2. Local HuggingFace Embedding Model
- Configure ChromaDB to use local `all-MiniLM-L6-v2` via `sentence-transformers`.
- 100% offline execution, zero API keys required for vector embeddings.

### 3. Management Command: `python manage.py setup_db`
- Replaces legacy `migrations_nonsql`.
- Idempotent execution:
  - Runs PostgreSQL `manage.py migrate`.
  - Creates MongoDB indexes (`url_unique`, `stage_1`, `published_at_desc`, `article_id_unique`, compound indexes).
  - Ensures MinIO `bronze`, `silver`, `gold` buckets exist.
  - Builds BM25 corpus from gold article titles.

### 4. Cascading Multi-Store Hard Delete
- Implement `delete_article_hard(article_id: str)` in `services.py`:
  1. MongoDB: Deletes `article_index`, `exams`, `user_highlights`, `reading_history`.
  2. MinIO: Purges Bronze, Silver, Gold objects.
  3. ChromaDB: Deletes all vector chunks matching `article_id`.
  4. BM25: Rebuilds in-memory corpus.

---

## ✅ Acceptance Criteria
- [ ] `python manage.py setup_db` completes without errors on fresh database containers.
- [ ] ChromaDB generates embeddings locally without external API requests.
- [ ] Hard deletion purges all article artifacts across MongoDB, MinIO, ChromaDB, and BM25 simultaneously.
