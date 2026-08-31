"""
ai_service/interface.py — Public API contract for the AI Service.

This is the SINGLE integration boundary between the AI Service and external callers
(Django Backend, Dagster Data Pipeline, evaluation scripts).

ALL comments and docstrings are in English.
"""

from __future__ import annotations
from typing import Any, Generator


def generate_quiz(article_text: str) -> dict[str, Any]:
    """
    Generate IELTS-style reading comprehension questions and extract keywords.

    Args:
        article_text: Plain text content of the article.

    Returns:
        dict with keys: keywords (list[str]), summary (str), questions (list of question dicts).
    """
    from ai_service.quiz_generator.generator import run_question_generator_flow
    return run_question_generator_flow(article_text)


def explain_phrase(phrase: str, context: str = "") -> dict[str, Any]:
    """
    Explain a word or phrase in its surrounding context.

    Args:
        phrase: The word or phrase to explain.
        context: The surrounding paragraph for contextual understanding.

    Returns:
        dict with keys: summary, detailed_explanation, simplified_version, key_terms.
    """
    from ai_service.explainer.explainer import run_explained_flow
    return run_explained_flow(phrase=phrase, paragraph_context=context)


def stream_explanation(phrase: str, context: str = "") -> Generator[str, None, None]:
    """
    Stream token-by-token explanation for real-time frontend display.

    Args:
        phrase: The word or phrase to explain.
        context: The surrounding paragraph for context.

    Yields:
        str chunks of the explanation as they are generated.
    """
    from ai_service.explainer.explainer import stream_explained_tokens
    yield from stream_explained_tokens(phrase=phrase, paragraph_context=context)


def ask_question(question: str, article_id: str | None = None) -> dict[str, Any]:
    """
    Answer a question using the multi-agent RAG pipeline.

    Args:
        question: User query in English or Vietnamese.
        article_id: Optional article ID to restrict retrieval scope.

    Returns:
        dict with keys: answer (markdown string), citations (list of dicts).
    """
    from ai_service.rag.pipeline import execute_rag_pipeline
    result = execute_rag_pipeline(question=question, article_id=article_id)
    return {
        "answer": result.answer,
        "citations": [c if isinstance(c, dict) else c.model_dump() for c in result.citations],
        "retrieved_chunks_count": result.retrieved_chunks_count,
        "intent": result.intent.value if hasattr(result.intent, "value") else str(result.intent),
    }


def search_articles(query: str, method: str = "hybrid", limit: int = 10) -> list[dict[str, Any]]:
    """
    Search articles by keyword (BM25), semantic vector (ChromaDB), or hybrid.

    Args:
        query: Search query string.
        method: One of 'keyword', 'semantic', or 'hybrid'.
        limit: Maximum number of results to return.

    Returns:
        List of dicts with keys: article_id, title, score.
    """
    if method == "keyword":
        from ai_service.rag.search.bm25_index import process_text_to_tokens, search_bm25
        tokens = process_text_to_tokens(query)
        return search_bm25(tokens, n=limit)
    elif method == "semantic":
        from ai_service.rag.search.vector_store import search_by_text
        return search_by_text(query, limit=limit)
    else:
        from ai_service.rag.search.bm25_index import process_text_to_tokens, search_bm25
        from ai_service.rag.search.vector_store import search_by_text
        semantic = search_by_text(query, limit=limit)
        tokens = process_text_to_tokens(query)
        keyword = search_bm25(tokens, n=limit)
        seen = set()
        merged = []
        for item in semantic + keyword:
            aid = item.get("article_id") or item.get("id")
            if aid and aid not in seen:
                seen.add(aid)
                merged.append(item)
        return merged[:limit]


def index_article(
    article_id: str,
    title: str,
    text: str,
    url: str = "",
    keywords: list[str] | None = None,
) -> bool:
    """
    Index an article into ChromaDB and BM25 search indices.

    Called by the data pipeline after creating a Gold article.

    Args:
        article_id: Unique article identifier.
        title: Article title.
        text: Full cleaned article text.
        url: Source URL.
        keywords: Article keywords and topic tags.

    Returns:
        True if indexing succeeded.
    """
    from ai_service.rag.search.bm25_index import rebuild_index
    from ai_service.rag.search.vector_store import add_article_vector, upsert_article_chunks

    add_article_vector(
        gold_id=article_id,
        summary=title,
        title=title,
        url=url,
        keywords=keywords,
    )
    upsert_article_chunks(
        article_id=article_id,
        title=title,
        full_text=text,
        url=url,
        keywords=keywords,
    )
    rebuild_index()
    return True


def get_passage_proof(article_id: str, question_idx: int) -> dict[str, Any] | None:
    """
    Find verbatim passage proof for a specific quiz question.

    Args:
        article_id: The article ID.
        question_idx: Index of the question in the quiz list.

    Returns:
        dict with proof data or None if not found.
    """
    from ai_service.rag.grounding.passage_proof import get_passage_proof as _get_proof
    return _get_proof(article_id=article_id, question_idx=question_idx)
