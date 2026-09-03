# 🗄️ DATABASE ENGINEER TASK BACKLOG & ACTION PLAN

**Project**: ReadAndQues — Interactive Academic Reading & AI Quiz Platform  
**Target Milestone**: Medallion Data Lake Integrity, Connection Pooling & Index Optimization  
**Assigned Role / Subagent**: Database Engineer (PostgreSQL, MongoDB 7, MinIO S3, ChromaDB)

---

## 🎯 Objective
Harden multi-database tier operations (Postgres for transactional auth/logs, MongoDB for document storage, MinIO for bronze/silver/gold object lake, Chroma for dense vector embeddings), configure connection pooling, and verify index performance.

---

## 📋 Detailed Task Breakdown

### Task DB-01: Fix Non-SQL Migration Runner & Versioning
- **Files**: 
  - `ReadAndQues/service/migrations_nonsql/runner.py`
  - `ReadAndQues/service/migrations_nonsql/versions/0001_initial_mongo_validators_and_indexes.py`
- **Priority**: High (P1)
- **Status**: Ready for Sprint
- **Technical Specifications**:
  1. Fix broken import in `runner.py`: Replace legacy `from database.Mongo.connection import get_mongo_db` with `from service.infrastructure.mongo.connection import get_mongo_db`.
  2. Implement idempotent checksum verification to ensure schema validator migrations run reliably in Docker startup commands without crashing on existing validator collections.
  3. Integrate `python manage.py setup_db` and `NonSqlMigrationRunner` into automated deployment pipeline.

### Task DB-02: Configure Production MongoDB Connection Pooling & Resilience
- **File**: `ReadAndQues/service/infrastructure/mongo/connection.py`
- **Priority**: High (P1)
- **Status**: Ready for Sprint
- **Technical Specifications**:
  1. Configure PyMongo MongoClient with explicit pooling parameters:
     - `maxPoolSize=100`
     - `minPoolSize=10`
     - `maxIdleTimeMS=45000`
     - `waitQueueTimeoutMS=5000`
     - `retryWrites=True`
  2. Implement proper MongoClient disposal / cleanup on worker process shutdown.

### Task DB-03: Medallion Storage Lifecycle & MinIO Data Retention Policies
- **Files**: 
  - `ReadAndQues/service/infrastructure/minio/object_store.py`
  - `ReadAndQues/service/infrastructure/minio/connection.py`
- **Priority**: Medium (P2)
- **Status**: Backlog
- **Technical Specifications**:
  1. Review S3 object keys across Medallion layers:
     - Bronze: `bronze/{article_id}/raw.html` and `bronze/{article_id}/metadata.json`
     - Silver: `silver/{article_id}/clean.json`
     - Gold: `gold/{article_id}/enriched.json`
  2. Configure ILM (Information Lifecycle Management) rule on MinIO to archive or expire raw bronze HTML older than 90 days if storage quotas are constrained.
  3. Ensure deterministic MD5 / SHA-256 integrity verification when uploading and reading blobs.

### Task DB-04: Relational PostgreSQL Schema & Index Tuning
- **Files**: `ReadAndQues/service/models.py`, `ReadAndQues/accounts/models.py`
- **Priority**: Medium (P2)
- **Status**: Backlog
- **Technical Specifications**:
  1. Check PostgreSQL indexes on `ExamAttemptLog` and `TopicProficiency`:
     - Index on `ExamAttemptLog(user_id, submitted_at DESC)` for fast profile history retrieval.
     - Unique composite index on `TopicProficiency(user_id, topic)` to prevent race conditions during concurrent quiz submissions.
  2. Audit `UserProfile` select_for_update transactional locking on star balance deductions during high concurrency article imports.

### Task DB-05: ChromaDB Collection Hygiene & Persistence Verification
- **Files**: `ReadAndQues/service/infrastructure/chroma/vector_store.py`, `ReadAndQues/service/infrastructure/chroma/connection.py`
- **Priority**: Medium (P2)
- **Status**: Backlog
- **Technical Specifications**:
  1. Ensure article chunk embeddings store complete metadata (`article_id`, `title`, `theme`, `genre`, `chunk_id`, `source_url`) for filtered vector queries.
  2. Verify ChromaDB persistence volume in Docker Compose (`chroma_data:/chroma/chroma`) to prevent embedding loss during container restarts.

---

## 🧪 Acceptance Criteria & Test Validation
- [ ] Non-SQL migrations run cleanly with `NonSqlMigrationRunner().run()`.
- [ ] `python manage.py setup_db` completes with 0 warnings.
- [ ] Database connection pool withstands concurrent load without connection starvation.
