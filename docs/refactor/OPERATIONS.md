# Operations and Recovery Guide

This operations guide defines procedures for backup, restore, non-SQL migrations, search projection reindexing, deployment health checks, and recovery from failed AI/orchestration runs.

---

## 1. Datastore Backups & Restore

### PostgreSQL (Transactional Ledger & User Data)
```bash
# Backup
pg_dump -U postgres -h localhost -d readandques_db > backup_postgres.sql

# Restore
psql -U postgres -h localhost -d readandques_db < backup_postgres.sql
```

### MongoDB (Canonical Articles & Artifacts)
```bash
# Backup
mongodump --uri="mongodb://admin:changeme@localhost:27017/articlesDB?authSource=admin" --out=/backup/mongo

# Restore
mongorestore --uri="mongodb://admin:changeme@localhost:27017/articlesDB?authSource=admin" /backup/mongo
```

### MinIO (Raw Bronze Objects & Manifests)
```bash
# Backup using MinIO Client (mc)
mc mirror localminio/bronze /backup/minio/bronze
```

---

## 2. Non-SQL Versioned Migrations

Run locked, checksummed non-SQL migrations for MongoDB validators and indexes:
```bash
.venv/bin/python ReadAndQues/manage.py migrate_non_sql
```

---

## 3. Projection Reindexing (ChromaDB & BM25)

To idempotently rebuild ChromaDB vector embeddings and the BM25 lexical index directly from canonical article records:
```bash
.venv/bin/python ReadAndQues/manage.py rebuild_projections
```

---

## 4. Deployment Health & Readiness Checks

Verify database connections, indexes, MinIO bucket policies, and vector stores:
```bash
.venv/bin/python ReadAndQues/manage.py check_deployment_health
```

---

## 5. Failed Run Recovery Procedures

1. **AI Tool Failures**:
   - Inspect PostgreSQL `AIRunLog` for specific `run_id` and error tracebacks.
   - Retry failed jobs via `OrchestrationFacade.run_ai_only_pipeline_async(article_id)`.

2. **Pipeline Failures**:
   - Run `python manage.py audit_data` to locate documents missing `article_id` or failing contract validation.
   - Re-run daily pipeline with `OrchestrationFacade.run_daily_pipeline()`.

---

## 6. Legacy Deprecation Soak Period

- Legacy adapters (`LegacyArticleReadAdapter`) remain active during the initial soak release.
- Legacy Mongo collections (`gold_articles`) are safely archived using:
```bash
.venv/bin/python ReadAndQues/manage.py archive_legacy_collections
```
- Legacy adapters may be removed only after a successful 30-day soak period with 0 validation errors recorded in `audit_data`.
