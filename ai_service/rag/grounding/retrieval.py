"""
ai_service/rag/grounding/retrieval.py — Article-scoped Lexical Retrieval.
"""

from rank_bm25 import BM25Okapi

from ai_service.rag.grounding.chunking import ArticleChunk
from ai_service.rag.search.bm25_index import process_text_to_tokens


def retrieve_article_chunks(chunks: list[ArticleChunk], query: str, top_k: int = 3) -> list[ArticleChunk]:
    if not chunks or not query.strip():
        return []

    query_tokens = process_text_to_tokens(query)
    if not query_tokens:
        return chunks[:top_k]

    tokenized_corpus = [process_text_to_tokens(chunk.text) for chunk in chunks]
    if not any(tokenized_corpus):
        tokenized_corpus = [chunk.text.lower().split() for chunk in chunks]

    try:
        bm25 = BM25Okapi(tokenized_corpus)
        scores = bm25.get_scores(query_tokens)
        scored = list(zip(scores, chunks, strict=False))
        scored.sort(key=lambda x: x[0], reverse=True)
        matched = [c for s, c in scored if s > 0]
        if matched:
            return matched[:top_k]
        return [c for _, c in scored[:top_k]]
    except Exception:
        scored = []
        for chunk in chunks:
            chunk_lower = chunk.text.lower()
            score = sum(chunk_lower.count(t) for t in query_tokens)
            scored.append((score, chunk))
        scored.sort(key=lambda x: x[0], reverse=True)
        matched = [c for s, c in scored if s > 0]
        if matched:
            return matched[:top_k]
        return [c for _, c in scored[:top_k]]
