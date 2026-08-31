# System Architecture Overview

ReadAndQues is built as a modular, decoupled pair-programming-friendly system with clear separation of concerns.

---

## 1. Architectural Tiers

### A. Shared Contract Layer (`shared/`)
* **Purpose**: Single source of truth for cross-boundary data models and enums.
* **Tech**: Pure Python standard library dataclasses (`Article`, `Exam`, `Question`) and enums (`Stage`, `Status`, `AgentIntent`).
* **Rule**: Zero heavy external dependencies (no Pydantic, no Django, no LangChain).

### B. Data Engineering Pipeline (`NewsPipeline/`)
* **Purpose**: Automated ingestion of daily world news via RSS feeds and Trafilatura extraction.
* **Tech**: Dagster 1.13 (`dg`), Feedparser, Trafilatura, MinIO, PyMongo.
* **Medallion Flow**:
  1. `bronze_article_links`: Parses RSS feeds, filters for freshness (7 days), deduplicates.
  2. `silver_html_documents`: Crawls raw HTML using Trafilatura, extracts clean text, stores raw snapshot in MinIO.
  3. `gold_articles`: Enriches text with AI quizzes and dynamic keywords, upserts to MongoDB `gold_articles`, and triggers vector/BM25 indexing.

### C. AI Engine (`ai_service/`)
* **Purpose**: Encapsulated intelligence platform for question generation, contextual explanations, and multi-agent RAG.
* **Tech**: LangChain, LangGraph, Azure OpenAI, ChromaDB, Rank-BM25, Sentence-Transformers.
* **Boundary**: External callers interact exclusively through [`ai_service/interface.py`](file:///home/likelipop/Project/ReadandQues/ai_service/interface.py).

### D. Web Backend & API (`ReadAndQues/`)
* **Purpose**: User authentication, reading session tracking, and REST endpoints for the client application.
* **Tech**: Django 5.x, Django Ninja, PostgreSQL, PyMongo.
* **Pattern**: Separation into pure read operations ([`selectors.py`](file:///home/likelipop/Project/ReadandQues/ReadAndQues/service/selectors.py)) and transactional mutations ([`services.py`](file:///home/likelipop/Project/ReadandQues/ReadAndQues/service/services.py)).

### E. User Interface (`frontend/`)
* **Purpose**: Split-screen reading and quiz practice environment.
* **Tech**: React 18, TypeScript, Tailwind CSS, Vite.

---

## 2. Key Design Decisions

1. **Dynamic Keywords over Rigid Enums**: Categorical fields (`theme`/`genre`) are replaced with `keywords: list[str]`, enabling flexible discovery and open tagging.
2. **Zero Framework Leakage in AI Layer**: Django never imports LangChain or ChromaDB directly; all AI tasks flow through `ai_service.interface`.
3. **Dedicated Data Pipeline**: Dagster handles batch extraction, scheduling, and asset lineage independently from web requests.
4. **Lightweight Web Tasks**: Background tasks in Django use Python daemon threads without Celery or Redis complexity.
