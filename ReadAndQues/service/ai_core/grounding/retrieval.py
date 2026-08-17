import re

from service.ai_core.grounding.chunking import ArticleChunk


def retrieve_article_chunks(chunks: list[ArticleChunk], query: str, top_k: int = 3) -> list[ArticleChunk]:
    """
    Performs article-scoped lexical retrieval over the given article's chunks.
    Guarantees no cross-article leakage.
    """
    if not chunks or not query.strip():
        return []

    tokens = [t.lower() for t in re.findall(r"\w+", query) if len(t) > 2]
    if not tokens:
        return chunks[:top_k]

    scored = []
    for chunk in chunks:
        chunk_text_lower = chunk.text.lower()
        score = sum(chunk_text_lower.count(t) for t in tokens)
        scored.append((score, chunk))

    scored.sort(key=lambda x: x[0], reverse=True)
    # Filter chunks with score > 0 if available, else return top_k
    matched = [c for s, c in scored if s > 0]
    if matched:
        return matched[:top_k]
    return [c for _, c in scored[:top_k]]
