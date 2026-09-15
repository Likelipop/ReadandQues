# Service Layer & Business Logic Architecture

The **Service Layer** (`ReadAndQues/service/`) implements the **Services & Selectors Pattern** (Domain-Driven Design). It decouples business workflows, gamification transactions, and database operations from Django views and HTTP controllers.

---

## 1. Architectural Philosophy: Services vs. Selectors

In traditional Django applications, business logic often gets smeared across fat models or bloated views. ReadAndQues enforces a strict two-way split:

```
┌────────────────────────────────────────────────────────┐
│                   HTTP / API Controllers               │
│          (Django Views, Django Ninja Routers, CLI)     │
└───────────────────┬────────────────┬───────────────────┘
                    │                │
        Mutations & │                │ Read Queries
        State Write │                │ & Aggregations
                    ▼                ▼
┌─────────────────────────┐   ┌──────────────────────────┐
│   service/services.py   │   │   service/selectors.py   │
│  - Atomic Transactions  │   │  - Pure Read Functions   │
│  - Star Deductions      │   │  - Query Optimizations   │
│  - Exam Grading Engine  │   │  - Cache Lookups         │
└───────────┬─────────────┘   └────────────┬─────────────┘
            │                              │
            ▼                              ▼
┌────────────────────────────────────────────────────────┐
│           Infrastructure & Storage Adapters            │
│   (PostgreSQL ORM, MongoDB Store, MinIO, ChromaDB)     │
└────────────────────────────────────────────────────────┘
```

### Benefits:
* **Thin Controllers:** Views only handle request deserialization, status codes, and HTTP responses.
* **Testability:** Core business logic can be unit-tested without instantiating HTTP request factories or mocking headers.
* **Multi-Channel Reuse:** The same service functions can be invoked from Django Ninja REST APIs, Celery background workers, or management commands.

---

## 2. Core Business Workflows (`service/services.py`)

### A. Star Economy & Atomic Deductions
The platform uses **Stars** as a gamified virtual currency. Importing a custom article via URL costs **1 star**.

To eliminate race conditions (e.g. user spamming the import button with only 1 star remaining), deductions use Django's `@transaction.atomic` and select-for-update locking:

```python
@transaction.atomic
def charge_and_create_import_request(user_id: int, url: str, stars_cost: int = 1) -> ArticleImportRequest:
    # 1. Lock user profile row in PostgreSQL
    profile = UserProfile.objects.select_for_update().get(user_id=user_id)
    
    # 2. Verify star balance
    if profile.stars < stars_cost:
        raise InsufficientStarsError(f"User requires {stars_cost} star(s), but has {profile.stars}.")
        
    # 3. Deduct star and log transactional request
    profile.stars -= stars_cost
    profile.total_articles_imported += 1
    profile.save(update_fields=["stars", "total_articles_imported"])
    
    import_req = ArticleImportRequest.objects.create(
        user_id=user_id,
        url=url,
        status="pending",
        stars_charged=stars_cost
    )
    return import_req
```

---

### B. Exam Grading & Scoring Engine
When a student finishes an IELTS practice test, `evaluate_exam_submission()` evaluates the submission:

1. **Answer Evaluation:**
   * **Multiple Choice & Yes/No/Not Given:** Direct case-insensitive string equality against `quiz.correct_answer`.
   * **Summary Completion (`fill_in_blank`):** The student's pipe-delimited answers (`word1 | word2 | ...`) are split and compared position-by-position against the correct answers list.
2. **Attempt Logging:** Creates an `ExamAttemptLog` in PostgreSQL, storing score, elapsed time, user answers, and highlight states.
3. **Star Rewards Calculation:**
   * Score $\ge 70\%$: Awards **+1 star**.
   * Perfect Score ($100\%$): Awards **+2 stars**.
4. **Topic Proficiency Update:**
   Updates the user's `TopicProficiency` record for the article's theme (e.g., Environment, Science):
   $$\text{Accuracy} = \frac{\text{Previous Correct} + \text{New Correct}}{\text{Previous Total} + \text{New Total}}$$

---

### C. Persistent Article Highlighting (`save_article_markers`)
Allows students to highlight and annotate article text during reading:
* Accepts the Markdown text embedded with `==highlighted text==` tags.
* Saves the state to PostgreSQL (`ExamAttemptLog.highlighted_markdown`).
* **Backward Compatibility:** Handles legacy client payloads containing `"highlights"` dictionaries by normalizing them to Markdown tags before saving.

---

## 3. Read Selectors Layer (`service/selectors.py`)

All read queries are strictly isolated in `service/selectors.py`:

| Selector Function | Description | Target Database |
| :--- | :--- | :--- |
| `get_article_detail(article_id)` | Fetches complete article document, sanitized text, and quizzes | MongoDB `gold_content` |
| `list_gold_articles(theme, limit, offset)`| Returns paginated article cards for browsing catalogs | MongoDB `gold_content` |
| `get_user_profile_stats(user_id)` | Returns stars, streaks, total tests, and accuracy metrics | PostgreSQL `UserProfile` |
| `get_topic_proficiency_radar(user_id)` | Computes accuracy percentages across all IELTS categories | PostgreSQL `TopicProficiency` |
| `get_user_exam_history(user_id, limit)` | Returns chronological list of completed test attempts | PostgreSQL `ExamAttemptLog` |

---

## 4. Infrastructure Adapters (`service/infrastructure/`)

To prevent direct coupling to database drivers, the service layer communicates with non-relational databases via **Repository Pattern Adapters**:

* **`MongoArticleStore` (`get_article_store()`):**
  * Manages PyMongo connections to `articlesDB`.
  * Provides typed helpers (`get_gold_content`, `upsert_article`, `delete_article`).
  * Features automatic retry and connection-pool management.
* **`MinIOStorageAdapter`:**
  * Handles object uploads and downloads for raw HTML backups and pickled machine learning models.
* **`ChromaVectorAdapter`:**
  * Connects to ChromaDB for semantic vector searches.
