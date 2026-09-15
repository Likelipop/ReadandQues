# Developer Guide & API Reference

This document is the operational handbook and API reference for developers integrating with or modifying the **AI Service** (`ai_service/`).

---

## 1. Environment Configuration Reference

The AI Service connects to Azure OpenAI and downstream storage systems via the following environment variables (typically defined in `.env`):

| Variable Name | Required | Default Value | Description |
| :--- | :--- | :--- | :--- |
| `AZURE_OPENAI_API_KEY` | **Yes** | — | Primary API key for Azure OpenAI Service |
| `AZURE_OPENAI_ENDPOINT` | **Yes** | — | Azure endpoint URL (e.g. `https://<resource>.services.ai.azure.com`) |
| `AZURE_DEPLOYMENT_NAME` | No | `gpt-5-mini` | Azure model deployment name |
| `AZURE_OPENAI_API_VERSION` | No | `2024-02-01` | Azure OpenAI API version |
| `CHROMA_HOST` | No | `chromadb` (Docker) / `localhost` (Local) | Hostname for ChromaDB vector store |
| `CHROMA_PORT` | No | `8000` (Docker) / `8002` (Local) | Port for ChromaDB vector store |
| `MONGO_URI` | No | `mongodb://admin:changeme@mongo:27017...` | MongoDB connection URI |
| `MINIO_ENDPOINT` | No | `minio:9000` (Docker) / `localhost:9000` | MinIO S3 endpoint |

---

## 2. Public API Specification (`ai_service.interface`)

All external modules (Django views, Celery tasks, Dagster assets) interact with the AI Service **exclusively** through `ai_service.interface`.

```python
from ai_service.interface import (
    ask_study_dock,
    explain_phrase,
    generate_quiz,
    get_passage_proof,
    index_article,
    search_articles,
    stream_explanation,
    stream_study_dock,
    stream_study_dock_sync,
)
```

---

### A. Study Dock: Conversational Multi-Agent System

#### 1. Synchronous Invocation (`ask_study_dock`)
```python
def ask_study_dock(
    query: str,
    article_id: str = "",
    page_context: str = "homepage",
    article_text: str = "",
    thread_id: str = "",
    user_id: int | None = None,
) -> dict[str, Any]:
    """
    Executes the LangGraph Multi-Agent workflow synchronously.
    
    Returns:
        dict: {
            "response": str,         # Markdown response from agent
            "citations": list[dict], # Source citations (if RAG executed)
            "quiz_data": list[dict], # Quiz payload (if quiz intent)
            "action_type": str,      # "chat" | "quiz"
            "intent": str,           # "general" | "quiz"
            "error": str             # Error trace if any
        }
    """
```

**Usage Example:**
```python
result = ask_study_dock(
    query="Why did East Antarctica gain ice recently?",
    article_id="art_b63f7920e6650b13",
    page_context="readspace",
    article_text="East Antarctica experienced record-breaking snowfall...",
    thread_id="user_session_42",
)
print(result["response"])
print("Citations:", result["citations"])
```

---

#### 2. Streaming Invocation (`stream_study_dock_sync` & `stream_study_dock`)
For real-time token streaming over WebSockets, Server-Sent Events (SSE), or HTTP streaming responses:

```python
# Synchronous generator (Recommended for Django WSGI / gthread workers)
for event in stream_study_dock_sync(query="Explain atmospheric rivers", thread_id="session_1"):
    if event["type"] == "delta":
        print(event["text"], end="", flush=True)
    elif event["type"] == "metadata_final":
        print("\n\nCitations:", event["citations"])
```

---

### B. IELTS Quiz Generation (`generate_quiz`)

```python
def generate_quiz(article_text: str) -> dict[str, Any]:
    """
    Generates IELTS Academic Reading comprehension questions and semantic metadata.
    
    Returns:
        dict: {
            "quizzes": list[QuizItem],
            "semantic_analysis": {
                "keywords": list[str],
                "summary": str,
                "main_idea": str,
                "genre": str,
                "theme": str
            }
        }
    """
```

**Usage Example:**
```python
exam_data = generate_quiz(article_text="Azza Fadhel and team developed an AI-driven method...")
for q in exam_data["quizzes"]:
    print(f"[{q['quiz_type']}] {q['question']}")
    print(f"Answer: {q['correct_answer']}\n")
```

---

### C. Contextual Phrase Explainer (`explain_phrase` & `stream_explanation`)

```python
# 1. Structured Output
explanation = explain_phrase(
    phrase="unprecedented atmospheric rivers",
    context="East Antarctica experienced unprecedented atmospheric rivers that deposited..."
)
print(explanation["summary"])
print(explanation["simplified_version"])

# 2. Real-time token streaming
for token in stream_explanation(phrase="unprecedented", context="..."):
    print(token, end="", flush=True)
```

---

### D. Hybrid Search (`search_articles`)

```python
def search_articles(
    query: str,
    method: str = "hybrid",  # "hybrid" | "semantic" | "keyword"
    limit: int = 10,
) -> list[dict[str, Any]]:
    """
    Search articles by dense vector (ChromaDB), lexical (BM25), or hybrid RRF.
    """
```

**Usage Example:**
```python
# Query across all ingested news
results = search_articles(query="artificial intelligence printing", method="hybrid", limit=5)
for item in results:
    print(f"- {item.get('title')} (ID: {item.get('article_id')})")
```

---

### E. Indexing Pipeline Bridge (`index_article`)
Called by the data pipeline after creating a Gold article:
```python
index_article(
    article_id="art_12345",
    title="Breakthrough in Quantum Computing",
    text="Researchers at MIT have demonstrated...",
    url="https://example.com/quantum",
    keywords=["Quantum", "Physics", "Computing"],
)
```

---

## 3. Local Development & Testing Runbook

### Running Standalone Queries (CLI)
You can test the AI Service without starting Django or Docker:

```bash
# In project root:
uv run python -c "
from ai_service.interface import ask_study_dock
res = ask_study_dock('Explain the concept of RAG simply')
print(res['response'])
"
```

### Running the Test Suite
```bash
# Run unit tests for multi-agent graph
uv run pytest ai_service/agents/tests/

# Run RAG Triad benchmarks
uv run python -m evaluation.test_rag_triad
```

---

## 4. Troubleshooting & Operational Guide

| Problem | Root Cause | Solution |
| :--- | :--- | :--- |
| `Missing AZURE_OPENAI_API_KEY` | Environment variable not found | Verify `.env` exists in root and contains `AZURE_OPENAI_API_KEY`. |
| `RateLimitError` / HTTP 429 | Azure OpenAI TPM/RPM limit exceeded | `connection.py` includes `max_retries=3`. For heavy batch jobs, throttle requests with `time.sleep()`. |
| `ChromaConnectionError` | ChromaDB container is down or wrong port | Verify ChromaDB is running via `docker ps`. Host calls must use port `8002`; container calls must use `chromadb:8000`. |
| `OutputParserException` | LLM failed structured output schema | Handled automatically by `generator.py` retry loops. Ensure temperature is $\le 1.0$. |
| Tokens not streaming in browser | WSGI server buffering HTTP responses | Use `stream_study_dock_sync()` and ensure Nginx/Gunicorn has proxy buffering disabled (`X-Accel-Buffering: no`). |
