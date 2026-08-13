# Component Guide: Orchestration Engine & Pipelines

This document describes the typed pipeline orchestration engine, ZEN atomic job domain modules, `BackgroundRunner`, and `OrchestrationFacade`.

---

## 1. Boundary & Responsibilities

The Orchestration Engine in [service/orchestration/](file:///home/likelipop/Project/ReadandQues/ReadAndQues/service/orchestration/) manages multi-step batch processing and background pipelines ([ADR-0002](file:///home/likelipop/Project/ReadandQues/docs/refactor/adr/0002-application-orchestration-boundary.md)):

- Single-step query operations (e.g., fetching an article by ID) use direct repository calls and do **not** use pipelines.
- Multi-step workflows (e.g., crawl web page -> ingest Bronze -> extract Silver -> AI enrich Gold -> vector index) run through atomic orchestration `Pipe`s composed in [service/orchestration/pipes.py](file:///home/likelipop/Project/ReadandQues/ReadAndQues/service/orchestration/pipes.py).

---

## 2. Typed Contracts & Exception Hierarchy

Pipeline execution uses Pydantic v2 typed contracts defined in [service/orchestration/contracts.py](file:///home/likelipop/Project/ReadandQues/ReadAndQues/service/orchestration/contracts.py):

- **`PipelineContext`**: Thread-safe dictionary container holding initial inputs and intermediate job outputs.
- **`JobResult`**: Status (`completed`, `failed`, `skipped`), output data, duration in ms, and error message for an individual job step.
- **`PipelineResult`**: Aggregated result of a pipeline execution (`pipeline_name`, `status`, `stage_results`, `total_duration_ms`).

Structured Exceptions ([service/orchestration/exceptions.py](file:///home/likelipop/Project/ReadandQues/ReadAndQues/service/orchestration/exceptions.py)):
- `OrchestrationError`: Base exception for pipeline failures.
- `JobFailedError`: Raised when a job step fails or raises an unhandled exception.
- `MissingContextError`: Raised during contract validation when required inputs are missing from `PipelineContext`.
- `PipelineValidationError`: Raised when pipe configuration or job signatures are invalid.

---

## 3. Background Runner & Facade

Pipelines can run synchronously or asynchronously using `BackgroundRunner` and `OrchestrationFacade` in [service/orchestrator.py](file:///home/likelipop/Project/ReadandQues/ReadAndQues/service/orchestrator.py):

- **`BackgroundRunner`**: Clean, lightweight thread daemon runner that dispatches pipelines asynchronously without duplicate code paths.
- **`OrchestrationFacade`**: Thin facade exposing clean methods for views and background workers.

```python
from service.orchestrator import OrchestrationFacade

# Run full single article pipeline synchronously
result = OrchestrationFacade.execute_article_task(article_id="art_123", url="https://example.com/article")

# Run AI generation in background thread
OrchestrationFacade.run_ai_only_pipeline_async(article_id="art_123")
```

---

## 4. Domain Job Packages

Pipeline jobs are atomic, single-responsibility steps inside [service/orchestration/jobs/](file:///home/likelipop/Project/ReadandQues/ReadAndQues/service/orchestration/jobs/):

- **`ingestion.py`**: Web scraping via `service/crawler`, raw HTML parsing, and MinIO Bronze object persistence (`ingest_single_to_bronze`).
- **`processing.py`**: Text cleaning, validation, paragraph segmentation, and MinIO Silver persistence (`fetch_single_silver`).
- **`enrichment.py`**: Core AI processing via LangGraph. Persists results to MinIO Gold, MongoDB Exams, and ChromaDB Vectors.
- **`paraphrase.py`**: Interfaces with the versioned AI tool for Smart Ink paraphrasing of highlights.
- **`maintenance.py`**: Index initialization and cache refresh jobs.

Each job function uses `@job(name="...", inputs=[...], outputs=[...])` and defines explicit parameters. Atomic jobs are composed into pipelines in `pipes.py` (`single_article_pipe`, `ai_only_pipe`, `smart_ink_pipe`).
