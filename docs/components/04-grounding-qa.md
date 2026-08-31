# Component Guide: Grounding & RAG Retrieval

This document explains the multi-stage grounding and retrieval mechanisms used in ReadAndQues to ensure high precision and zero hallucinations.

---

## 1. Multi-Stage Hybrid Retrieval Flow

```
User Query: "What are the latest developments in renewable energy?"
    │
    ├─────────────────────────────┬─────────────────────────────┐
    ▼                             ▼                             ▼
[ChromaDB Vector Search]   [BM25 Okapi Search]          [Metadata Filters]
(Semantic Embeddings)       (Lexical Token Match)        (Keywords / Article ID)
    │                             │                             │
    └─────────────────────────────┴─────────────────────────────┘
                                  │
                                  ▼
                    [Reciprocal Rank Fusion (RRF)]
                                  │
                                  ▼
                   [Cross-Encoder Reranker Node]
                    (ms-marco-MiniLM-L-6-v2)
                                  │
                                  ▼
                  [Top-5 Grounded Chunks + Quotes]
                                  │
                                  ▼
                     [Grounded LLM Response]
```

---

## 2. Core Grounding Components

### A. Hierarchical Chunking ([`grounding/chunking.py`](file:///home/likelipop/Project/ReadandQues/ai_service/rag/grounding/chunking.py))
Articles are partitioned into parent chunks (~500 words for broader context) and child chunks (~100-150 words for precise retrieval).

### B. Reciprocal Rank Fusion (RRF)
Combines semantic rank from ChromaDB and keyword rank from BM25 using standard RRF formula:
$$	ext{RRF Score} = \sum_{s \in \{	ext{vector}, 	ext{bm25}\}} rac{1}{60 + 	ext{rank}_s}$$

### C. Cross-Encoder Reranking ([`grounding/reranker.py`](file:///home/likelipop/Project/ReadandQues/ai_service/rag/grounding/reranker.py))
Scores query-chunk pairs jointly with a transformer Cross-Encoder model to eliminate irrelevant candidates before prompting the LLM.

### D. Verbatim Passage Proof ([`grounding/passage_proof.py`](file:///home/likelipop/Project/ReadandQues/ai_service/rag/grounding/passage_proof.py))
Matches quiz questions against original source text using fuzzy token alignment, ensuring students can inspect exact quotes.
