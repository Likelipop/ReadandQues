# ReadAndQues Developer Documentation Portal

Welcome to the **ReadAndQues** developer documentation portal. This documentation hub is designed to give new and existing developers a clear, structured understanding of the codebase architecture, design patterns, datastores, AI platform, and operational workflows.

---

## 🚀 Quick Start for New Developers

### 1. Environment Setup
Ensure Python 3.13 and `uv` package manager are installed:
```bash
# Synchronize frozen virtual environment dependencies
uv sync --frozen

# Activate virtual environment
source .venv/bin/activate
```

### 2. Database Migrations
Apply PostgreSQL relational migrations and non-SQL versioned migrations (MongoDB, MinIO, ChromaDB):
```bash
# Relational DB migrations
python ReadAndQues/manage.py migrate

# Non-SQL versioned migrations (MongoDB indexes & validators)
python ReadAndQues/manage.py migrate_non_sql
```

### 3. Run Quality Gate & Unit Tests
Before committing changes, execute the full quality gate check:
```bash
# Run full quality gate (Python syntax, unit tests, Django checks, migration drift, smoke tests)
.venv/bin/python scripts/refactor_quality_gate.py --full

# Run unit tests only
make test-unit
```

### 4. Start Development Server
```bash
python ReadAndQues/manage.py runserver 8000
```

---

## 🗺️ Documentation Sitemap & Reading Order

For developers joining the project, we recommend reading the documentation in this order:

```
                  [ 1. System Architecture Overview ]
                   docs/architecture/01-overview.md
                                  |
         +------------------------+------------------------+
         |                        |                        |
         v                        v                        v
[ 2. Data Layer ]        [ 3. Orchestration ]      [ 4. AI Platform ]
docs/components/         docs/components/          docs/components/
  01-data-layer.md         02-orchestration.md       03-ai-platform.md
         |                        |                        |
         +------------------------+------------------------+
                                  |
                 +----------------+----------------+
                 |                                 |
                 v                                 v
   [ 5. Grounded Q&A Ticket ]         [ 6. Web Applications ]
    docs/components/                   docs/components/
      04-grounding-qa.md                 05-web-applications.md
```

### Core Architecture & Components

1. 🏗️ **[System Architecture Overview](file:///home/likelipop/Project/ReadandQues/docs/architecture/01-overview.md)**
   High-level system design, layer boundaries (View -> Service -> Repository / Facade -> Datastores), Medallion Architecture (Bronze -> Silver -> Gold), and subsystem layout.

2. 🗄️ **[Datastore & Storage Layer](file:///home/likelipop/Project/ReadandQues/docs/components/01-data-layer.md)**
   Datastore single-source-of-truth ownership (PostgreSQL, MongoDB, MinIO, ChromaDB, BM25), Pydantic v2 data contracts, lazy connection proxies, non-SQL migration runner, and repositories.

3. ⚡ **[Orchestration Engine & Pipelines](file:///home/likelipop/Project/ReadandQues/docs/components/02-orchestration.md)**
   Typed pipeline execution (`PipelineContext`, `JobResult`), exception hierarchy, background executors, domain job modules, and `OrchestrationFacade`.

4. 🤖 **[Shared AI Platform & LangGraph](file:///home/likelipop/Project/ReadandQues/docs/components/03-ai-platform.md)**
   `ModelGateway` & model profiles, versioned `AITool` contracts, `AIToolRegistry`, `AIToolPolicy` (timing, caching, token usage), PostgreSQL `AIRunLog` ledgering, and LangGraph graphs.

5. 🔍 **[Grounded Q&A Ticket Subsystem](file:///home/likelipop/Project/ReadandQues/docs/components/04-grounding-qa.md)**
   Stable `ArticleChunk` offset chunking with SHA-256 hashes, article-scoped lexical retrieval, exact quote citation verification, and `ask_article` workflow.

6. 🌐 **[Web Application & Presentation Layer](file:///home/likelipop/Project/ReadandQues/docs/components/05-web-applications.md)**
   Django modular apps (`readspace`, `homepage`, `accounts`, `service`), View-Service decoupling, REST APIs, user star charges, and UI styling principles.

---

## 📜 Architectural Decision Records (ADRs) & Operations

- 🏛️ **[ADR-0001: Datastore Ownership & Consistency](file:///home/likelipop/Project/ReadandQues/docs/refactor/adr/0001-data-ownership.md)**
- 🏛️ **[ADR-0002: Application & Orchestration Boundary](file:///home/likelipop/Project/ReadandQues/docs/refactor/adr/0002-application-orchestration-boundary.md)**
- 🏛️ **[ADR-0003: Shared AI-Tool Platform](file:///home/likelipop/Project/ReadandQues/docs/refactor/adr/0003-ai-tool-platform.md)**
- 🔧 **[Operations & Recovery Guide](file:///home/likelipop/Project/ReadandQues/docs/refactor/OPERATIONS.md)**
- 📋 **[Master Plan Refactor Roadmap](file:///home/likelipop/Project/ReadandQues/docs/refactor/MASTER_PLAN.md)**
- 📊 **[Refactor Status Ledger](file:///home/likelipop/Project/ReadandQues/docs/refactor/STATUS.md)**

---

## 📦 Documentation Archives

Historical task documents, bug notes, and developer logs are preserved for reference in **[docs/archive/](file:///home/likelipop/Project/ReadandQues/docs/archive/)**.
