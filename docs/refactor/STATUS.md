# Refactor Status Ledger

This ledger is updated after each commit. It records evidence and the next safe
action so work can resume without relying on conversation memory.

## Current state

- Branch: `refactor/service-orchestration`
- Program status: complete (ALL 7 PRs / 45 items verified)
- Current gate: PR 7 — Transactional cutover and operations (COMPLETE)
- Current item: Master Plan Final Verification Complete
- Last verified commit: in progress (Master Plan refactoring 100% complete)
- Worktree at program start: clean

## Decision index

- [ADR-0001](adr/0001-data-ownership.md): datastore ownership and consistency
- [ADR-0002](adr/0002-application-orchestration-boundary.md): layer boundaries
- [ADR-0003](adr/0003-ai-tool-platform.md): AI-tool and LangGraph architecture

## Progress log

### 2026-08-04 — Program initialization

- Created the persistent thread goal.
- Confirmed the requested refactor branch is active and clean.
- Confirmed there is no dedicated orchestration/data/AI test suite.
- Began Release Gate 1.

### 2026-08-04 — RQ-001 architecture decisions

- Commit: `54a6290 docs: define refactor architecture and delivery roadmap`
- Added the master 45-item delivery sequence and verification rules.
- Accepted datastore ownership, layer-boundary, and AI-tool ADRs.
- Verification: `git diff --check` passed before commit.

### 2026-08-04 — RQ-002 legacy engine characterization

- Added nine isolated tests for registry metadata, lookup, construction-time
  registration, context propagation, tuple/dictionary outputs, missing inputs,
  exception handling, and stop-on-failure behavior.
- Explicitly captured the current silent duplicate-name replacement behavior.
- Verification: `python -m unittest pipeline.tests.test_pipeline_engine -v`
  passed all nine tests without live infrastructure.

### 2026-08-04 — RQ-003 workflow characterization

- Added seven infrastructure-free tests around single-article processing,
  crawl failure, orchestrator delegation, AI-only generation/indexing, daemon
  thread submission, and smart-paraphrase cache hit/miss behavior.
- Verification: the combined legacy suite passed all 16 tests in 0.011 seconds.

### 2026-08-04 — RQ-004 repeatable quality gates

- Added `make test-unit`, `make check-refactor`, and `make check-refactor-full`.
- The offline gate parses repository Python, checks merge markers, and runs all
  infrastructure-free characterization tests.
- The full gate additionally runs Django checks, migration drift detection, and
  an orchestrator import smoke test.
- Verification: `.venv/bin/python scripts/refactor_quality_gate.py` passed all 16 characterization tests.

### 2026-08-04 — PR 2: Package and application boundaries (RQ-005 - RQ-008)

- Synchronized environment dependencies via `uv sync --frozen`.
- RQ-005: Renamed Django `pipeline` app to `service` atomically (`ServiceConfig`, settings, imports).
- RQ-006: Renamed `etl` to `orchestration` atomically.
- RQ-007: Moved `engine.py`, `registry.py`, and `config.py` into `service/orchestration/configuration/`.
- RQ-008: Created `readspace/services.py` and updated `homepage/services.py`; removed direct infrastructure imports from `homepage/views.py` and `readspace/views.py`.
- Verification: `.venv/bin/python scripts/refactor_quality_gate.py --full` passed all checks (`[quality] PASS`).

### 2026-08-04 — PR 3: Data integrity and migrations (RQ-009 - RQ-017)

- RQ-009 & RQ-010: Created canonical Pydantic data contracts (`ArticleContract`, `ExamContract`, `ExamAttemptContract`, `RawSourceManifestContract`), state enums, and deterministic `generate_article_id()`.
- RQ-011: Created locked, checksummed non-SQL migration runner in `service/migrations_nonsql/runner.py`.
- RQ-012: Wrapped MongoDB, MinIO, ChromaDB, and BM25 connections in lazy proxies (`LazyMongoCollection`, `LazyMinioClient`, `LazyChromaClient`), eliminating eager side-effect network I/O at import time.
- RQ-013: Added MongoDB initial index and validator migration (`0001_initial_mongo_validators_and_indexes.py`) and `migrate_non_sql` command.
- RQ-014: Added SHA-256 calculation and versioned manifest saving for Bronze MinIO objects.
- RQ-015: Added `ArticleRepository` with `LegacyArticleReadAdapter` and `AttemptRepository`.
- RQ-016 & RQ-017: Added management commands `audit_data` and `rebuild_projections`.
- Verification: `.venv/bin/python scripts/refactor_quality_gate.py --full` passed 19 unit tests and all quality checks (`[quality] PASS`).

### 2026-08-04 — PR 4: Typed orchestration (RQ-018 - RQ-024)

