# API Reference & Endpoints

ReadAndQues provides two API layers:
1. **Django Ninja REST API (`/api/v1/`) 🟢 `[ACTIVE / MODERN]`:** Type-safe, fast, OpenAPI-compliant endpoints consumed by the modern React frontend.
2. **Traditional Django Views 🟡 `[MAINTAINED / LEGACY]`:** Legacy HTML page views and backward-compatibility endpoints.

---

## 1. Django Ninja REST API 🟢 `[ACTIVE / MODERN]`

The primary API router is defined in `readspace/api/router.py` and mounted at `/api/v1/` (and aliased at `/readspace/v1/`).

* **Interactive Swagger UI:** `http://localhost:8000/api/v1/docs`
* **Redoc Documentation:** `http://localhost:8000/api/v1/redoc`

```
Frontend / HTTP Client
          │
          ▼
┌────────────────────────────────────────────────────────┐
│ Django Ninja Router (/api/v1/)                         │
│  - Automated Pydantic Schema Validation                │
│  - Injected Auth: SessionAuth / TokenAuth              │
│  - Auto-generated OpenAPI v3 Specification             │
└───────┬──────────────┬──────────────┬──────────────┬───┘
        ▼              ▼              ▼              ▼
   [/articles]     [/search]       [/exams]       [/user]
```

---

### Endpoints Reference Table

| Method | Route Path | Summary | Auth Required | Description |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/articles/` | List Articles | Optional | Returns paginated gold articles with optional theme/search filters. |
| `GET` | `/articles/{id}` | Article Detail | Optional | Returns full article document including quizzes and metadata. |
| `POST` | `/articles/import` | Import from URL | **Yes** | Charges 1 star and imports an external news article via URL. |
| `GET` | `/search/semantic`| Semantic Search | Optional | Vector similarity search against ChromaDB chunks. |
| `GET` | `/search/hybrid` | Hybrid RAG Search | Optional | Combined Dense Vector + Sparse BM25 with RRF scoring. |
| `POST` | `/exams/submit` | Submit Exam Attempt | **Yes** | Grades user answers, saves attempt log, and updates Topic Proficiency. |
| `GET` | `/exams/history` | Exam History | **Yes** | Returns past exam attempts and scores for the current user. |
| `GET` | `/user/profile` | User Profile | **Yes** | Returns user profile, star balance, streaks, and reading stats. |
| `GET` | `/user/topics` | Topic Proficiencies | **Yes** | Returns accuracy percentages across IELTS reading topics. |
| `POST` | `/dictionary/explain`| Contextual Explainer| Optional | Explains vocabulary or idioms in the context of the active passage. |

---

### Detailed Request & Response Contracts

#### 1. Submit Exam Attempt (`POST /api/v1/exams/submit`)
Submits a student's completed test for server-side evaluation:

**Request Body (`SubmitExamRequestSchema`):**
```json
{
  "article_id": "art_b63f7920e6650b13",
  "answers": {
    "0": "Atmospheric rivers",
    "1": "Yes",
    "2": "record | snowfall | interior"
  },
  "highlighted_markdown": "East Antarctica experienced ==record-breaking snowfall==...",
  "elapsed_time": 420
}
```

**Response Body (`SubmitExamResponseSchema`):**
```json
{
  "attempt_id": "8f3b6c20-7b5a-4b92-8012-9c1b4e2f8901",
  "score": 3,
  "total_questions": 3,
  "accuracy_percentage": 100.0,
  "feedback": [
    {
      "question_idx": 0,
      "is_correct": true,
      "user_answer": "Atmospheric rivers",
      "correct_answer": "Atmospheric rivers",
      "explanation": "Atmospheric rivers carried unprecedented moisture inland.",
      "supporting_text": "Atmospheric rivers contributed over 70% of the anomalous snowfall."
    }
  ],
  "stars_awarded": 2,
  "new_star_balance": 14
}
```

---

#### 2. Hybrid Article Search (`GET /api/v1/search/hybrid?query=...`)

**Query Parameters:**
* `query` (str): Search string (e.g. `climate ice accumulation`).
* `limit` (int, default: 10): Maximum results to return.

**Response Body:**
```json
{
  "query": "climate ice accumulation",
  "results": [
    {
      "article_id": "art_b63f7920e6650b13",
      "title": "Antarctica gained a record 695 billion tons of ice",
      "theme": "Environment",
      "url": "https://www.sciencedaily.com/releases/...",
      "score": 0.0328,
      "sources": ["vector", "bm25"]
    }
  ]
}
```

---

## 2. Traditional Django Views 🟡 `[MAINTAINED / LEGACY]`

Defined in `readspace/views.py` and `readspace/urls.py`, these endpoints serve standard server-rendered HTML pages and legacy API contracts:

### A. HTML Page Views
* `GET /readspace/<id>/`: Renders the main reading workspace HTML template (`readspace.html`) with embedded article content.
* `GET /readspace/all-tests/`: Renders the catalog of all available IELTS reading practice tests.
* `GET /readspace/import/`: Renders the article import form.

### B. Compatibility API Endpoints
* `POST /readspace/api/<id>/save_markers/`:
  * **Legacy Compatibility:** Accepts both modern payload `{"highlighted_text": "..."}` and legacy key `{"highlights": "..."}`.
* `GET /readspace/api/search/keyword/` & `GET /readspace/api/search/semantic/`:
  * Maintained for older client views that query BM25 or ChromaDB separately rather than using the unified `/api/v1/search/hybrid` endpoint.
* `GET /readspace/status/<id>/`:
  * Polling endpoint used by legacy asynchronous crawlers.
