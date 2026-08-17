"""
service/rag/agents/news/agent.py — News RAG Agent.
"""

import logging
import os
import time
from typing import Dict, List, Optional
from openai import OpenAI

from service.domain.enums import AgentIntent
import service.infrastructure.chroma.vector_store as vector_store
import service.infrastructure.bm25.connection as bm25_conn
import service.infrastructure.bm25.index as bm25_idx
from service.rag.agents.news.prompts import NEWS_AGENT_SYSTEM_PROMPT
from service.rag.schemas import AgentResult, Citation

logger = logging.getLogger(__name__)


def _retrieve_hybrid(query: str, top_k: int = 6, filters: Optional[Dict] = None) -> List[Dict]:
    vector_hits = vector_store.vector_search_chunks(query, limit=top_k * 2, where_filter=filters)
    tokens = bm25_conn.process_text_to_tokens(query) if hasattr(bm25_conn, "process_text_to_tokens") else []
    bm25_hits = bm25_idx.search_bm25(tokens, n=top_k * 2) if tokens else []

    rrf_map: Dict[str, Dict] = {}
    rrf_k = 60.0

    for rank, hit in enumerate(vector_hits):
        doc_key = hit["id"]
        rrf_score = 1.0 / (rrf_k + (rank + 1))
        rrf_map[doc_key] = {"rrf_score": rrf_score, "hit": hit, "sources": ["vector"]}

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
            syn_key = f"{article_id}_bm25_{rank}"
            rrf_map[syn_key] = {
                "rrf_score": rrf_score,
                "hit": {"id": syn_key, "text": "", "metadata": {"article_id": article_id, "title": f"Article {article_id}"}},
                "sources": ["bm25"],
            }

    sorted_candidates = sorted(rrf_map.values(), key=lambda x: x["rrf_score"], reverse=True)
    results = []
    for c in sorted_candidates[:top_k]:
        hit = c["hit"]
        hit["rrf_score"] = round(c["rrf_score"], 4)
        results.append(hit)
    return results


def run_news_agent(query: str, filters: Optional[Dict] = None, top_k: int = 6) -> AgentResult:
    """Executes News RAG Agent workflow."""
    start_time = time.time()
    retrieved = _retrieve_hybrid(query, top_k=top_k, filters=filters)

    if not retrieved:
        return AgentResult(
            intent=AgentIntent.NEWS,
            answer="Rất tiếc, tập tin tức hiện tại trong hệ thống chưa chứa thông tin để trả lời câu hỏi này.",
            citations=[],
            retrieved_chunks_count=0,
            confidence_score=0.0,
            execution_time_ms=(time.time() - start_time) * 1000,
        )

    citations = []
    seen = set()
    for chunk in retrieved:
        meta = chunk.get("metadata", {})
        aid = meta.get("article_id")
        if aid and aid not in seen:
            seen.add(aid)
            citations.append(Citation(
                article_id=aid,
                title=meta.get("title", "Untitled Article"),
                url=meta.get("url", ""),
                theme=meta.get("theme", "General"),
                genre=meta.get("genre", "general"),
                rrf_score=chunk.get("rrf_score", 0.0),
            ))

    # Format Context
    context_lines = []
    for i, c in enumerate(retrieved, 1):
        m = c.get("metadata", {})
        title = m.get("title", "Untitled")
        url = m.get("url", "")
        aid = m.get("article_id", "")
        src = f"[{title}]({url})" if url else f"[{title}] (ID: {aid})"
        context_lines.append(f"--- Document {i} ---\nSource: {src}\nContent:\n{c.get('text', '')}\n")

    formatted_context = "\n".join(context_lines)
    system_prompt = NEWS_AGENT_SYSTEM_PROMPT.format(context=formatted_context)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        fallback_ans = "Hệ thống đã tìm thấy các bài báo liên quan:\n" + "\n".join([f"- [{c.title}]({c.url})" for c in citations])
        return AgentResult(
            intent=AgentIntent.NEWS,
            answer=fallback_ans,
            citations=citations,
            retrieved_chunks_count=len(retrieved),
            execution_time_ms=(time.time() - start_time) * 1000,
        )

    try:
        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query},
            ],
            temperature=0.0,
        )
        answer = resp.choices[0].message.content or ""
        return AgentResult(
            intent=AgentIntent.NEWS,
            answer=answer,
            citations=citations,
            retrieved_chunks_count=len(retrieved),
            execution_time_ms=(time.time() - start_time) * 1000,
        )
    except Exception as e:
        logger.error(f"[NewsAgent] OpenAI call failed: {e}")
        return AgentResult(
            intent=AgentIntent.NEWS,
            answer=f"Lỗi khi gọi AI Model: {e}",
            citations=citations,
            retrieved_chunks_count=len(retrieved),
            execution_time_ms=(time.time() - start_time) * 1000,
        )
