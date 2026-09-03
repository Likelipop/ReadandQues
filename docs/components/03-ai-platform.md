# Component Guide: AI Platform (`ai_service`)

The AI Platform is an independent package in [`ai_service/`](file:///home/likelipop/Project/ReadandQues/ai_service/) providing NLP and LLM capabilities.

---

## 1. Public API Interface (`ai_service/interface.py`)

All callers interact through [`ai_service/interface.py`](file:///home/likelipop/Project/ReadandQues/ai_service/interface.py):

```python
from ai_service.interface import (
    generate_quiz,
    explain_phrase,
    stream_explanation,
    ask_question,
    search_articles,
    index_article,
    get_passage_proof,
)
```

| Function | Description |
|---|---|
| `generate_quiz(article_text)` | Analyzes article, extracts `keywords: list[str]`, generates IELTS-style questions with supporting quotes. |
| `explain_phrase(phrase, context)` | Provides contextual explanation, band score vocabulary, and examples. |
| `stream_explanation(phrase, context)` | Generator yielding real-time explanation tokens. |
| `ask_question(question, article_id)` | Executes multi-agent RAG pipeline to answer user questions grounded in articles. |
| `search_articles(query, method, limit)` | Searches articles by `keyword` (BM25), `semantic` (ChromaDB), or `hybrid`. |
| `index_article(article_id, title, text, url, keywords)` | Indexes article and chunks into ChromaDB and BM25. |
| `get_passage_proof(article_id, question_idx)` | Returns verbatim passage quotes supporting a quiz answer. |

---

## 2. Package Structure

```
ai_service/
├── connection.py            # Azure OpenAI / OpenAI LLM factory
├── interface.py             # Public API integration boundary
├── quiz_generator/          # Question generator flow & keyword extraction
│   ├── generator.py
│   ├── prompts.py
│   └── schemas.py
├── explainer/               # Contextual phrase explanation
│   ├── explainer.py
│   ├── prompts.py
│   └── schemas.py
└── rag/                     # Grounded RAG & search infrastructure
    ├── pipeline.py          # StateGraph RAG router
    ├── agents/news_agent.py # Hybrid search & reranked news agent
    ├── grounding/           # Semantic chunking, reranker, passage proof
    └── search/              # ChromaDB vector store & BM25 Okapi index
```
