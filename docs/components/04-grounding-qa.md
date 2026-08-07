# Component Guide: Grounded Q&A Ticket Subsystem

This document explains the article-grounded Q&A ticket subsystem, stable chunking, article-scoped retrieval, and exact citation verification.

---

## 1. Grounding Mandate & Problem Statement

Standard LLM Q&A can hallucinate or bring in external web knowledge not present in the user's active reading material. The Grounded Q&A subsystem guarantees:

1. **Strict Article Scoping**: Answers are generated exclusively from the active article text.
2. **Zero Cross-Article Contamination**: Lexical retrieval is strictly scoped to the active article's chunks.
3. **Exact Citation Verification**: Every answer must quote an exact substring from the article. Unverified answers are automatically rejected and converted to `"not_found_in_article"`.

---

## 2. Article Chunking & Content Hashes

Articles are partitioned into stable chunks with offset boundaries in [service/ai_core/grounding/chunking.py](file:///home/likelipop/Project/ReadandQues/ReadAndQues/service/ai_core/grounding/chunking.py):

```python
from service.ai_core.grounding import chunk_article_text

chunks = chunk_article_text(article_text="Paragraph 1...\n\nParagraph 2...")
```

Each `ArticleChunk` contains:
- `chunk_id`: Stable identifier (e.g. `chunk_0`, `chunk_1`)
- `text`: Paragraph text content
- `start_offset` & `end_offset`: Exact 0-indexed character offsets within full article text
- `content_hash`: SHA-256 checksum hex slice

---

## 3. Article-Scoped Lexical Retrieval

Candidate chunks are retrieved strictly from the active article in [service/ai_core/grounding/retrieval.py](file:///home/likelipop/Project/ReadandQues/ReadAndQues/service/ai_core/grounding/retrieval.py):

```python
from service.ai_core.grounding import retrieve_article_chunks

matched_chunks = retrieve_article_chunks(chunks=chunks, query="solar energy", top_k=3)
```

No database vectors or global search collections are queried during single-article Q&A, guaranteeing zero cross-article leakage.

---

## 4. LangGraph Ask-Article Workflow

The Q&A workflow is executed by the stateful LangGraph workflow in [service/ai_core/graphs/ask_article/graph.py](file:///home/likelipop/Project/ReadandQues/ReadAndQues/service/ai_core/graphs/ask_article/graph.py):

```
+---------------------+        +---------------------+        +---------------------+
| chunk_and_retrieve  | ---->  |   generate_answer   | ---->  |   verify_grounding  |
| (Splits text and    |        | (LLM extracts answer|        | (Checks exact quote |
|  selects top-k)     |        |  & citation quote)  |        |  in chunk text)     |
+---------------------+        +---------------------+        +---------------------+
```

### Verification Node Behavior (`verify_grounding`):
- If `answer == "not_found_in_article"`, passes through directly.
- Checks whether `citation_quote` is present as an exact, case-insensitive substring within the retrieved chunk text.
- If the quote fails validation, logs a warning and returns `answer = "not_found_in_article"` with `is_grounded = False`.

---

## 5. API Endpoint Usage

The Q&A ticket subsystem is exposed via the versioned AI tool endpoint `/api/ai/tool/run/`:

```http
POST /readspace/api/ai/tool/run/
Content-Type: application/json

{
  "tool_name": "ask_article",
  "version": "1.0.0",
  "input_data": {
    "article_text": "Solar energy is renewable...",
    "question": "Is solar energy renewable?"
  }
}
```

Response:
```json
{
  "run_id": "run_9f8e7d6c5b4a3210",
  "tool_name": "ask_article",
  "version": "1.0.0",
  "status": "completed",
  "output": {
    "answer": "Yes, solar energy is a renewable resource.",
    "citation_quote": "Solar energy is renewable",
    "chunk_id": "chunk_0",
    "is_grounded": true
  },
  "duration_ms": 142.5
}
```
