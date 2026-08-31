# Component Guide: Web Applications & REST API

This document details the Django backend architecture and React frontend interface.

---

## 1. Django Backend Architecture

The backend in [`ReadAndQues/`](file:///home/likelipop/Project/ReadandQues/ReadAndQues/) follows a clean Selectors and Services pattern:

```
                  ┌──────────────────────┐
                  │ Django Ninja Router  │
                  └──────────┬───────────┘
                             │
              ┌──────────────┴──────────────┐
              ▼                             ▼
    ┌──────────────────┐          ┌──────────────────┐
    │  selectors.py    │          │   services.py    │
    │  (Pure Reads)    │          │  (Mutations)     │
    └─────────┬────────┘          └─────────┬────────┘
              │                             │
              ▼                             ▼
    PostgreSQL / MongoDB          MongoDB / ai_service
```

### A. Selectors ([`service/selectors.py`](file:///home/likelipop/Project/ReadandQues/ReadAndQues/service/selectors.py))
Pure read queries with zero side effects:
* `list_completed_articles(keyword, date_filter, page, limit)`: Paginated article list with dynamic keyword filtering.
* `get_article_detail(article_id)`: Fetches clean text, keywords, and exam data.
* `get_popular_keywords(limit)`: Aggregates top trending topic tags across all articles.
* `get_hot_news(limit)` / `get_recommendations(user)`: Homepage spotlight articles.

### B. Services ([`service/services.py`](file:///home/likelipop/Project/ReadandQues/ReadAndQues/service/services.py))
Transactional business mutations:
* `import_article(url, user_id)`: Registers a URL and triggers background ingestion.
* `submit_exam_attempt(user_id, article_id, answers, time_spent)`: Records test scores in PostgreSQL `ExamAttemptLog` and increments user stars.
* `save_user_highlights(user_id, article_id, highlights)`: Persists interactive text markers.
* `ask_rag_question(question, article_id)`: Queries RAG agent via `ai_service.interface`.

---

## 2. REST API Endpoints (Django Ninja)

Interactive OpenAPI documentation is hosted at `/api/docs`.

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/homepage/` | Homepage bundle (hero news, daily vocab, recommendations, popular keywords). |
| `GET` | `/api/articles/` | Article catalog with `keyword`, `date_filter`, `q`, `page`, `limit` params. |
| `GET` | `/api/articles/{article_id}/` | Article reading content, quizzes, and related articles. |
| `POST` | `/api/articles/import/` | Import external URL for reading and quiz generation. |
| `POST` | `/api/exams/{article_id}/submit/` | Submit quiz answers and receive score evaluation. |
| `POST` | `/api/rag/ask/` | Ask questions to the AI assistant grounded in article context. |
| `POST` | `/api/explain/` | Explain a selected word or phrase in context. |

---

## 3. Frontend Architecture

The frontend in [`frontend/`](file:///home/likelipop/Project/ReadandQues/frontend/) is a modern React SPA:
* **`features/reading/`**: Split-screen reading view, paragraph highlighter, vocabulary popover, interactive question panel.
* **`features/discovery/`**: Homepage carousel, dynamic keyword filter chips, search modal.
* **`features/chat/`**: Grounded AI assistant drawer with citation links.
