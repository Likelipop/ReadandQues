# 📋 Task 02: RAG Module & LangGraph Dynamic Agent Router

> **Git Branch**: `feature/02-rag-langgraph-router`

## 🎯 Goal
Build a dedicated `service/rag/` module powered by a LangGraph StateGraph intent classifier and dynamic agent sub-graphs, parent-child ChromaDB vector chunking, and AI audit policy logging.

---

## 🛠 Detailed Technical Changes

### 1. Dedicated RAG Module Directory (`service/rag/`)
- `service/rag/router.py`: LangGraph `StateGraph` intent classifier (`RouterState` -> `classify_intent` -> conditional dispatch).
- `service/rag/schemas.py`: Pydantic `RAGQuery`, `RAGResponse`, `AgentResult`, `Citation` schemas.
- `service/rag/prompts.py`: Classification prompt for intent detection (`news`, `teacher`, `quiz_helper`, `unknown`).

### 2. Grouped Agent Architecture (`service/rag/agents/`)
- `service/rag/agents/news/`:
  - `agent.py`: `retrieve()` (hybrid ChromaDB parent-child + BM25 + RRF) and `generate()` (grounded response).
  - `prompts.py`: System prompt requiring citation links `[Article Title](url)` or `[Article Title] (ID: id)`.
  - `schemas.py`: `NewsAgentInput` and `NewsAgentOutput`.

### 3. Parent-Child Chunking (`service/infrastructure/chroma/chunking.py`)
- Algorithm in `chunking.py`:
  - **Parent Chunks**: $\ge 500$ words, whole paragraph group.
  - **Child Chunks**: Individual paragraphs within parent chunk.
- Storage in ChromaDB `news_chunks` collection with metadata:
  - `chunk_type`: `"parent"` or `"child"`
  - `parent_id`: ID of the parent chunk
- Retrieval pattern: Embed query $\rightarrow$ hit children $\rightarrow$ extract `parent_id` $\rightarrow$ load parent context for LLM.

### 4. Integration with AI Audit Platform (`service/ai/platform/`)
- Route all RAG LLM generation through `AIToolPolicy.execute()`.
- Record token usage, latency (ms), model name, and input/output payloads in PostgreSQL `AIRunLog` table.

### 5. Single RAG Entry Point (`service/services.py`)
- Expose `ask_rag_question(question: str, article_id: str = None)` in `services.py`.
- Delegate execution to `service.rag.router.build_rag_router().invoke()`.

---

## ✅ Acceptance Criteria
- [ ] Querying `ask_rag_question()` automatically classifies intent and routes to the News Agent.
- [ ] ChromaDB `news_chunks` correctly indexes parent and child chunks with metadata flags.
- [ ] Grounded responses return citation quotes matching paragraph evidence.
- [ ] Every RAG invocation logs a record into PostgreSQL `AIRunLog`.
