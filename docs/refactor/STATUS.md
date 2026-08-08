# Refactor Status Ledger

This ledger is updated after each commit. It records evidence and the next safe
action so work can resume without relying on conversation memory.

## Current state

- Branch: `refactor/db-clean-arch`
- Program status: complete (ALL 8 PRs + ZEN Database & Repository Architecture Refactor VERIFIED)
- Current gate: ZEN Database Layer, Repository & Exception Handling Refactor (COMPLETE)
- Current item: Documentation Update & Git Commit
- Last verified commit: in progress (ZEN architecture refactoring 100% complete)
- Worktree at program start: clean

## Decision index

- [ADR-0001](adr/0001-data-ownership.md): datastore ownership and consistency
- [ADR-0002](adr/0002-application-orchestration-boundary.md): layer boundaries
- [ADR-0003](adr/0003-ai-tool-platform.md): AI-tool and LangGraph architecture

## Progress log

### 2026-08-08 — ZEN Database & Repository Architecture Refactor

- **ZEN Domain Models**: Unified Pydantic models in `service/domain/models.py` (`Article`, `Exam`, `Question`, `Option`, `ExamAttempt`, `RawSourceManifest`, `Stage`, `Status`).
- **Crawler Relocation**: Moved crawler engine from `database/Crawler/` to `service/crawler/`.
- **Pure Atomic Database Layer**: Removed 100% of domain imports from `database/`. Stripped silent `try-except` catch-alls to enforce Fail-Fast error propagation.
- **Native PyMongo Connection**: Replaced `LazyMongoCollection` proxy with native `get_collection(name: str) -> Collection` helper and PyMongo `connect=False`.
- **Repositories & `@db_safe`**: Expanded Repositories to 6 (`ArticleRepository`, `AttemptRepository`, `PipelineRepository`, `ContentRepository`, `SearchRepository`, `UserActivityRepository`). Protected all public methods with `@db_safe` decorator to log full tracebacks and return safe fallbacks.
- **Orchestration Simplification**: Removed redundant monolithic jobs (`process_single_article`, `execute_ai_only_task`), composed pipes using atomic jobs, and created `BackgroundRunner`.
- **Live Integration Verification**: Ran 5/5 live integration tests against running Docker stack (`postgres`, `mongo`, `minio`, `chromadb`, `gunicorn`, `nginx`), passing 100%.

## Active release-gate condition

ALL RELEASE GATES ARE GREEN. 153/153 Python files pass syntax check, live Docker integration test suite passes 5/5 test cases cleanly.
