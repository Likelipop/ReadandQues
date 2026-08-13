# Component Guide: Web Application Layer & Django Apps

This document describes the presentation and web application layer, Django apps, View-to-Service decoupling, REST APIs, and template structures.

---

## 1. Django Applications Structure

ReadAndQues is divided into modular Django applications:

```
ReadAndQues/
├── accounts/      # User authentication, profiles, star balances
├── homepage/      # Landing page, article feed sections, global search
├── readspace/     # Interactive reading workspace, quizzes, paraphrasing, markers
└── service/       # Central backend domain, orchestration, AI platform, models
```

---

## 2. View-to-Service Decoupling Pattern

According to [ADR-0002](file:///home/likelipop/Project/ReadandQues/docs/refactor/adr/0002-application-orchestration-boundary.md), Django view functions must not contain business logic or direct database connections. Instead, views delegate directly to application service functions:

```
[ HTTP Request ]
       |
       v
  readspace/views.py (Request parsing, login check)
       |
       v
  readspace/services.py (Business logic & Use case)
       |
       +----------------------------+
       |                            |
       v                            v
  ArticleRepository           OrchestrationFacade
  (Simple Reads/Writes)      (Multi-step Pipelines)
```

Example in [readspace/views.py](file:///home/likelipop/Project/ReadandQues/ReadAndQues/readspace/views.py):
```python
from readspace.services import get_article_detail

def readspace_view(request, pk):
    article, quiz, attempt = get_article_detail(pk, user_id=request.user.id)
    return render(request, "readspace/readspace.html", {
        "article": article,
        "quiz": quiz,
        "attempt": attempt,
    })
```

---

## 3. Key URLs & REST APIs

### Main Web Views
- **`GET /`**: Homepage landing feed and curated article sections ([homepage/views.py](file:///home/likelipop/Project/ReadandQues/ReadAndQues/homepage/views.py)).
- **`GET /readspace/<pk>/`**: Interactive reading workspace ([readspace/views.py](file:///home/likelipop/Project/ReadandQues/ReadAndQues/readspace/views.py)).
- **`GET /readspace/all-tests/`**: User test library.
- **`POST /readspace/import/`**: Web article import handler.

### REST APIs
- **`POST /readspace/api/ai/tool/run/`**: Generic authenticated AI tool runner (`smart_paraphrase`, `quiz_generator`, `batch_paraphrase`, `ask_article`).
- **`POST /readspace/api/<pk>/smart_paraphrase/`**: Legacy paraphrase API wrapper.
- **`POST /readspace/api/<pk>/save_markers/`**: Saves user highlighter marks and reading progress.
- **`GET /readspace/api/search/keyword/?q=...`**: BM25 lexical keyword search.
- **`GET /readspace/api/search/semantic/?q=...`**: ChromaDB vector semantic search.

---

## 4. User Star Charges & Entitlements

Article imports and AI operations consume user stars. Transactional star deductions are handled atomically via `charge_and_create_import_request` in [service/models.py](file:///home/likelipop/Project/ReadandQues/ReadAndQues/service/models.py):

```python
from service.models import charge_and_create_import_request

# Deduct star & log import request atomically in PostgreSQL
import_req = charge_and_create_import_request(user_id=request.user.id, url=article_url)
```

---

## 5. UI Design & Styling Rules

- **CSS & Aesthetics**: Uses Vanilla CSS with curated color tokens, sleek dark modes, and dynamic micro-animations.
- **Typography**: Modern Google Fonts (e.g. Inter, Outfit, Roboto).
- **Templates Location**: Located in `templates/` and app-specific `templates/readspace/`, `templates/homepage/`.
