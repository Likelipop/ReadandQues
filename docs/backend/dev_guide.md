# Backend Developer Handbook & Runbook

This guide contains step-by-step instructions for developers running, configuring, testing, and debugging the **Django Backend** (`ReadAndQues/`).

---

## 1. Quick Service Port & Connection Reference

| Service / Component | Host URL / Port | Container Host / Port | Credentials / Notes |
| :--- | :--- | :--- | :--- |
| **Django Backend** | `http://localhost:8000` | `backend:8000` | Default dev server |
| **Django Ninja Swagger** | `http://localhost:8000/api/v1/docs` | `backend:8000/api/v1/docs` | Interactive OpenAPI documentation |
| **PostgreSQL Database** | `localhost:5432` | `db:5432` | User: `postgres` / Pass: `postgres` (or SQLite `db.sqlite3`) |
| **MongoDB Database** | `localhost:27017` | `mongo:27017` | User: `admin` / Pass: `changeme` / DB: `articlesDB` |
| **MinIO S3 Storage** | `http://localhost:9000` | `minio:9000` | Console: `http://localhost:9001` (`minioadmin`/`minioadmin`) |
| **ChromaDB Vector Store** | `http://localhost:8002` | `chromadb:8000` | Internal path: `/data` |

---

## 2. Environment Configuration (`.env`)

Ensure a `.env` file exists in the repository root or within `ReadAndQues/`:

```bash
# ── Django Core Settings ──────────────────────────────────────────────────────
SECRET_KEY="django-insecure-development-secret-key-change-in-production"
DEBUG=True
ALLOWED_HOSTS="localhost,127.0.0.1,0.0.0.0"

# ── Relational Database (PostgreSQL / SQLite fallback) ────────────────────────
DATABASE_URL="postgres://postgres:postgres@localhost:5432/readandques"
# If DATABASE_URL is unset, Django automatically falls back to local SQLite (db.sqlite3)

# ── Document & Object Storage ────────────────────────────────────────────────
MONGO_URI="mongodb://admin:changeme@localhost:27017/articlesDB?authSource=admin"
MONGO_DB_NAME="articlesDB"
MINIO_ENDPOINT="localhost:9000"
MINIO_ACCESS_KEY="minioadmin"
MINIO_SECRET_KEY="minioadmin"

# ── Vector Store ─────────────────────────────────────────────────────────────
CHROMA_HOST="localhost"
CHROMA_PORT=8002

# ── AI Service (Azure OpenAI) ────────────────────────────────────────────────
AZURE_OPENAI_API_KEY="your-azure-api-key"
AZURE_OPENAI_ENDPOINT="https://your-resource.services.ai.azure.com"
AZURE_DEPLOYMENT_NAME="gpt-5-mini"
AZURE_OPENAI_API_VERSION="2024-02-01"

# ── Email Service (Resend) ───────────────────────────────────────────────────
RESEND_API_KEY="re_123456789" # If unset, OTP codes are logged to the console
```

---

## 3. Local Development Runbook

### A. Initial Setup
From the repository root:

```bash
# 1. Install dependencies via uv
uv sync

# 2. Apply database migrations to PostgreSQL / SQLite
uv run python ReadAndQues/manage.py migrate

# 3. (Optional) Run initial database setup / seed command
uv run python ReadAndQues/manage.py setup_db

# 4. Create an administrator superuser
uv run python ReadAndQues/manage.py createsuperuser
```

---

### B. Starting the Development Server
```bash
# Launch Django dev server on port 8000
uv run python ReadAndQues/manage.py runserver 0.0.0.0:8000
```
Visit **`http://localhost:8000/`** to view the homepage, or **`http://localhost:8000/api/v1/docs`** to explore the interactive Swagger documentation.

---

### C. Running Unit & Integration Tests
```bash
# 1. Run all backend tests
uv run pytest ReadAndQues/

# 2. Run API contract tests (validates Pydantic & legacy payload compatibility)
uv run pytest ReadAndQues/readspace/tests/test_api_contracts.py

# 3. Run accounts authentication tests
uv run pytest ReadAndQues/accounts/tests/
```

---

## 4. Troubleshooting & Operational Guide

| Symptom / Error | Root Cause | Solution |
| :--- | :--- | :--- |
| **CSRF verification failed (403 Forbidden)** | Request sent without `X-CSRFToken` header or `csrftoken` cookie | Ensure frontend fetches CSRF cookie or includes `X-CSRFToken` header for non-GET requests. |
| **`InsufficientStarsError` on Article Import** | User has 0 stars in `UserProfile` | In development, set `DEBUG=True` to receive 100 default stars upon registration, or update `stars` directly via Django admin (`/admin/`). |
| **`No module named 'ai_service'`** | Project root directory is not in `PYTHONPATH` | Run commands using `uv run python ReadAndQues/manage.py ...` or ensure the project root is in your virtualenv. |
| **Tokens not streaming (buffered burst)** | Nginx or browser buffering the SSE stream | Verify the endpoint sets `X-Accel-Buffering: no` and ensure Nginx proxy buffering is disabled (`proxy_buffering off;`). |
| **`User.profile.RelatedObjectDoesNotExist`** | Legacy user record created before the `post_save` signal was added | Signal handles fallback automatically. For existing users, run: `UserProfile.objects.get_or_create(user=user)`. |
| **MongoDB connection timeout** | MongoDB container is stopped or port is mapped incorrectly | Ensure Docker container `mongo` is running and accessible on port `27017`. |
