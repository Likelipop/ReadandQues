# 🚀 DEVOPS & INFRASTRUCTURE ENGINEER TASK BACKLOG & ACTION PLAN

**Project**: ReadAndQues — Interactive Academic Reading & AI Quiz Platform  
**Target Milestone**: Production Docker Stack Hardening, CI/CD Quality Gates & Monitoring  
**Assigned Role / Subagent**: DevOps Engineer (Docker Compose, Nginx, Gunicorn, Celery, GitHub Actions)

---

## 🎯 Objective
Harden multi-container Docker Compose infrastructure, configure production-grade Nginx reverse proxy with rate limiting and SSE streaming support, fix CI quality gate scripts, and implement healthcheck monitoring.

---

## 📋 Detailed Task Breakdown

### Task OPS-01: Fix CI Quality Gate Script & Smoke Tests
- **File**: `scripts/refactor_quality_gate.py`
- **Priority**: High (P1) - CI Blocker
- **Status**: Ready for Sprint
- **Technical Specifications**:
  1. Line 108 currently runs `[sys.executable, "-c", "import service.orchestrator"]`.
  2. Replace with `[sys.executable, "-c", "import service.pipelines; import service.services"]`.
  3. Ensure `python scripts/refactor_quality_gate.py --full` passes cleanly in CI workflows without infrastructure dependencies.

### Task OPS-02: Configure Nginx Reverse Proxy for Server-Sent Events (SSE)
- **File**: `nginx/default.conf`
- **Priority**: High (P1)
- **Status**: Ready for Sprint
- **Technical Specifications**:
  1. SSE endpoints (`/api/v1/api/rag/stream/` and `/api/v1/api/explain/stream/`) require specific Nginx configuration to prevent response buffering:
     ```nginx
     location ~* ^/(api/v1/api/rag/stream|api/v1/api/explain/stream)/ {
         proxy_pass http://web:8000;
         proxy_http_version 1.1;
         proxy_set_header Connection '';
         proxy_set_header Host $host;
         proxy_buffering off;
         proxy_cache off;
         chunked_transfer_encoding on;
         proxy_read_timeout 600s;
     }
     ```
  2. Configure gzip compression for static CSS/JS while ensuring gzip is bypassed on SSE streams.

### Task OPS-03: Docker Compose Resource Limits & Production Healthchecks
- **File**: `docker-compose.yaml`
- **Priority**: High (P1)
- **Status**: Ready for Sprint
- **Technical Specifications**:
  1. Add memory and CPU reservations/limits for resource-intensive services (Mongo, ChromaDB, Celery worker).
  2. Update Gunicorn worker configuration in `gunicorn.conf.py` for optimal worker concurrency:
     - Worker class: `sync` or `gthread` (4 workers x 2 threads = 8 concurrent request slots).
  3. Add container healthcheck dependencies to ensure Web and Celery services start strictly after Postgres, Mongo, Redis, MinIO, and ChromaDB are healthy.

### Task OPS-04: Production Secret Management & Environment Security
- **Files**: `.env.example`, `ReadAndQues/settings/prod.py`
- **Priority**: High (P1) - Security Finding
- **Status**: Ready for Sprint
- **Technical Specifications**:
  1. Enforce strict failure in `settings/prod.py` if `SECRET_KEY` or database passwords match default insecure strings.
  2. Add environment variables for `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `OPENAI_API_KEY`, `RESEND_API_KEY`, and `CORS_ALLOWED_ORIGINS`.
  3. Ensure `DEBUG=False` in production settings and configure `ALLOWED_HOSTS` dynamically.

### Task OPS-05: Automated GitHub Actions CI/CD Pipeline
- **File**: `.github/workflows/ci.yaml` (NEW)
- **Priority**: Medium (P2)
- **Status**: Backlog
- **Technical Specifications**:
  1. Create automated GitHub Actions workflow running on pull requests:
     - Python syntax check & Ruff linting (`ruff check .`).
     - Backend isolated characterization tests (`python scripts/refactor_quality_gate.py`).
     - Full Pytest test suite with locked dependencies.
     - Frontend TypeScript check (`tsc --noEmit`) and Vitest test suite (`npm test`).

---

## 🧪 Acceptance Criteria & Test Validation
- [ ] `docker-compose up --build` starts all 8 services cleanly with healthy status.
- [ ] SSE streams flow without proxy buffering delays through Nginx port 8080.
- [ ] CI quality gate runs in under 60 seconds with 100% pass rate.
