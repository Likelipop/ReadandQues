# Component Guide: Data Layer & Persistence

This document details the polyglot persistence architecture, datastore ownership rules, and shared schemas.

---

## 1. Datastore Responsibilities

| Datastore | Primary Role | Collections / Tables |
|---|---|---|
| **PostgreSQL 15** | Relational user accounts, authentication, activity ledgers, and topic proficiency. | `auth_user`, `accounts_userprofile`, `service_examattemptlog`, `service_topicproficiency` |
| **MongoDB 7** | Document storage for crawled articles, enriched gold articles, and generated quizzes. | `article_index`, `gold_articles`, `exams`, `reading_history`, `user_highlights` |
| **MinIO (S3)** | Object store for raw crawled HTML snapshots (Silver layer cache). | `silver-clean`, `raw-html` |
| **ChromaDB** | Vector database for article and paragraph semantic search. | `articles`, `news_chunks` |
| **BM25 Index** | Lexical keyword index using Okapi BM25 and spaCy tokenization. | In-memory with periodic disk persistence |

---

## 2. Shared Domain Models (`shared/`)

All cross-service boundaries use pure Python dataclasses defined in [`shared/schemas.py`](file:///home/likelipop/Project/ReadandQues/shared/schemas.py):

* **`Article`**:
  * `article_id: str` (deterministic hash via `generate_article_id(url)`)
  * `url: str`
  * `title: str`
  * `source_name: str`
  * `original_text: str`
  * `word_count: int`
  * `keywords: list[str]` (dynamic list of topic tags, e.g., `["AI", "Healthcare", "Robotics"]`)
  * `summary: str`
  * `exams: list[Exam]`
  * `created_at: datetime`

* **`Question`**:
  * `type: str` (`multiple_choice`, `yes_no_notgiven`, `fill_in_blank`)
  * `question: str`
  * `options: list[str]`
  * `correct_answer: str`
  * `explanation: str`
  * `supporting_quote: str`

* **`Exam`**:
  * `exam_id: str`
  * `title: str`
  * `questions: list[Question]`

---

## 3. Database Initialization

Run database setup to create necessary indexes idempotently:
```bash
python manage.py setup_db
```
This configures unique indexes on `url` and `article_id`, as well as multikey indexes on `keywords`.
