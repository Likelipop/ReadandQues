# 🧠 BACKEND & AI DEVELOPER TASK BACKLOG & ACTION PLAN

**Project**: ReadAndQues — Interactive Academic Reading & AI Quiz Platform  
**Target Milestone**: Architecture Integrity, AI Model Fallback & Production Hardening  
**Assigned Role / Subagent**: Backend & AI Developer (Django, Python 3.13, LangGraph, ChromaDB, Celery)

---

## 🎯 Objective
Resolve architectural coupling in AI router, eliminate BM25 blocking rebuilds in single-article ingestion, decouple and harmonize domain models with API schemas, fix deprecated datetime calls, and secure email OTP handlers.

---

## 📋 Detailed Task Breakdown

### Task BE-01: Standardize RAG Router with ModelGateway & Fault Tolerance
- **Files**: `ReadAndQues/service/rag/router.py`, `ReadAndQues/service/ai_core/platform/gateway.py`
- **Priority**: High (P1) - Critical Architecture Debt
- **Status**: Ready for Sprint
- **Technical Specifications**:
  1. `service/rag/router.py` currently creates a raw `OpenAI(api_key=api_key)` client inside `classify_intent_node`, bypassing the platform's `ModelGateway` and `ModelRouter` provider fallback hierarchy (Azure OpenAI, OpenAI, Ollama).
  2. Refactor `classify_intent_node` to use `ModelGateway.get_llm(profile_name="precise", temperature=0.0)` with automatic fallback routing.
  3. Ensure structured intent classification works seamlessly across Azure and local Ollama deployments when OpenAI API key is not present.

### Task BE-02: Optimize BM25 Index Rebuilding & Asynchronous Celery Dispatch
- **Files**: `ReadAndQues/service/pipelines.py`, `ReadAndQues/service/tasks.py`
- **Priority**: High (P1) - Critical Performance
- **Status**: Ready for Sprint
- **Technical Specifications**:
  1. In `service/pipelines.py` (lines 142 & 193), `bm25_conn.rebuild_index()` is invoked synchronously inside `ingest_and_enrich_article` and `enrich_article_only`.
  2. During batch crawling or multiple user imports, this causes $ full index rebuilds in-memory, degrading worker performance.
  3. Change the pipeline to dispatch `task_rebuild_bm25_index.delay()` asynchronously via Celery with a debounce mechanism or perform incremental updates.

### Task BE-03: Resolve Legacy & Outdated Module Imports
- **Files**: 
  - `ReadAndQues/service/migrations_nonsql/runner.py`
  - `scripts/batch_index_news.py`
  - `scripts/refactor_quality_gate.py`
  - `scripts/test_live_docker_stack.py`
- **Priority**: High (P1) - CI/CD Blocker
- **Status**: Ready for Sprint
- **Technical Specifications**:
  1. `service/migrations_nonsql/runner.py`: Fix import `from database.Mongo.connection import get_mongo_db` -> `from service.infrastructure.mongo.connection import get_mongo_db`.
  2. `scripts/batch_index_news.py`: Update legacy imports to `service.infrastructure.mongo.article_store` and `service.infrastructure.chroma.vector_store`.
  3. `scripts/refactor_quality_gate.py`: Update `import service.orchestrator` smoke test to `import service.pipelines` and `import service.services`.
  4. `scripts/test_live_docker_stack.py`: Align imports with `service.services` and `service.selectors`.

### Task BE-04: Secure OTP Verification & Eliminate Console Print Statements
- **File**: `ReadAndQues/accounts/emails.py`
- **Priority**: High (P1) - Security Finding
- **Status**: Ready for Sprint
- **Technical Specifications**:
  1. Replace raw `print()` statements in `send_verification_email` with structured Python logging.
  2. Ensure 6-digit OTP codes are masked in production logs to prevent OTP theft via container log aggregation.
  3. Add rate limiting on OTP verification attempts per IP/Session to prevent brute-force attacks.

### Task BE-05: Fix Python 3.12+ Deprecations (Ruff & UTC)
- **Files**:
  - `ReadAndQues/service/selectors.py`
  - `ReadAndQues/service/ai_core/graphs/question_generator/graph.py`
  - `ReadAndQues/service/tests/*.py`
- **Priority**: Medium (P2)
- **Status**: Ready for Sprint
- **Technical Specifications**:
  1. Replace `datetime.datetime.utcnow()` and `datetime.datetime.now(datetime.timezone.utc)` with standard `datetime.datetime.now(datetime.UTC)`.
  2. Run `ruff check --fix .` and sort import blocks using `isort` rules.

---

## 🧪 Acceptance Criteria & Test Validation
- [ ] `pytest` passes all 139 test cases with 0 warnings.
- [ ] `python scripts/refactor_quality_gate.py --full` exits with code 0 (PASS).
- [ ] `ruff check .` returns 0 linting errors.
