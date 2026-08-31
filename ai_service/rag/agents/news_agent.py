"""
ai_service/rag/agents/news_agent.py — News RAG Agent with Hybrid Search & Reranking.
"""

import logging
import os
import time

from ai_service.rag.grounding.reranker import rerank_chunks
from ai_service.rag.schemas import AgentResult, Citation
from ai_service.rag.search.bm25_index import process_text_to_tokens, search_bm25
from ai_service.rag.search.vector_store import vector_search_chunks
from shared.enums import AgentIntent

logger = logging.getLogger(__name__)

NEWS_AGENT_SYSTEM_PROMPT = """You are a professional News Assistant and IELTS Reading Study Buddy.
Answer the user's question based strictly on the retrieved context below.

RULES:
1. Only use information present in the context. Do NOT hallucinate.
2. Format your response in clean GitHub Flavored Markdown with bold keywords and structured bullet points.
3. If relevant, cite sources as `[Article Title](URL)` or `[Article Title] (ID: article_id)`.
4. If the context does not contain enough information, state: "The current articles in the system do not contain enough information to answer this question."

=== RETRIEVED CONTEXT ===
{context}
"""


def _retrieve_hybrid_candidates(query: str, candidate_limit: int = 20, filters: dict | None = None) -> list[dict]:
    vector_hits = vector_search_chunks(query, limit=candidate_limit, where_filter=filters)
    tokens = process_text_to_tokens(query)
    bm25_hits = search_bm25(tokens, n=candidate_limit) if tokens else []

    rrf_map: dict[str, dict] = {}
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
                "hit": {
                    "id": syn_key,
                    "text": "",
                    "metadata": {"article_id": article_id, "title": f"Article {article_id}"},
                },
                "sources": ["bm25"],
            }

    sorted_candidates = sorted(rrf_map.values(), key=lambda x: x["rrf_score"], reverse=True)
    results = []
    for c in sorted_candidates[:candidate_limit]:
        hit = c["hit"]
        hit["rrf_score"] = round(c["rrf_score"], 4)
        results.append(hit)
    return results


def run_news_agent(
    query: str, filters: dict | None = None, top_candidates: int = 20, top_reranked: int = 5
) -> AgentResult:
    start_time = time.time()
    candidates = _retrieve_hybrid_candidates(query, candidate_limit=top_candidates, filters=filters)

    if not candidates:
        return AgentResult(
            intent=AgentIntent.NEWS,
            answer="The current articles in the system do not contain enough information to answer this question.",
            citations=[],
            retrieved_chunks_count=0,
            confidence_score=0.0,
            execution_time_ms=(time.time() - start_time) * 1000,
        )

    retrieved = rerank_chunks(query=query, candidates=candidates, top_k=top_reranked)

    citations = []
    seen = set()
    for chunk in retrieved:
        meta = chunk.get("metadata", {})
        aid = meta.get("article_id")
        if aid and aid not in seen:
            seen.add(aid)
            kw_raw = meta.get("keywords", "")
            kw_list = [k.strip() for k in kw_raw.split(",") if k.strip()] if isinstance(kw_raw, str) else (kw_raw or [])
            citations.append(
                Citation(
                    article_id=aid,
                    title=meta.get("title", "Untitled Article"),
                    url=meta.get("url", ""),
                    keywords=kw_list,
                    rrf_score=chunk.get("rerank_score", chunk.get("rrf_score", 0.0)),
                )
            )

    context_lines = []
    for i, c in enumerate(retrieved, 1):
        m = c.get("metadata", {})
        title = m.get("title", "Untitled")
        url = m.get("url", "")
        aid = m.get("article_id", "")
        src = f"[{title}]({url})" if url else f"[{title}] (ID: {aid})"
        context_lines.append(
            f"--- Document {i} (Score: {c.get('rerank_score', 0.0)}) ---\nSource: {src}\nContent:\n{c.get('text', '')}\n"
        )

    formatted_context = "\n".join(context_lines)
    system_prompt = NEWS_AGENT_SYSTEM_PROMPT.format(context=formatted_context)

    api_key = os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        fallback_ans = (
            "### 📰 Relevant Articles Found:\n\n"
            + "\n".join([f"- **[{c.title}]({c.url})** (Tags: `{', '.join(c.keywords) or 'General'}`)" for c in citations])
            + "\n\n> *Note: Offline mode. Please configure LLM API key for full generated answers.*"
        )
        return AgentResult(
            intent=AgentIntent.NEWS,
            answer=fallback_ans,
            citations=citations,
            retrieved_chunks_count=len(retrieved),
            execution_time_ms=(time.time() - start_time) * 1000,
        )

    try:
        from ai_service.connection import get_llm
        llm = get_llm(temperature=0.2)
        from langchain_core.messages import HumanMessage, SystemMessage
        resp = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=query)])
        answer = resp.content if hasattr(resp, "content") else str(resp)

        return AgentResult(
            intent=AgentIntent.NEWS,
            answer=answer,
            citations=citations,
            retrieved_chunks_count=len(retrieved),
            execution_time_ms=(time.time() - start_time) * 1000,
        )
    except Exception as e:
        logger.error(f"[NewsAgent] LLM generation call failed: {e}")
        return AgentResult(
            intent=AgentIntent.NEWS,
            answer=f"Error generating answer: {e}",
            citations=citations,
            retrieved_chunks_count=len(retrieved),
            execution_time_ms=(time.time() - start_time) * 1000,
        )
