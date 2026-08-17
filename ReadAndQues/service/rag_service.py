"""
service/rag_service.py — Hybrid Retrieval & RAG Query Execution.
"""

import logging
import os
from typing import Dict, List, Optional
from openai import OpenAI

import service.infrastructure.chroma.vector_store as vector_store
import service.infrastructure.bm25.connection as bm25_conn
import service.infrastructure.bm25.index as bm25_idx
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


def perform_hybrid_search(query: str, top_k: int = 6, filters: Optional[Dict] = None) -> List[Dict]:
    """Hybrid Search combining ChromaDB vector search + BM25 keyword search via RRF."""
    vector_hits = vector_store.vector_search_chunks(query, limit=top_k * 2, where_filter=filters)
    tokens = bm25_conn.process_text_to_tokens(query) if hasattr(bm25_conn, "process_text_to_tokens") else []
    bm25_hits = bm25_idx.search_bm25(tokens, n=top_k * 2) if tokens else []

    rrf_map: Dict[str, Dict] = {}
    rrf_k = 60.0

    for rank, hit in enumerate(vector_hits):
        doc_key = hit["id"]
        rrf_score = 1.0 / (rrf_k + (rank + 1))
        rrf_map[doc_key] = {
            "rrf_score": rrf_score,
            "hit": hit,
            "sources": ["vector"],
        }

    for rank, hit in enumerate(bm25_hits):
        article_id = hit["id"]
        matching_key = None
        for key in rrf_map:
            if rrf_map[key]["hit"]["metadata"].get("article_id") == article_id:
                matching_key = key
                break

        rrf_score = 1.0 / (rrf_k + (rank + 1))

        if matching_key:
            rrf_map[matching_key]["rrf_score"] += rrf_score
            rrf_map[matching_key]["sources"].append("bm25")
        else:
            synthetic_key = f"{article_id}_bm25_{rank}"
            rrf_map[synthetic_key] = {
                "rrf_score": rrf_score,
                "hit": {
                    "id": synthetic_key,
                    "text": "",
                    "metadata": {"article_id": article_id, "title": f"Article {article_id}"},
                    "distance": 1.0,
                    "score": hit.get("score", 0.0),
                },
                "sources": ["bm25"],
            }

    sorted_candidates = sorted(rrf_map.values(), key=lambda x: x["rrf_score"], reverse=True)
    final_results = []
    for candidate in sorted_candidates[:top_k]:
        hit = candidate["hit"]
        hit["rrf_score"] = round(candidate["rrf_score"], 4)
        hit["retrieval_sources"] = candidate["sources"]
        final_results.append(hit)

    return final_results


def query_news_rag(
    query: str,
    top_k: int = 6,
    filters: Optional[Dict] = None,
    model_name: str = "gpt-4o-mini",
) -> Dict:
    """Execute end-to-end RAG query."""
    if not query or not query.strip():
        return {
            "status": "error",
            "answer": "Vui lòng nhập câu hỏi hợp lệ.",
            "query": query,
            "citations": [],
            "retrieved_chunks_count": 0,
        }

    retrieved_chunks = perform_hybrid_search(query, top_k=top_k, filters=filters)

    if not retrieved_chunks:
        return {
            "status": "no_context",
            "answer": "Rất tiếc, tập tin tức hiện tại trong hệ thống chưa chứa thông tin để trả lời câu hỏi này.",
            "query": query,
            "citations": [],
            "retrieved_chunks_count": 0,
        }

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

    formatted_context = format_context_documents(retrieved_chunks)
    system_prompt = NEWS_RAG_SYSTEM_PROMPT.format(context=formatted_context)
    user_prompt = NEWS_RAG_USER_TEMPLATE.format(query=query)

    client = get_openai_client()
    if not client:
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
            temperature=0.0,
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
