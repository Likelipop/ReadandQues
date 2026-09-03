"""
ai_service/agents/tools.py — Tools for Multi-Agent Supervisor.

Provides the single `search_articles` tool for grounded article search & news discovery.
All comments and docstrings are in English.
"""

import logging
from typing import Any

from langchain_core.tools import tool

from ai_service.rag.agents.news_agent import retrieve_and_rerank_context

logger = logging.getLogger(__name__)


def _get_article_metadata(article_id: str) -> dict[str, Any]:
    """Safely fetch gold article metadata for rich card presentation."""
    try:
        try:
            import service.infrastructure.mongo.article_store as article_store
        except ImportError:
            import ReadAndQues.service.infrastructure.mongo.article_store as article_store
        doc = article_store.get_gold_content(article_id)
        if doc:
            return doc
    except Exception as e:
        logger.debug(f"Could not fetch metadata from article_store for {article_id}: {e}")
    return {}


@tool
def search_articles(query: str, article_id: str = "", limit: int = 3) -> str:
    """
    Search the ReadAndQues article archive using hybrid BM25 + vector search with reranking.

    Use this tool ONLY when:
    - User asks about factual news or real-world events.
    - User on the Homepage asks for article recommendations, topic exploration, or reading material.
    - User in ReadSpace explicitly asks for information beyond the active passage.

    Do NOT use this tool for:
    - Vocabulary or grammar explanations (explain directly).
    - General questions about ReadAndQues website or features (answer directly).
    - Requests to generate a quiz (delegate to the quiz generator).

    Args:
        query: The semantic search query or topic keywords.
        article_id: Optional article ID to restrict retrieval scope.
        limit: Maximum number of articles/chunks to return (default: 3).

    Returns:
        Structured string containing grounded passages, citations, and rich card metadata.
    """
    filters = {"article_id": article_id} if article_id else None
    try:
        formatted_context, citations, retrieved = retrieve_and_rerank_context(
            query=query, filters=filters, top_candidates=15, top_reranked=limit
        )
    except Exception as e:
        logger.error(f"[search_articles tool] Retrieval error: {e}")
        return f"Error retrieving articles from database: {e}"

    if not retrieved and not citations:
        return "No relevant articles found in the database matching your query."

    # Build detailed context including rich metadata for Homepage cards
    output_lines = [
        "=== SEARCH RESULTS & GROUNDED CONTEXT ===",
    ]

    seen_articles = set()
    card_metadata_list = []

    for chunk in retrieved:
        meta = chunk.get("metadata", {})
        aid = meta.get("article_id") or ""
        if aid and aid not in seen_articles:
            seen_articles.add(aid)
            doc = _get_article_metadata(aid)
            title = doc.get("title") or meta.get("title") or f"Article {aid}"
            url = doc.get("url") or meta.get("url") or ""
            thumb = doc.get("thumbnail_url") or doc.get("image_url") or "https://images.unsplash.com/photo-1504711434969-e33886168f5c?auto=format&fit=crop&q=80&w=600"
            word_count = doc.get("word_count") or len((doc.get("original_text") or "").split()) or 450
            reading_time = max(1, round(word_count / 150))
            theme = doc.get("theme") or meta.get("theme") or "General"
            
            card_metadata_list.append(
                f"- Article ID: {aid}\n"
                f"  Title: {title}\n"
                f"  URL: {url}\n"
                f"  Thumbnail: {thumb}\n"
                f"  Word Count: ~{word_count} words ({reading_time} min read)\n"
                f"  Theme/Topic: {theme}\n"
                f"  ReadSpace Link: /readspace/{aid}\n"
            )

    if card_metadata_list:
        output_lines.append("\n### Available Articles for Recommendations (Use to format Rich News Cards):")
        output_lines.extend(card_metadata_list)

    output_lines.append("\n### Grounded Passages for Q&A:")
    output_lines.append(formatted_context if formatted_context else "No passage excerpts available.")

    return "\n".join(output_lines)
