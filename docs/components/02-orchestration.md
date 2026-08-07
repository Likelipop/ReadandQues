# Component Guide: Orchestration Engine & Pipelines

This document describes the typed pipeline orchestration engine, job domain modules, background executors, and `OrchestrationFacade`.

---

## 1. Boundary & Responsibilities

The Orchestration Engine in [service/orchestration/](file:///home/likelipop/Project/ReadandQues/ReadAndQues/service/orchestration/) manages multi-step batch processing and background pipelines ([ADR-0002](file:///home/likelipop/Project/ReadandQues/docs/refactor/adr/0002-application-orchestration-boundary.md)):

- Single-step query operations (e.g., fetching an article by ID) use direct repository calls and do **not** use pipelines.
- Multi-step workflows (e.g., scrape web page -> extract text -> save Bronze -> enrich Silver -> generate Gold -> trigger AI quiz -> build vector index) run through typed orchestration `Pipe`s.

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

## 3. Executors & Background Execution

Pipelines can run synchronously or asynchronously using executors in [service/orchestration/executors.py](file:///home/likelipop/Project/ReadandQues/ReadAndQues/service/orchestration/executors.py):

- **`InlineExecutor`**: Executes pipeline jobs sequentially in the caller's thread (useful for synchronous request flows and unit testing).
- **`ThreadedBackgroundExecutor`**: Submits pipeline execution to a background daemon thread pool, returning immediately while jobs complete asynchronously.

---

## 4. Domain Job Packages

Pipeline jobs are grouped by domain responsibility inside [service/orchestration/jobs/](file:///home/likelipop/Project/ReadandQues/ReadAndQues/service/orchestration/jobs/):

- **`ingestion_jobs.py`**: Web scraping, raw HTML parsing, and MinIO Bronze object persistence.
- **`article_jobs.py`**: Text cleaning, paragraph segmentation, and MongoDB canonical Gold article saving.
- **`ai_jobs.py`**: Interfacing with versioned AI tools (`smart_paraphrase`, `quiz_generator`, `batch_paraphrase`).
- **`search_jobs.py`**: Updating ChromaDB vector embeddings and BM25 lexical search indices.
- **`maintenance_jobs.py`**: Data auditing and projection reindexing jobs.

Each job function uses `@register_job(name="...")` and defines explicit input parameters.

---

## 5. Orchestration Facade

Application services and Django views invoke pipelines exclusively through `OrchestrationFacade` in [service/orchestrator.py](file:///home/likelipop/Project/ReadandQues/ReadAndQues/service/orchestrator.py):

```python
from service.orchestrator import OrchestrationFacade

facade = OrchestrationFacade()

# Run full single article ingestion synchronously
result = facade.run_single_article_pipeline(url="https://example.com/article")

# Run AI generation in background thread
thread_id = facade.run_ai_only_pipeline_async(article_id="art_123")

# Run daily batch pipeline with truthful stage failure reporting
daily_res = facade.run_daily_pipeline()
```
