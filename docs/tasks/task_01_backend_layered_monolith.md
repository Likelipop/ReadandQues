# 📋 Task 01: Backend Layered Monolith & Architecture Clean-up

> **Git Branch**: `feature/01-backend-layered-monolith`

## 🎯 Goal
Eliminate architectural smells in `ReadAndQues/service/` by converting it into a clean, layered monolith. Flatten redundant repos and orchestration frameworks into plain services, selectors, and infrastructure adapters.

---

## 🛠 Detailed Technical Changes

### 1. Data Access Consolidation (`service/infrastructure/`)
- Delete top-level `/database/` package. Move contents into `service/infrastructure/`:
  - `service/infrastructure/mongo/` (`article_store.py`, `exam_store.py`, `activity_store.py`, `pipeline_store.py`, `connection.py`)
  - `service/infrastructure/minio/` (`object_store.py`, `connection.py`)
  - `service/infrastructure/chroma/` (`vector_store.py`, `connection.py`, `chunking.py`)
  - `service/infrastructure/bm25/` (`index.py`, `text_processing.py`, `connection.py`)
  - `service/infrastructure/utils.py` (Move `@db_safe` decorator here)
- Delete `service/repositories/` entirely (7 files).

### 2. Business Logic Layer (`service/services.py` & `service/selectors.py`)
- Create `service/services.py` (ALL write operations & mutations):
  - `import_article(url, user_id)`
  - `trigger_quiz_generation(article_id)`
  - `submit_exam_attempt(user_id, article_id, score, answers, ...)`
  - `run_daily_ingestion(max_articles)`
  - `ask_rag_question(question, article_id)`
  - `smart_paraphrase(article_id, paragraph_text)`
  - `save_user_highlights(user_id, article_id, highlights)`
- Create `service/selectors.py` (ALL read operations):
  - `get_article_detail(article_id)`
  - `get_article_status(article_id)`
  - `list_completed_articles(theme, genre, page, limit)`
  - `get_hot_news(limit)`
  - `get_related_articles(article_id, limit)`
  - `get_user_attempted_ids(user_id)`
  - `get_daily_vocab()`
  - `get_theme_choices()` & `get_genre_choices()` (Single source of truth)

### 3. Simplified ETL Pipeline (`service/pipelines.py` & `service/tasks.py`)
- Delete `service/orchestration/` (13 framework files) and `service/orchestrator.py`.
- Create `service/pipelines.py` with plain ETL functions:
  - `ingest_and_enrich_article(article_id, url)`: crawl $\rightarrow$ clean $\rightarrow$ silver $\rightarrow$ AI $\rightarrow$ gold.
  - `enrich_article_only(article_id)`: re-run AI on existing silver.
  - `run_daily_batch(max_articles)`: RSS crawl & batch process.
- Create `service/tasks.py`:
  - `run_in_background(func, *args, **kwargs)` thread launcher.

### 4. Domain Layer Normalization (`service/domain/`)
- `service/domain/enums.py`: Centralize `ThemeCategory`, `Genre`, `ArticleStage`, `AIStatus`, `AgentIntent`.
- Delete hardcoded theme/genre lists in `readspace/views.py` and `homepage/views.py`.

### 5. Presentation Layer Cleanup (`readspace/` & `homepage/`)
- Remove `readspace/services.py`, `homepage/services.py`, `homepage/context_processors.py`.
- Refactor views to import ONLY `service.services` and `service.selectors`.

---

## ✅ Acceptance Criteria
- [ ] No imports from `database/` exist in the codebase.
- [ ] No `service/repositories/` folder exists.
- [ ] Views only call `service.services` or `service.selectors`.
- [ ] `ThemeCategory` enum in `service/domain/enums.py` is the single source of truth for themes/genres.
- [ ] All tests in `service/tests/` pass with updated imports.
