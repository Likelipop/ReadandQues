# AI Service (`ai_service`)

Independent AI and RAG service package for ReadAndQues.

## Architecture

This package encapsulates all Large Language Model (LLM) and Retrieval-Augmented Generation (RAG) operations:

```
ai_service/
├── interface.py              # Single public contract for external callers
├── connection.py              # LLM client factory (Azure OpenAI)
├── quiz_generator/            # Structured IELTS quiz generation
├── explainer/                 # Contextual vocabulary and sentence explainer
└── rag/                       # Multi-agent RAG subsystem
    ├── pipeline.py            # LangGraph router & query executor
    ├── agents/                # Specialized domain agents (News)
    ├── grounding/             # Semantic chunking, reranking, and retrieval
    └── search/                # Vector store (ChromaDB) and lexical index (BM25)
```

## Public API (`ai_service.interface`)

Backend and Pipeline components only import from `ai_service.interface`:

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

# 1. Generate quiz from article text
quiz_data = generate_quiz(article_text="...")

# 2. Explain vocabulary / sentence in context
explanation = explain_phrase(phrase="mitigate", context="...")

# 3. Stream explanation tokens
for token in stream_explanation(phrase="breakthrough", context="..."):
    print(token, end="", flush=True)

# 4. RAG Chatbot query
answer = ask_question(question="What are recent advances in AI?")

# 5. Search
results = search_articles(query="climate change", method="hybrid")

# 6. Index article (called by data pipeline)
index_article(
    article_id="art_123",
    title="Article Title",
    text="Full content...",
    url="https://...",
    theme="Technology",
    genre="scientific",
)
```

## Dependencies

Install via `pip install -r ai_service/requirements.txt`:
- `langchain-openai`, `langgraph`, `openai`, `tiktoken`
- `chromadb`, `rank-bm25`, `sentence-transformers`, `spacy`
