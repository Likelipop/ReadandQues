"""
service/rag_service.py — Production RAG Service implementation
"""

import logging
import os
from typing import Dict, List, Optional
from openai import OpenAI

from service.repositories.search_repository import SearchRepository
from service.rag_prompts import NEWS_RAG_SYSTEM_PROMPT, NEWS_RAG_USER_TEMPLATE

logger = logging.getLogger(__name__)

_openai_client = None


def get_openai_client() -> Optional[OpenAI]:
    global _openai_client
    if _openai_client is not None:
        return _openai_client

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.warning("[RAG] OPENAI_API_KEY environment variable is missing.")
        return None

    try:
        _openai_client = OpenAI(api_key=api_key)
        return _openai_client
    except Exception as e:
        logger.error(f"[RAG] Failed to initialize OpenAI client: {e}")
        return None


def format_context_documents(chunks: List[Dict]) -> str:
    """Format retrieved RAG chunks into readable string context for LLM prompt."""
    if not chunks:
        return "No relevant news articles found."

    formatted_pieces = []
    for i, chunk in enumerate(chunks, 1):
        meta = chunk.get("metadata", {})
        title = meta.get("title", "Untitled Article")
        url = meta.get("url", "")
        article_id = meta.get("article_id", "")
        chunk_idx = meta.get("chunk_index", 0)
        text = chunk.get("text", "").strip()

        source_label = f"[{title}]({url})" if url else f"[{title}] (ID: {article_id})"
        piece = (
            f"--- Document {i} ---\n"
            f"Source: {source_label}\n"
            f"Article ID: {article_id} (Chunk {chunk_idx + 1})\n"
            f"Content:\n{text}\n"
        )
        formatted_pieces.append(piece)

    return "\n\n".join(formatted_pieces)


def query_news_rag(
    query: str,
    top_k: int = 6,
    filters: Optional[Dict] = None,
    model_name: str = "gpt-4o-mini",
) -> Dict:
    """
    Execute end-to-end RAG pipeline over MongoDB news collection:
    1. Hybrid search (ChromaDB Vector + BM25 Lexical + RRF).
    2. Build grounded context & prompts.
    3. Invoke LLM with temperature=0.0 (Factual Grounding).
    4. Return formatted answer & citation metadata.
    """
    if not query or not query.strip():
        return {
            "status": "error",
            "answer": "Vui lòng nhập câu hỏi hợp lệ.",
            "query": query,
            "citations": [],
            "retrieved_chunks_count": 0,
        }

    # 1. Retrieve Chunks
    search_repo = SearchRepository()
    retrieved_chunks = search_repo.search_hybrid(query, top_k=top_k, where_filter=filters)

    if not retrieved_chunks:
        return {
            "status": "no_context",
            "answer": "Rất tiếc, tập tin tức hiện tại trong hệ thống chưa chứa thông tin để trả lời câu hỏi này.",
            "query": query,
            "citations": [],
            "retrieved_chunks_count": 0,
        }

    # 2. Extract Citations
    citations = []
    seen_articles = set()
    for chunk in retrieved_chunks:
        meta = chunk.get("metadata", {})
        aid = meta.get("article_id")
        if aid and aid not in seen_articles:
            seen_articles.add(aid)
            citations.append({
                "article_id": aid,
                "title": meta.get("title", "Untitled Article"),
                "url": meta.get("url", ""),
                "theme": meta.get("theme", "General"),
                "genre": meta.get("genre", "general"),
                "rrf_score": chunk.get("rrf_score", 0.0),
            })

    # 3. Build Prompt Context
    formatted_context = format_context_documents(retrieved_chunks)
    system_prompt = NEWS_RAG_SYSTEM_PROMPT.format(context=formatted_context)
    user_prompt = NEWS_RAG_USER_TEMPLATE.format(query=query)

    # 4. Invoke LLM
    client = get_openai_client()
    if not client:
        # Fallback response if OpenAI key is not configured
        return {
            "status": "warning",
            "answer": (
                "Hệ thống đã truy xuất được các bài báo liên quan nhưng OpenAI API Key chưa được cấu hình.\n\n"
                "**Các bài báo liên quan được tìm thấy:**\n" +
                "\n".join([f"- [{c['title']}]({c['url']})" for c in citations])
            ),
            "query": query,
            "citations": citations,
            "retrieved_chunks_count": len(retrieved_chunks),
        }

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,  # Strict factual grounding as per skill-rag-pipeline & skill-prompt-patterns
        )
        answer_text = response.choices[0].message.content

        return {
            "status": "success",
            "answer": answer_text,
            "query": query,
            "citations": citations,
            "retrieved_chunks_count": len(retrieved_chunks),
            "model_used": model_name,
        }

    except Exception as e:
        logger.error(f"[RAG] OpenAI generation error: {e}")
        return {
            "status": "error",
            "answer": f"Đã xảy ra lỗi khi gọi AI Model: {str(e)}",
            "query": query,
            "citations": citations,
            "retrieved_chunks_count": len(retrieved_chunks),
        }
