# Architecture Overview & System Design

Welcome to the **ReadAndQues** project codebase! This document provides a developer-first overview of the system architecture, design invariants, data flow, and layer boundaries.

---

## 1. High-Level System Architecture

ReadAndQues is an intelligent reading and examination web application built on Django. It ingests web articles, cleanses and processes them into standardized reading/testing units, generates AI-powered comprehension quizzes and paraphrases, and provides an article-grounded Q&A ticket system.

```
+-------------------------------------------------------------------------------+
|                             WEB PRESENTATION LAYER                            |
|             (Django Views: readspace, homepage, accounts, REST APIs)          |
+---------------------------------------+---------------------------------------+
                                        |
                 +----------------------+----------------------+
                 |                                             |
                 v                                             v
  +-----------------------------+               +-------------------------------+
  |  APPLICATION SERVICES LAYER |               |     ORCHESTRATION FACADE      |
  |  (readspace/services.py,    |               |  (service/orchestrator.py)    |
  |   homepage/services.py)     |               +---------------+---------------+
  +--------------+--------------+                               |
                 |                                              v
                 |                              +-------------------------------+
                 |                              |      TYPED PIPELINE ENGINE    |
                 |                              |  (service/orchestration/)     |
                 |                              +---------------+---------------+
                 |                                              |
                 v                                              v
  +-----------------------------+               +-------------------------------+
  |      REPOSITORIES LAYER     |               |       SHARED AI PLATFORM      |
  | (ArticleRepository,         |               | (ModelGateway, AIToolPolicy,  |
  |  AttemptRepository)         |               |  AIToolRegistry, LangGraph)   |
  +--------------+--------------+               +---------------+---------------+
                 |                                              |
                 +----------------------+-----------------------+
                                        |
                                        v
+-------------------------------------------------------------------------------+
|                                DATASTORE LAYER                                |
|  - PostgreSQL: User Accounts, AIRunLog, ArticleImportRequest, ExamAttemptLog  |
|  - MongoDB: Canonical Articles (gold_articles), Non-SQL Migrations            |
|  - MinIO: Raw Bronze JSON Source Objects + Manifests                          |
|  - ChromaDB: Vector Embeddings for Semantic Search                            |
|  - BM25: In-Memory Lexical Index for Keyword Search                           |
+-------------------------------------------------------------------------------+
```

---

## 2. Layer Boundaries & Invariants

To keep the codebase maintainable, clear layer boundaries are strictly enforced ([ADR-0002](file:///home/likelipop/Project/ReadandQues/docs/refactor/adr/0002-application-orchestration-boundary.md)):

1. **Views (`views.py`)**: Responsible *only* for HTTP handling, request validation, authentication, and response rendering. Views **never** directly invoke raw database drivers or pipeline jobs.
2. **Application Services (`services.py`)**: Encapsulate high-level application use-cases. They call **Repositories** for CRUD operations and the **OrchestrationFacade** for multi-step background workflows.
3. **Orchestration Engine (`service/orchestration/`)**: Executes multi-step batch or background workflows (`ingest_bronze`, `enrich_silver`, `generate_gold`, `daily_pipeline`). Pipeline jobs are domain-grouped and typed.
4. **Shared AI Platform (`service/ai_core/`)**: Standardized runtime for LLM execution via versioned `AITool` contracts, `ModelGateway`, `AIToolPolicy` (timing, caching, token usage), and PostgreSQL `AIRunLog` ledgering.
5. **Repositories (`service/repositories/`)**: Abstract datastore access and return typed Pydantic contracts ([ADR-0001](file:///home/likelipop/Project/ReadandQues/docs/refactor/adr/0001-data-ownership.md)).

---

## 3. Data Flow & Medallion Architecture

ReadAndQues processes raw web content through a **Medallion Data Architecture**:

```
+------------------+        +------------------+        +------------------+
|   BRONZE LAYER   | ---->  |   SILVER LAYER   | ---->  |    GOLD LAYER    |
| (Raw Web Scrapes |        |  (Cleaned Text,  |        | (Canonical Schema|
|  stored in MinIO |        |   Paragraphs,    |        |  stored in Mongo |
|  with SHA256)    |        |   Metadata)      |        |  & Projections)  |
+------------------+        +------------------+        +------------------+
```

- **Bronze**: Raw HTML/JSON payloads scraped from web sources, stored immutably in MinIO with SHA-256 manifest validation.
- **Silver**: Cleansed article text, extracted metadata, and paragraph breakdowns.
- **Gold**: Fully enriched canonical `ArticleContract` document stored in MongoDB `gold_articles` and projected into ChromaDB (vector embeddings) and BM25 (lexical index).

---

## 4. Key Subsystems Overview

| Subsystem | Folder Location | Primary Responsibility |
|---|---|---|
| **Data Layer** | `service/domain/`, `service/repositories/`, `database/` | Pydantic contracts, repositories, datastore lazy connections, non-SQL migrations |
| **Orchestration** | `service/orchestration/`, `service/orchestrator.py` | Typed pipeline engine, domain jobs, background execution facade |
| **AI Platform** | `service/ai_core/platform/`, `service/ai_core/tools/` | ModelGateway, versioned AI tools, policy wrapper, AIRunLog persistence |
| **Grounded Q&A** | `service/ai_core/grounding/`, `service/ai_core/graphs/ask_article/` | Article chunking, scoped retrieval, exact citation verification |
| **Web Apps** | `readspace/`, `homepage/`, `accounts/`, `service/` | Views, services, templates, authentication, REST APIs |

---

## 5. Next Steps for New Developers

To get up to speed with specific subsystems, read the component guides in order:

1. [Datastore & Storage Layer Guide](file:///home/likelipop/Project/ReadandQues/docs/components/01-data-layer.md)
2. [Orchestration Engine Guide](file:///home/likelipop/Project/ReadandQues/docs/components/02-orchestration.md)
3. [AI Platform Guide](file:///home/likelipop/Project/ReadandQues/docs/components/03-ai-platform.md)
4. [Grounded Q&A Subsystem Guide](file:///home/likelipop/Project/ReadandQues/docs/components/04-grounding-qa.md)
5. [Web Application Layer Guide](file:///home/likelipop/Project/ReadandQues/docs/components/05-web-applications.md)