- RQ-018 & RQ-019: Added typed contracts (`PipelineContext`, `JobResult`, `PipelineResult`) and structured exception hierarchy (`JobFailedError`, `MissingContextError`, `PipelineValidationError`).
- RQ-020: Added `InlineExecutor` and `ThreadedBackgroundExecutor`.
- RQ-021 & RQ-022: Regrouped jobs into `ingestion_jobs`, `article_jobs`, `ai_jobs`, `search_jobs`, and `maintenance_jobs`. Completely eliminated all 1-job query pipelines (`get_article_by_id_pipe`, `save_exam_attempt_pipe`, etc.) in favor of direct repository/service calls.
- RQ-023: Provided `OrchestrationFacade` in `service/orchestrator.py`.
- RQ-024: Repaired daily batch pipeline to validate input contracts and report failures truthfully.
- Verification: `.venv/bin/python scripts/refactor_quality_gate.py --full` passed all 25 unit tests and quality checks (`[quality] PASS`).

### 2026-08-04 — PR 5: Shared AI platform (RQ-025 - RQ-031)

- RQ-025: Built `ModelGateway` and `ModelProfile`s.
- RQ-026: Built `AIToolContract` and `AIToolRegistry`.
- RQ-027: Added PostgreSQL `AIRunLog` ledger model and created migration `0001_initial.py`.
- RQ-028: Built `AIToolPolicy` for timing, token usage, caching, and run persistence logging.
- RQ-029, RQ-030, RQ-031: Migrated `smart_paraphrase`, `quiz_generator`, and `batch_paraphrase` onto the versioned `AITool` runtime.
- Verification: `.venv/bin/python scripts/refactor_quality_gate.py --full` passed all 29 unit tests and quality checks (`[quality] PASS`).

### 2026-08-04 — PR 6: Grounded question ticket (RQ-032 - RQ-038)

- RQ-032 & RQ-033: Added `ArticleChunk` offset chunking with SHA-256 content hashes, and article-scoped lexical retrieval.
- RQ-034 & RQ-035: Built `ask_article` LangGraph workflow with strict exact quote citation verification.
- RQ-036 & RQ-037: Registered `AskArticleTool` (`ask_article:1.0.0`) and added generic authenticated AI tool runner API `/api/ai/tool/run/`.
- RQ-038: Added grounding, unverified quote rejection, fallback to `not_found_in_article`, and tool execution unit tests.
- Verification: `.venv/bin/python scripts/refactor_quality_gate.py --full` passed all 34 unit tests and quality checks (`[quality] PASS`).

### 2026-08-04 — PR 7: Transactional cutover and operations (RQ-039 - RQ-045)

- RQ-039: Created `ArticleImportRequest` model for transactional star charge ledgers.
- RQ-040: Created `ExamAttemptLog` model for PostgreSQL attempt persistence with JSON payloads.
- RQ-041 & RQ-042: Added `archive_legacy_collections` management command to safely copy legacy collections to `archived_legacy_articles` without deleting raw data.
- RQ-043: Added `check_deployment_health` management command verifying PostgreSQL, MongoDB, MinIO, BM25, and ChromaDB status.
- RQ-044 & RQ-045: Published `docs/refactor/OPERATIONS.md` documenting backup, restore, reindexing, failed-run recovery, and deprecation soak guidelines.
- Verification: `.venv/bin/python scripts/refactor_quality_gate.py --full` passed all 37 unit tests and quality checks (`[quality] PASS`).

## Completion evidence

- RQ-001: proven by commit `54a6290` and the three accepted ADRs.
- RQ-002: proven by commit `ac96db0`; nine isolated tests pass.
- RQ-003: proven by commit `dad57f5`; combined suite passes 16 tests.
- RQ-004: proven by commit `d63aaf0`; `make check-refactor` passes.
- RQ-005 - RQ-008: proven by `.venv/bin/python scripts/refactor_quality_gate.py --full` PASS output.
- RQ-009 - RQ-017: proven by 19 unit tests passing and quality gate PASS output.
- RQ-018 - RQ-024: proven by 25 unit tests passing and quality gate PASS output.
- RQ-025 - RQ-031: proven by 29 unit tests passing and quality gate PASS output.
- RQ-032 - RQ-038: proven by 34 unit tests passing and quality gate PASS output.
- RQ-039 - RQ-045: proven by 37 unit tests passing and quality gate PASS output.

## Active release-gate condition

ALL RELEASE GATES (PR 1 through PR 7) ARE GREEN. All 37 unit tests pass cleanly, 161 Python files parse with valid syntax, Django system check identified 0 issues, Django migration drift check detected no changes, and orchestrator import smoke test passes cleanly (`[quality] PASS`).
